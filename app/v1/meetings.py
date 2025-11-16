from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.deps import get_session_dep, AnyAuthenticated, CoreOrAdmin
from schemas.meeting import MeetingCreate, MeetingRead, MeetingUpdate, MeetingAttendanceCreate, MeetingAttendanceRead, UserAttendanceCount
from models.meeting import Meeting
from models.user import User, RoleEnum
from models.project import Project
from models.meeting_attendance import MeetingAttendance
from sqlalchemy import func

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
    if user.role in (RoleEnum.ADMIN, RoleEnum.CORE):
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

@router.post("/{mid}/attendance", response_model=list[MeetingAttendanceRead], dependencies=[Depends(CoreOrAdmin)])
async def mark_attendance(mid: int, payload: MeetingAttendanceCreate, session: AsyncSession = Depends(get_session_dep)):
    # Check if meeting exists
    m = (await session.execute(select(Meeting).where(Meeting.id == mid))).scalar_one_or_none()
    if not m:
        raise HTTPException(status_code=404, detail="Meeting not found")

    # Check if users exist
    users = (await session.execute(select(User).where(User.id.in_(payload.user_ids)))).scalars().all()
    if len(users) != len(payload.user_ids):
        raise HTTPException(status_code=400, detail="One or more users not found")

    # Create attendance records
    attendances = []
    for user_id in payload.user_ids:
        attendance = MeetingAttendance(meeting_id=mid, user_id=user_id, attended=True)
        session.add(attendance)
        attendances.append(attendance)

    await session.commit()
    for attendance in attendances:
        await session.refresh(attendance)

    return attendances

@router.get("/{mid}/attendance", response_model=list[MeetingAttendanceRead])
async def get_meeting_attendance(mid: int, session: AsyncSession = Depends(get_session_dep)):
    # Check if meeting exists
    m = (await session.execute(select(Meeting).where(Meeting.id == mid))).scalar_one_or_none()
    if not m:
        raise HTTPException(status_code=404, detail="Meeting not found")

    attendances = (await session.execute(select(MeetingAttendance).where(MeetingAttendance.meeting_id == mid))).scalars().all()
    return attendances

@router.get("/attendance/counts", response_model=list[UserAttendanceCount], dependencies=[Depends(CoreOrAdmin)])
async def get_user_attendance_counts(session: AsyncSession = Depends(get_session_dep)):
    # Get all users with their attendance counts
    result = await session.execute(
        select(
            User.id,
            User.username,
            User.email,
            func.count(MeetingAttendance.id).label("meetings_joined")
        )
        .select_from(User)
        .outerjoin(MeetingAttendance, User.id == MeetingAttendance.user_id)
        .group_by(User.id, User.username, User.email)
    )

    counts = []
    for row in result:
        counts.append(UserAttendanceCount(
            user_id=row.id,
            username=row.username,
            email=row.email,
            meetings_joined=row.meetings_joined
        ))

    return counts
