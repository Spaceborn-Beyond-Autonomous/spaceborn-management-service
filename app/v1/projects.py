# routes/projects.py
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, or_, func, update
from sqlalchemy.orm import selectinload
from app.deps import get_session_dep, CoreOrAdmin, AnyAuthenticated
from schemas.project import ProjectCreate, ProjectRead, ProjectUpdate, ProjectStatus, ProjectPriority
from models.project import Project
from models.user import User, RoleEnum
from services.cache_service import ProjectCacheService
from datetime import datetime
from typing import Optional
import json


router = APIRouter(prefix="/projects", tags=["projects"])


def _serialize_project(project: Project) -> dict:
    """Serialize project to dict for caching"""
    return {
        "id": project.id,
        "name": project.name,
        "description": project.description,
        "status": project.status.value if hasattr(project.status, 'value') else project.status,
        "priority": project.priority.value if hasattr(project.priority, 'value') else project.priority,
        "progress": project.progress,
        "start_date": project.start_date.isoformat() if project.start_date else None,
        "due_date": project.due_date.isoformat() if project.due_date else None,
        "completed_at": project.completed_at.isoformat() if project.completed_at else None,
        "budget": project.budget,
        "spent": project.spent,
        "team_id": project.team_id,
        "owner_id": project.owner_id,
        "is_archived": project.is_archived,
        "tags": project.tags or [],
        "created_at": project.created_at.isoformat(),
        "updated_at": project.updated_at.isoformat(),
        # Computed fields
        "budget_remaining": project.budget_remaining,
        "days_until_due": project.days_until_due,
        "is_overdue": project.is_overdue,
    }


@router.post("/", response_model=ProjectRead, status_code=status.HTTP_201_CREATED, dependencies=[Depends(CoreOrAdmin)])
async def create_project(
    payload: ProjectCreate, 
    session: AsyncSession = Depends(get_session_dep)
):
    """Create a new project"""
    project = Project(**payload.model_dump())
    session.add(project)
    await session.commit()
    await session.refresh(project)
    
    # Cache the new project
    await ProjectCacheService.set_project(project.id, _serialize_project(project))
    
    # Invalidate list caches
    await ProjectCacheService.invalidate_project_lists()
    
    print(f"✓ Project {project.id} created and cached")
    return project


@router.get("/", response_model=list[ProjectRead])
async def list_projects(
    session: AsyncSession = Depends(get_session_dep),
    user: User = Depends(AnyAuthenticated),
    status_filter: Optional[ProjectStatus] = Query(None, alias="status"),
    priority: Optional[ProjectPriority] = None,
    include_archived: bool = False,
    team_id: Optional[int] = None,
    owner_id: Optional[int] = None,
    overdue_only: bool = False,
):
    """List projects with filtering and caching"""
    
    # Build cache key based on filters
    cache_key_parts = [
        f"project:list:user:{user.id}",
        f"status:{status_filter.value if status_filter else 'all'}",
        f"priority:{priority.value if priority else 'all'}",
        f"archived:{include_archived}",
        f"team:{team_id or 'all'}",
        f"owner:{owner_id or 'all'}",
        f"overdue:{overdue_only}"
    ]
    cache_key = ":".join(cache_key_parts)
    
    # Try cache first
    cached_projects = await ProjectCacheService.get_project_list(cache_key)
    if cached_projects:
        print(f"✓ Cache HIT for project list (user {user.id})")
        return cached_projects
    
    print(f"✗ Cache MISS for project list (user {user.id})")
    
    # Build query with eager loading
    query = select(Project).options(
        selectinload(Project.team),
        selectinload(Project.owner),
    )
    
    # Base permission filters
    if user.role == RoleEnum.EMPLOYEE:
        team_ids = [t.id for t in user.teams]
        if team_ids:
            query = query.where(
                or_(
                    Project.owner_id == user.id,
                    Project.team_id.in_(team_ids)
                )
            )
        else:
            query = query.where(Project.owner_id == user.id)
    
    # Additional filters
    filters = []
    
    if not include_archived:
        filters.append(Project.is_archived == False)
    
    if status_filter:
        filters.append(Project.status == status_filter)
    
    if priority:
        filters.append(Project.priority == priority)
    
    if team_id:
        filters.append(Project.team_id == team_id)
    
    if owner_id:
        filters.append(Project.owner_id == owner_id)
    
    if overdue_only:
        filters.append(
            and_(
                Project.due_date < datetime.now(),
                Project.status != ProjectStatus.COMPLETED
            )
        )
    
    if filters:
        query = query.where(and_(*filters))
    
    # Order by priority and due date
    query = query.order_by(
        Project.priority.desc(),
        Project.due_date.asc().nullslast(),
        Project.created_at.desc()
    )
    
    result = await session.execute(query)
    projects = result.scalars().all()
    
    # Serialize for response
    projects_list = [_serialize_project(p) for p in projects]
    
    # Cache the result
    await ProjectCacheService.set_project_list(cache_key, projects_list)
    
    return projects_list


