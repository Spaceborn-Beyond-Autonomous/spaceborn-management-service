from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.api.deps import get_session_dep, CoreOrAdmin, AnyAuthenticated
from app.schemas.project import ProjectCreate, ProjectRead, ProjectUpdate
from app.models.project import Project
from app.models.user import User, RoleEnum

router = APIRouter(prefix="/projects", tags=["projects"])

@router.post("/", response_model=ProjectRead, status_code=status.HTTP_201_CREATED, dependencies=[Depends(CoreOrAdmin)])
async def create_project(payload: ProjectCreate, session: AsyncSession = Depends(get_session_dep)):
    p = Project(**payload.model_dump())
    session.add(p)
    await session.commit()
    await session.refresh(p)
    return p

@router.get("/", response_model=list[ProjectRead], dependencies=[Depends(AnyAuthenticated)])
async def list_projects(session: AsyncSession = Depends(get_session_dep), user: User = Depends(AnyAuthenticated)):
    if user.role in (RoleEnum.admin, RoleEnum.core):
        res = (await session.execute(select(Project))).scalars().all()
    else:
        # employee: projects they own or their team projects (through membership)
        res = (await session.execute(select(Project).where(
            (Project.owner_id == user.id) | (Project.team_id.in_([t.id for t in user.teams]))
        ))).scalars().all()
    return res

@router.get("/{pid}", response_model=ProjectRead, dependencies=[Depends(AnyAuthenticated)])
async def get_project(pid: int, session: AsyncSession = Depends(get_session_dep), user: User = Depends(AnyAuthenticated)):
    p = (await session.execute(select(Project).where(Project.id == pid))).scalar_one_or_none()
    if not p:
        raise HTTPException(status_code=404, detail="Project not found")
    if user.role == RoleEnum.employee and not (p.owner_id == user.id or (p.team_id and p.team_id in [t.id for t in user.teams])):
        raise HTTPException(status_code=403, detail="Insufficient permissions")
    return p

@router.patch("/{pid}", response_model=ProjectRead, dependencies=[Depends(CoreOrAdmin)])
async def update_project(pid: int, payload: ProjectUpdate, session: AsyncSession = Depends(get_session_dep)):
    p = (await session.execute(select(Project).where(Project.id == pid))).scalar_one_or_none()
    if not p:
        raise HTTPException(status_code=404, detail="Project not found")
    for k, v in payload.model_dump(exclude_unset=True).items():
        setattr(p, k, v)
    await session.commit()
    await session.refresh(p)
    return p

@router.delete("/{pid}", status_code=status.HTTP_204_NO_CONTENT, dependencies=[Depends(CoreOrAdmin)])
async def delete_project(pid: int, session: AsyncSession = Depends(get_session_dep)):
    p = (await session.execute(select(Project).where(Project.id == pid))).scalar_one_or_none()
    if not p:
        raise HTTPException(status_code=404, detail="Project not found")
    await session.delete(p)
    await session.commit()
