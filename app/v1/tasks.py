from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, text
from app.deps import AnyAuthenticated, CoreOrAdmin
from schemas.task import TaskCreate, TaskRead, TaskUpdate
from models.task import Task
from models.user import User, RoleEnum
from db.session import get_async_session

router = APIRouter(prefix="/tasks", tags=["tasks"])

@router.get("/debug_enum")
async def debug_enum(session: AsyncSession = Depends(get_async_session)):
    result = await session.execute(text("SELECT unnest(enum_range(NULL::task_status_enum));"))
    return result.scalars().all()


@router.post("/", response_model=TaskRead, status_code=status.HTTP_201_CREATED, dependencies=[Depends(CoreOrAdmin)])
async def create_task(payload: TaskCreate, session: AsyncSession = Depends(get_async_session)):
    t = Task(**payload.model_dump())
    session.add(t)
    await session.commit()
    await session.refresh(t)
    return t


@router.get("/", response_model=list[TaskRead], dependencies=[Depends(AnyAuthenticated)])
async def list_tasks(session: AsyncSession = Depends(get_async_session), user: User = Depends(AnyAuthenticated)):
    if user.role in (RoleEnum.ADMIN, RoleEnum.CORE):
        res = (await session.execute(select(Task))).scalars().all()
    else:
        res = (await session.execute(select(Task).where(Task.assignee_id == user.id))).scalars().all()
    return res


@router.patch("/{tid}", response_model=TaskRead, dependencies=[Depends(AnyAuthenticated)])
async def update_task(tid: int, payload: TaskUpdate, session: AsyncSession = Depends(get_async_session), user: User = Depends(AnyAuthenticated)):
    t = (await session.execute(select(Task).where(Task.id == tid))).scalar_one_or_none()
    if not t:
        raise HTTPException(status_code=404, detail="Task not found")
    if user.role == RoleEnum.EMPLOYEE and t.assignee_id != user.id:
        raise HTTPException(status_code=403, detail="Insufficient permissions")
    for k, v in payload.model_dump(exclude_unset=True).items():
        setattr(t, k, v)
    await session.commit()
    await session.refresh(t)
    return t


@router.delete("/{tid}", status_code=status.HTTP_204_NO_CONTENT, dependencies=[Depends(CoreOrAdmin)])
async def delete_task(tid: int, session: AsyncSession = Depends(get_async_session)):
    t = (await session.execute(select(Task).where(Task.id == tid))).scalar_one_or_none()
    if not t:
        raise HTTPException(status_code=404, detail="Task not found")
    await session.delete(t)
    await session.commit()