@router.get("/stats", response_model=dict)
async def get_project_stats(
    session: AsyncSession = Depends(get_session_dep),
    user: User = Depends(AnyAuthenticated),
):
    """Get project statistics"""
    
    # Cache key for stats
    cache_key = f"project:stats:user:{user.id}"
    
    # Try cache
    cached_stats = await ProjectCacheService.get_project_list(cache_key)
    if cached_stats:
        print(f"✓ Cache HIT for project stats (user {user.id})")
        return cached_stats
    
    print(f"✗ Cache MISS for project stats (user {user.id})")
    
    # Base query with permissions
    base_query = select(Project)
    if user.role == RoleEnum.EMPLOYEE:
        team_ids = [t.id for t in user.teams]
        if team_ids:
            query = base_query.where(
                or_(
                    Project.owner_id == user.id,
                    Project.team_id.in_(team_ids)
                )
            )
        else:
            query = base_query.where(Project.owner_id == user.id)
    
    # Total projects
    total = await session.scalar(select(func.count()).select_from(base_query.subquery()))
    
    # By status
    by_status = {}
    for proj_status in ProjectStatus:
        count = await session.scalar(
            select(func.count()).select_from(
                base_query.where(Project.status == proj_status).subquery()
            )
        )
        by_status[proj_status.value] = count
    
    # By priority
    by_priority = {}
    for proj_priority in ProjectPriority:
        count = await session.scalar(
            select(func.count()).select_from(
                base_query.where(Project.priority == proj_priority).subquery()
            )
        )
        by_priority[proj_priority.value] = count
    
    # Overdue projects
    overdue = await session.scalar(
        select(func.count()).select_from(
            base_query.where(
                and_(
                    Project.due_date < datetime.now(),
                    Project.status != ProjectStatus.COMPLETED
                )
            ).subquery()
        )
    )
    
    # Average progress
    avg_progress = await session.scalar(
        select(func.avg(Project.progress)).select_from(base_query.subquery())
    )
    
    # Budget totals
    total_budget = await session.scalar(
        select(func.sum(Project.budget)).select_from(base_query.subquery())
    )
    total_spent = await session.scalar(
        select(func.sum(Project.spent)).select_from(base_query.subquery())
    )
    
    stats = {
        "total": total or 0,
        "by_status": by_status,
        "by_priority": by_priority,
        "overdue": overdue or 0,
        "average_progress": round(avg_progress or 0, 2),
        "total_budget": total_budget or 0,
        "total_spent": total_spent or 0,
        "budget_remaining": (total_budget or 0) - (total_spent or 0),
    }
    
    # Cache stats for 2 minutes
    await ProjectCacheService.set_project_list(cache_key, stats, ttl=120)
    
    return stats


