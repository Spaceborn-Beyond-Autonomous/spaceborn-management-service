from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.api.deps import get_session_dep, AnyAuthenticated, CoreOrAdmin
from app.schemas.meeting import MeetingCreate, MeetingRead, MeetingUpdate
from app.models.meeting import Meeting
from app.models.user import User, RoleEnum
from app.models.project import Project

router = APIRouter(prefix="/meetings", tags=["meetings"])

@router.post("/", response_model=MeetingRead, status_code=status.HTTP_201_CREATED, dependencies=[Depends(CoreOrAdmin)])
async def create_meeting(payload: MeetingCreate, session: AsyncSession = Depends(get_session_dep)):
    p = (await session.execute(select(Project).where(Project.id == payload.project_id))).scalar_one_or_none()
    if not p:
        raise HTTPException(status_code=404, detail="Project not found")
    m = Meeting(**payload.model_dump())
    session.add(m)
    await session.commit()
    await session.refresh(m)
    return m

@router.get("/", response_model=list[MeetingRead], dependencies=[Depends(AnyAuthenticated)])
async def list_meetings(session: AsyncSession = Depends(get_session_dep), user: User = Depends(AnyAuthenticated)):
    if user.role in (RoleEnum.admin, RoleEnum.core):
        res = (await session.execute(select(Meeting))).scalars().all()
    else:
        # employee: meetings of their projects/teams — simplified visibility
        res = (await session.execute(select(Meeting))).scalars().all()
    return res

@router.patch("/{mid}", response_model=MeetingRead, dependencies=[Depends(CoreOrAdmin)])
async def update_meeting(mid: int, payload: MeetingUpdate, session: AsyncSession = Depends(get_session_dep)):
    m = (await session.execute(select(Meeting).where(Meeting.id == mid))).scalar_one_or_none()
    if not m:
        raise HTTPException(status_code=404, detail="Meeting not found")
    for k, v in payload.model_dump(exclude_unset=True).items():
        setattr(m, k, v)
    await session.commit()
    await session.refresh(m)
    return m

@router.delete("/{mid}", status_code=status.HTTP_204_NO_CONTENT, dependencies=[Depends(CoreOrAdmin)])
async def delete_meeting(mid: int, session: AsyncSession = Depends(get_session_dep)):
    m = (await session.execute(select(Meeting).where(Meeting.id == mid))).scalar_one_or_none()
    if not m:
        raise HTTPException(status_code=404, detail="Meeting not found")
    await session.delete(m)
    await session.commit()
