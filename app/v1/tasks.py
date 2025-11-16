from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.api.deps import get_session_dep, AnyAuthenticated, CoreOrAdmin
from app.schemas.task import TaskCreate, TaskRead, TaskUpdate
from app.models.task import Task
from app.models.user import User, RoleEnum

router = APIRouter(prefix="/tasks", tags=["tasks"])

@router.post("/", response_model=TaskRead, status_code=status.HTTP_201_CREATED, dependencies=[Depends(CoreOrAdmin)])
async def create_task(payload: TaskCreate, session: AsyncSession = Depends(get_session_dep)):
    t = Task(**payload.model_dump())
    session.add(t)
    await session.commit()
    await session.refresh(t)
    return t

@router.get("/", response_model=list[TaskRead], dependencies=[Depends(AnyAuthenticated)])
async def list_tasks(session: AsyncSession = Depends(get_session_dep), user: User = Depends(AnyAuthenticated)):
    if user.role in (RoleEnum.admin, RoleEnum.core):
        res = (await session.execute(select(Task))).scalars().all()
    else:
        res = (await session.execute(select(Task).where((Task.assignee_id == user.id)))).scalars().all()
    return res

@router.patch("/{tid}", response_model=TaskRead, dependencies=[Depends(AnyAuthenticated)])
async def update_task(tid: int, payload: TaskUpdate, session: AsyncSession = Depends(get_session_dep), user: User = Depends(AnyAuthenticated)):
    t = (await session.execute(select(Task).where(Task.id == tid))).scalar_one_or_none()
    if not t:
        raise HTTPException(status_code=404, detail="Task not found")
    if user.role == RoleEnum.employee and t.assignee_id != user.id:
        raise HTTPException(status_code=403, detail="Insufficient permissions")
    for k, v in payload.model_dump(exclude_unset=True).items():
        setattr(t, k, v)
    await session.commit()
    await session.refresh(t)
    return t

@router.delete("/{tid}", status_code=status.HTTP_204_NO_CONTENT, dependencies=[Depends(CoreOrAdmin)])
async def delete_task(tid: int, session: AsyncSession = Depends(get_session_dep)):
    t = (await session.execute(select(Task).where(Task.id == tid))).scalar_one_or_none()
    if not t:
        raise HTTPException(status_code=404, detail="Task not found")
    await session.delete(t)
    await session.commit()