@router.get("/{pid}", response_model=ProjectRead)
async def get_project(
    pid: int,
    session: AsyncSession = Depends(get_session_dep),
    user: User = Depends(AnyAuthenticated)
):
    """Get a single project by ID with caching"""
    
    # Try cache first
    cached_project = await ProjectCacheService.get_project(pid)
    if cached_project:
        print(f"✓ Cache HIT for project {pid}")
        
        # Still check permissions for cached data
        if user.role == RoleEnum.EMPLOYEE:
            team_ids = [t.id for t in user.teams]
            if not (cached_project["owner_id"] == user.id or cached_project["team_id"] in team_ids):
                raise HTTPException(status_code=403, detail="Insufficient permissions")
        
        return cached_project
    
    print(f"✗ Cache MISS for project {pid}")
    
    # Query with eager loading
    result = await session.execute(
        select(Project)
        .options(selectinload(Project.team), selectinload(Project.owner))
        .where(Project.id == pid)
    )
    project = result.scalar_one_or_none()
    
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    
    # Check permissions
    if user.role == RoleEnum.EMPLOYEE:
        team_ids = [t.id for t in user.teams]
        if not (project.owner_id == user.id or (project.team_id and project.team_id in team_ids)):
            raise HTTPException(status_code=403, detail="Insufficient permissions")
    
    # Serialize and cache
    project_data = _serialize_project(project)
    await ProjectCacheService.set_project(pid, project_data)
    
    return project_data


@router.patch("/{pid}", response_model=ProjectRead, dependencies=[Depends(CoreOrAdmin)])
async def update_project(
    pid: int,
    payload: ProjectUpdate,
    session: AsyncSession = Depends(get_session_dep)
):
    """Update a project"""
    project = await session.get(Project, pid)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    
    # Update fields
    for key, value in payload.model_dump(exclude_unset=True).items():
        setattr(project, key, value)
    
    # Auto-complete logic
    if payload.status == ProjectStatus.COMPLETED and not project.completed_at:
        project.completed_at = datetime.now()
        project.progress = 100
    
    await session.commit()
    await session.refresh(project)
    
    # Invalidate caches
    await ProjectCacheService.invalidate_project(pid)
    await ProjectCacheService.invalidate_project_lists()
    
    print(f"✓ Project {pid} updated and cache invalidated")
    
    return project


@router.delete("/{pid}", status_code=status.HTTP_204_NO_CONTENT, dependencies=[Depends(CoreOrAdmin)])
async def delete_project(
    pid: int,
    session: AsyncSession = Depends(get_session_dep)
):
    """Delete a project"""
    project = await session.get(Project, pid)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    
    await session.delete(project)
    await session.commit()
    
    # Invalidate caches
    await ProjectCacheService.invalidate_project(pid)
    await ProjectCacheService.invalidate_project_lists()
    
    print(f"✓ Project {pid} deleted and cache invalidated")


@router.patch("/{pid}/archive", response_model=ProjectRead, dependencies=[Depends(CoreOrAdmin)])
async def archive_project(
    pid: int,
    session: AsyncSession = Depends(get_session_dep)
):
    """Archive a project (soft delete)"""
    project = await session.get(Project, pid)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    
    project.is_archived = True
    await session.commit()
    await session.refresh(project)
    
    # Invalidate caches
    await ProjectCacheService.invalidate_project(pid)
    await ProjectCacheService.invalidate_project_lists()
    
    print(f"✓ Project {pid} archived")
    return project


@router.patch("/{pid}/unarchive", response_model=ProjectRead, dependencies=[Depends(CoreOrAdmin)])
async def unarchive_project(
    pid: int,
    session: AsyncSession = Depends(get_session_dep)
):
    """Unarchive a project"""
    project = await session.get(Project, pid)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    
    project.is_archived = False
    await session.commit()
    await session.refresh(project)
    
    # Invalidate caches
    await ProjectCacheService.invalidate_project(pid)
    await ProjectCacheService.invalidate_project_lists()
    
    print(f"✓ Project {pid} unarchived")
    return project


@router.patch("/{pid}/complete", response_model=ProjectRead, dependencies=[Depends(CoreOrAdmin)])
async def complete_project(
    pid: int,
    session: AsyncSession = Depends(get_session_dep)
):
    """Mark project as completed"""
    project = await session.get(Project, pid)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    
    # Use update statement instead of direct assignment
    await session.execute(
        update(Project)
        .where(Project.id == pid)
        .values(
            status=ProjectStatus.COMPLETED,
            progress=100,
            completed_at=datetime.now()
        )
    )
    
    await session.commit()
    await session.refresh(project)
    
    # Invalidate caches
    await ProjectCacheService.invalidate_project(pid)
    await ProjectCacheService.invalidate_project_lists()
    
    print(f"✓ Project {pid} marked as completed")
    return project
