from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from app.deps import AnyAuthenticated, get_session_dep
from models.user import User, RoleEnum
from models.project import Project
from models.task import Task, TaskStatus
from models.revenue import Revenue
from services.cache_service import DashboardCacheService

router = APIRouter(prefix="/dashboard", tags=["dashboards"])


# --------------------------
#   ADMIN DASHBOARD DATA
# --------------------------
async def get_admin_data(session: AsyncSession):
    total_users = (await session.execute(
        select(func.count()).select_from(User)
    )).scalar_one()

    total_projects = (await session.execute(
        select(func.count()).select_from(Project)
    )).scalar_one()

    total_revenue = (await session.execute(
        select(func.coalesce(func.sum(Revenue.amount), 0))
    )).scalar_one()

    tasks_by_status = (await session.execute(
        select(Task.status, func.count()).group_by(Task.status)
    )).all()

    return {
        "total_users": total_users,
        "total_projects": total_projects,
        "total_revenue": float(total_revenue),
        "tasks_by_status": {status.value: count for status, count in tasks_by_status},
    }


# --------------------------
#   CORE DASHBOARD DATA
# --------------------------
async def get_core_data(session: AsyncSession):
    projects = (await session.execute(select(Project))).scalars().all()
    open_tasks = (await session.execute(
        select(Task).where(Task.status != TaskStatus.done)
    )).scalars().all()

    return {
        "projects": [p.id for p in projects],
        "open_tasks": [t.id for t in open_tasks]
    }


# --------------------------
#   EMPLOYEE DASHBOARD DATA
# --------------------------
async def get_employee_data(session: AsyncSession, user: User):
    my_tasks = (await session.execute(
        select(Task).where(Task.assignee_id == user.id)
    )).scalars().all()

    my_projects = (await session.execute(
        select(Project).where(
            Project.team_id.in_([t.id for t in user.teams] or [-1])
        )
    )).scalars().all()

    return {
        "my_task_ids": [t.id for t in my_tasks],
        "my_project_ids": [p.id for p in my_projects]
    }


# --------------------------
#   MAIN DASHBOARD ROUTE
# --------------------------
@router.get("/", dependencies=[Depends(AnyAuthenticated)])
async def common_dashboard(
    session: AsyncSession = Depends(get_session_dep),
    user: User = Depends(AnyAuthenticated)
):
    # User profile summary
    user_data = {
        "id": user.id,
        "email": user.email,
        "name": user.username,
        "role": user.role.value,
    }

    # ------------------- ADMIN -------------------
    if user.role == RoleEnum.ADMIN:
        cached = await DashboardCacheService.get_admin()
        if cached:
            print("✓ Admin dashboard fetched from Redis cache")
            return {"user": user_data, "dashboard": cached}

        dashboard_data = await get_admin_data(session)
        await DashboardCacheService.set_admin(dashboard_data)
        print("✓ Admin dashboard cached")
        return {"user": user_data, "dashboard": dashboard_data}

    # ------------------- CORE -------------------
    elif user.role == RoleEnum.CORE:
        cached = await DashboardCacheService.get_core()
        if cached:
            print("✓ Core dashboard fetched from Redis cache")
            return {"user": user_data, "dashboard": cached}

        dashboard_data = await get_core_data(session)
        await DashboardCacheService.set_core(dashboard_data)
        print("✓ Core dashboard cached")
        return {"user": user_data, "dashboard": dashboard_data}

    # ------------------- EMPLOYEE -------------------
    else:
        cached = await DashboardCacheService.get_employee(user.id)
        if cached:
            print(f"✓ Employee {user.id} dashboard fetched from Redis cache")
            return {"user": user_data, "dashboard": cached}

        dashboard_data = await get_employee_data(session, user)
        await DashboardCacheService.set_employee(user.id, dashboard_data)
        print(f"✓ Employee {user.id} dashboard cached")
        return {"user": user_data, "dashboard": dashboard_data}
