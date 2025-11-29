from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from app.deps import AnyAuthenticated, get_session_dep
from models.user import User, RoleEnum
from models.team import team_members 
from models.project import Project
from models.task import Task, TaskStatus
from models.revenue import Revenue
from services.cache_service import DashboardCacheService

router = APIRouter(prefix="/dashboard", tags=["dashboards"])

# --------------------------
#   ADMIN DASHBOARD DATA
# --------------------------
async def get_admin_data(session: AsyncSession):
    # 1. Users
    q_users = select(func.count()).select_from(User)
    total_users = (await session.execute(q_users)).scalar_one()

    # 2. Projects
    q_projects = select(func.count()).select_from(Project)
    total_projects = (await session.execute(q_projects)).scalar_one()

    # 3. Revenue
    q_revenue = select(func.coalesce(func.sum(Revenue.amount), 0))
    total_revenue = (await session.execute(q_revenue)).scalar_one()

    # 4. Task Status
    q_tasks = select(Task.status, func.count()).group_by(Task.status)
    tasks_status_result = (await session.execute(q_tasks)).all()

    return {
        "total_users": total_users,
        "total_projects": total_projects,
        "total_revenue": float(total_revenue),
        "tasks_by_status": {status.value: count for status, count in tasks_status_result},
    }


# --------------------------
#   CORE DASHBOARD DATA
# --------------------------
async def get_core_data(session: AsyncSession):
    # 1. Projects
    q_projects = select(Project.id, Project.name)
    projects_res = (await session.execute(q_projects)).all()

    # 2. Open Tasks
    q_tasks = select(Task.id, Task.title).where(Task.status != TaskStatus.done)
    tasks_res = (await session.execute(q_tasks)).all()

    return {
        "projects": [{"id": r.id, "name": r.name} for r in projects_res],
        "open_tasks": [{"id": r.id, "title": r.title} for r in tasks_res]
    }


# --------------------------
#   EMPLOYEE DASHBOARD DATA
# --------------------------
async def get_employee_data(session: AsyncSession, user_id: int):
    # 1. My Tasks
    q_tasks = select(Task.id, Task.title, Task.status).where(Task.assignee_id == user_id)
    tasks_res = (await session.execute(q_tasks)).all()

    # 2. My Projects (via Team Members association)
    q_projects = (
        select(Project.id, Project.name)
        .join(team_members, team_members.c.team_id == Project.team_id)
        .where(team_members.c.user_id == user_id)
    )
    projects_res = (await session.execute(q_projects)).all()

    return {
        "my_tasks": [{"id": r.id, "title": r.title, "status": r.status.value} for r in tasks_res],
        "my_projects": [{"id": r.id, "name": r.name} for r in projects_res]
    }


# --------------------------
#   MAIN ROUTE
# --------------------------
@router.get("/", dependencies=[Depends(AnyAuthenticated)])
async def common_dashboard(
    session: AsyncSession = Depends(get_session_dep),
    user: User = Depends(AnyAuthenticated)
):
    user_data = {
        "id": user.id,
        "email": user.email,
        "name": user.username,
        "role": user.role.value,
    }

    async def fetch_and_cache(role_key: str, fetch_func, *args):
        # 1. Check Cache
        if role_key == "admin":
            cached = await DashboardCacheService.get_admin()
        elif role_key == "core":
            cached = await DashboardCacheService.get_core()
        else:
            cached = await DashboardCacheService.get_employee(user.id)
            
        if cached:
            return {"user": user_data, "dashboard": cached}
        
        # 2. Fetch Fresh Data
        data = await fetch_func(*args)
        
        # 3. Set Cache
        if role_key == "admin":
            await DashboardCacheService.set_admin(data)
        elif role_key == "core":
            await DashboardCacheService.set_core(data)
        else:
            await DashboardCacheService.set_employee(user.id, data)
            
        return {"user": user_data, "dashboard": data}

    if user.role == RoleEnum.ADMIN:
        return await fetch_and_cache("admin", get_admin_data, session)
    elif user.role == RoleEnum.CORE:
        return await fetch_and_cache("core", get_core_data, session)
    else:
        return await fetch_and_cache("employee", get_employee_data, session, user.id)