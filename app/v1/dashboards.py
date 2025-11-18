from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from app.deps import AnyAuthenticated, CoreOrAdmin, get_session_dep
from models.user import User, RoleEnum
from models.project import Project
from models.task import Task, TaskStatus
from models.revenue import Revenue
from schemas.user import UserRead

router = APIRouter(prefix="/dashboard", tags=["dashboards"])

async def get_admin_data(session: AsyncSession):
    total_users = (await session.execute(select(func.count()).select_from(User))).scalar_one()
    total_projects = (await session.execute(select(func.count()).select_from(Project))).scalar_one()
    total_revenue = (await session.execute(select(func.coalesce(func.sum(Revenue.amount), 0)))).scalar_one()
    tasks_by_status = (await session.execute(
        select(Task.status, func.count()).group_by(Task.status)
    )).all()
    return {
        "total_users": total_users,
        "total_projects": total_projects,
        "total_revenue": float(total_revenue),
        "tasks_by_status": {status.value: count for status, count in tasks_by_status},
    }

async def get_core_data(session: AsyncSession):
    projects = (await session.execute(select(Project))).scalars().all()
    open_tasks = (await session.execute(select(Task).where(Task.status != TaskStatus.done))).scalars().all()
    return {"projects": [p.id for p in projects], "open_tasks": [t.id for t in open_tasks]}

async def get_employee_data(session: AsyncSession, user: User):
    my_tasks = (await session.execute(select(Task).where(Task.assignee_id == user.id))).scalars().all()
    my_projects = (await session.execute(select(Project).where(
        (Project.team_id.in_([t.id for t in user.teams] or [-1]))
    ))).scalars().all()
    return {"my_task_ids": [t.id for t in my_tasks], "my_project_ids": [p.id for p in my_projects]}

@router.get("/", dependencies=[Depends(AnyAuthenticated)])
async def common_dashboard(session: AsyncSession = Depends(get_session_dep), user: User = Depends(AnyAuthenticated)):
    # Include user data in the response
    user_data = {
        "id": user.id,
        "email": user.email,
        "name": user.username,
        "role": user.role.value,
    }
    
    if user.role == RoleEnum.ADMIN:
        dashboard_data = await get_admin_data(session)
    elif user.role == RoleEnum.CORE:
        dashboard_data = await get_core_data(session)
    else:  # EMPLOYEE
        dashboard_data = await get_employee_data(session, user)
    
    return {
        "user": user_data,
        "dashboard": dashboard_data
    }
