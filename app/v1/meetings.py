from fastapi import APIRouter, Body, Depends, HTTPException, Path, Query, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import delete, select
from sqlalchemy.orm import selectinload
from app.deps import get_session_dep, AnyAuthenticated, CoreOrAdmin
from schemas.meeting import MeetingCreate, MeetingRead, MeetingUpdate, MeetingAttendanceCreate, MeetingAttendanceRead, UserAttendanceCount
from models.meeting import Meeting
from models.user import User, RoleEnum
from models.project import Project
from models.meeting_attendance import MeetingAttendance
from sqlalchemy import func
from typing import List


router = APIRouter(prefix="/meetings", tags=["meetings"])


@router.post(
    "/",
    response_model=MeetingRead,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(CoreOrAdmin)],
    summary="Create a new meeting",
    description="Create a new meeting with optional attendees.",
    responses={
        201: {"description": "Meeting created successfully"},
        400: {"description": "Invalid input data"},
        401: {"description": "Unauthorized - Authentication required"},
        403: {"description": "Forbidden - Core or Admin role required"}
    }
)
async def create_meeting(
    payload: MeetingCreate = Body(..., description="Meeting details including attendees"),
    session: AsyncSession = Depends(get_session_dep)
):
    """
    Create a new meeting.
    
    - **title**: Meeting title (required)
    - **agenda**: Meeting agenda/description (optional)
    - **scheduled_at**: ISO datetime string (required)
    - **attendees**: List of user IDs to invite (optional)
    - **meeting_link**: Virtual meeting URL (optional)
    - **organizer**: Name of the organizer (optional)
    - **reminder_interval**: Minutes before meeting to send reminder (default: 15)
    - **notes**: Additional notes (optional)
    """
    
    # Create meeting instance, excluding attendees (handled separately)
    meeting_data = payload.model_dump(exclude={'attendees'})
    m = Meeting(**meeting_data)
    
    # Save the meeting to get its ID
    session.add(m)
    await session.commit()
    await session.refresh(m)
    
    # Add attendees through the association table if provided
    if payload.attendees:
        for user_id in payload.attendees:
            attendance = MeetingAttendance(
                meeting_id=m.id,
                user_id=user_id,
                attended=True  # Default to True for invited attendees
            )
            session.add(attendance)
        await session.commit()
    
    # Eagerly load attendances and nested user data to avoid MissingGreenlet error
    result = await session.execute(
        select(Meeting)
        .options(
            selectinload(Meeting.attendances).selectinload(MeetingAttendance.user)
        )
        .where(Meeting.id == m.id)
    )
    meeting = result.scalar_one()
    
    return meeting


@router.get(
    "/",
    response_model=List[MeetingRead],
    status_code=status.HTTP_200_OK,
    dependencies=[Depends(AnyAuthenticated)],
    summary="List all meetings",
    description="Retrieve all meetings ordered by scheduled time (most recent first).",
    responses={
        200: {"description": "List of meetings retrieved successfully"},
        401: {"description": "Unauthorized - Authentication required"}
    }
)
async def list_meetings(
    session: AsyncSession = Depends(get_session_dep)
):
    """
    Get all meetings with their attendees.
    
    Meetings are ordered by scheduled_at in descending order (newest first).
    Each meeting includes full attendee information.
    """
    
    # Fetch all meetings with eagerly loaded attendances and users
    result = await session.execute(
        select(Meeting)
        .options(
            selectinload(Meeting.attendances).selectinload(MeetingAttendance.user)
        )
        .order_by(Meeting.scheduled_at.desc())
    )
    meetings = result.scalars().all()
    
    return meetings


@router.get(
    "/{mid}",
    response_model=MeetingRead,
    status_code=status.HTTP_200_OK,
    dependencies=[Depends(AnyAuthenticated)],
    summary="Get a single meeting",
    description="Retrieve detailed information about a specific meeting.",
    responses={
        200: {"description": "Meeting retrieved successfully"},
        404: {"description": "Meeting not found"},
        401: {"description": "Unauthorized - Authentication required"}
    }
)
async def get_meeting(
    mid: int = Path(..., description="The ID of the meeting to retrieve", ge=1),
    session: AsyncSession = Depends(get_session_dep)
):
    """
    Get a meeting by ID.
    
    - **mid**: Meeting ID (path parameter)
    
    Returns full meeting details including all attendees.
    """
    
    # Fetch meeting with eagerly loaded relationships
    result = await session.execute(
        select(Meeting)
        .options(
            selectinload(Meeting.attendances).selectinload(MeetingAttendance.user)
        )
        .where(Meeting.id == mid)
    )
    meeting = result.scalar_one_or_none()
    
    # Return 404 if meeting doesn't exist
    if not meeting:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Meeting with ID {mid} not found"
        )
    
    return meeting


@router.patch(
    "/{mid}",
    response_model=MeetingRead,
    status_code=status.HTTP_200_OK,
    dependencies=[Depends(CoreOrAdmin)],
    summary="Update a meeting",
    description="Update an existing meeting's details and attendees. Only provided fields will be updated.",
    responses={
        200: {"description": "Meeting updated successfully"},
        404: {"description": "Meeting not found"},
        401: {"description": "Unauthorized - Authentication required"},
        403: {"description": "Forbidden - Core or Admin role required"}
    }
)
async def update_meeting(
    mid: int = Path(..., description="The ID of the meeting to update", ge=1),
    payload: MeetingUpdate = Body(..., description="Fields to update"),
    session: AsyncSession = Depends(get_session_dep)
):
    """
    Update a meeting by ID.
    
    - **mid**: Meeting ID (path parameter)
    - **title**: Meeting title (optional)
    - **agenda**: Meeting agenda/description (optional)
    - **scheduled_at**: ISO datetime string (optional)
    - **attendees**: List of user IDs to assign as attendees (optional)
    - **meeting_link**: Virtual meeting URL (optional)
    - **organizer**: Name of the organizer (optional)
    - **reminder_interval**: Minutes before meeting to send reminder (optional)
    - **notes**: Additional notes (optional)
    
    All fields are optional. Only provided fields will be updated.
    """
    
    # Fetch the meeting from database
    result = await session.execute(
        select(Meeting).where(Meeting.id == mid)
    )
    m = result.scalar_one_or_none()
    
    # Return 404 if meeting doesn't exist
    if not m:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Meeting with ID {mid} not found"
        )
    
    # Extract update data, excluding 'attendees' to handle separately
    # exclude_unset=True ensures only provided fields are updated
    update_data = payload.model_dump(exclude_unset=True, exclude={'attendees'})
    
    # Update basic fields (title, agenda, scheduled_at, etc.)
    for field_name, field_value in update_data.items():
        setattr(m, field_name, field_value)
    
    # Commit basic field updates
    await session.commit()
    
    # Handle attendees update if provided in payload
    if payload.attendees is not None:
        # Get current attendee user IDs
        existing_result = await session.execute(
            select(MeetingAttendance.user_id)
            .where(MeetingAttendance.meeting_id == mid)
        )
        existing_ids = set(existing_result.scalars().all())
        new_ids = set(payload.attendees)
        
        # Determine which attendees to remove
        to_remove = existing_ids - new_ids
        if to_remove:
            await session.execute(
                delete(MeetingAttendance)
                .where(
                    MeetingAttendance.meeting_id == mid,
                    MeetingAttendance.user_id.in_(to_remove)
                )
            )
        
        # Determine which attendees to add
        to_add = new_ids - existing_ids
        for user_id in to_add:
            attendance = MeetingAttendance(
                meeting_id=mid,
                user_id=user_id,
                attended=True  # Default to True, can be updated later
            )
            session.add(attendance)
        
        # Commit attendee changes
        await session.commit()
    
    # Eagerly load relationships to avoid MissingGreenlet error during serialization
    # This ensures attendances and nested user data are loaded before returning
    result = await session.execute(
        select(Meeting)
        .options(
            selectinload(Meeting.attendances).selectinload(MeetingAttendance.user)
        )
        .where(Meeting.id == mid)
    )
    meeting = result.scalar_one()
    
    return meeting


@router.delete(
    "/{mid}",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[Depends(CoreOrAdmin)],
    summary="Delete a meeting",
    description="Permanently delete a meeting and all associated attendance records.",
    responses={
        204: {"description": "Meeting deleted successfully"},
        404: {"description": "Meeting not found"},
        401: {"description": "Unauthorized - Authentication required"},
        403: {"description": "Forbidden - Core or Admin role required"}
    }
)
async def delete_meeting(
    mid: int = Path(..., description="The ID of the meeting to delete", ge=1),
    session: AsyncSession = Depends(get_session_dep)
):
    """
    Delete a meeting by ID.
    
    This will also cascade delete all related attendance records.
    
    - **mid**: Meeting ID (path parameter)
    
    Returns 204 No Content on success.
    """
    
    # Fetch the meeting from database
    result = await session.execute(
        select(Meeting).where(Meeting.id == mid)
    )
    m = result.scalar_one_or_none()
    
    # Return 404 if meeting doesn't exist
    if not m:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Meeting with ID {mid} not found"
        )
    
    # Delete the meeting (cascade will handle attendances)
    await session.delete(m)
    await session.commit()
    
    # No return needed for 204 status


@router.post(
    "/{mid}/attendance",
    response_model=List[MeetingAttendanceRead],
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(CoreOrAdmin)],
    summary="Mark attendance for a meeting",
    description="Add attendance records for multiple users for a specific meeting.",
    responses={
        201: {"description": "Attendance marked successfully"},
        400: {"description": "Invalid input - No attendees provided or users not found"},
        404: {"description": "Meeting not found"},
        401: {"description": "Unauthorized - Authentication required"},
        403: {"description": "Forbidden - Core or Admin role required"}
    }
)
async def mark_attendance(
    mid: int = Path(..., description="The ID of the meeting", ge=1),
    payload: MeetingAttendanceCreate = Body(..., description="List of user IDs to mark as attended"),
    session: AsyncSession = Depends(get_session_dep)
):
    """
    Mark attendance for users in a meeting.
    
    - **mid**: Meeting ID (path parameter)
    - **attendees**: List of user IDs who attended the meeting
    
    Creates attendance records for the specified users.
    """
    
    # Verify meeting exists
    result = await session.execute(
        select(Meeting).where(Meeting.id == mid)
    )
    m = result.scalar_one_or_none()
    
    if not m:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Meeting with ID {mid} not found"
        )
    
    # Validate payload has attendees
    if not payload.attendees:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No attendees provided"
        )
    
    # Verify all users exist
    users_result = await session.execute(
        select(User).where(User.id.in_(payload.attendees))
    )
    users = users_result.scalars().all()
    
    if len(users) != len(payload.attendees):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="One or more users not found"
        )
    
    # Create attendance records
    attendances = []
    for user_id in payload.attendees:
        attendance = MeetingAttendance(
            meeting_id=mid,
            user_id=user_id,
            attended=True
        )
        session.add(attendance)
        attendances.append(attendance)
    
    # Commit and refresh all attendance records
    await session.commit()
    for attendance in attendances:
        await session.refresh(attendance)
    
    return attendances


@router.get(
    "/{mid}/attendance",
    response_model=List[MeetingAttendanceRead],
    status_code=status.HTTP_200_OK,
    dependencies=[Depends(AnyAuthenticated)],
    summary="Get meeting attendance",
    description="Retrieve all attendance records for a specific meeting.",
    responses={
        200: {"description": "Attendance records retrieved successfully"},
        404: {"description": "Meeting not found"},
        401: {"description": "Unauthorized - Authentication required"}
    }
)
async def get_meeting_attendance(
    mid: int = Path(..., description="The ID of the meeting", ge=1),
    session: AsyncSession = Depends(get_session_dep)
):
    """
    Get all attendance records for a meeting.
    
    - **mid**: Meeting ID (path parameter)
    
    Returns list of all users who attended the meeting.
    """
    
    # Verify meeting exists
    result = await session.execute(
        select(Meeting).where(Meeting.id == mid)
    )
    m = result.scalar_one_or_none()
    
    if not m:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Meeting with ID {mid} not found"
        )
    
    # Fetch all attendance records for this meeting
    attendances_result = await session.execute(
        select(MeetingAttendance).where(MeetingAttendance.meeting_id == mid)
    )
    attendances = attendances_result.scalars().all()
    
    return attendances


@router.get(
    "/attendance/counts",
    response_model=List[UserAttendanceCount],
    status_code=status.HTTP_200_OK,
    dependencies=[Depends(CoreOrAdmin)],
    summary="Get user attendance statistics",
    description="Retrieve attendance counts for all users across all meetings.",
    responses={
        200: {"description": "Attendance statistics retrieved successfully"},
        401: {"description": "Unauthorized - Authentication required"},
        403: {"description": "Forbidden - Core or Admin role required"}
    }
)
async def get_user_attendance_counts(
    session: AsyncSession = Depends(get_session_dep)
):
    """
    Get attendance statistics for all users.
    
    Returns a list of all users with their total meeting attendance count.
    Users with no attendance records will show 0 meetings joined.
    """
    
    # Query all users with their attendance counts using LEFT JOIN
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
        .order_by(func.count(MeetingAttendance.id).desc())  # Order by most active
    )
    
    # Transform database rows into Pydantic models
    counts = []
    for row in result:
        counts.append(UserAttendanceCount(
            user_id=row.id,
            username=row.username,
            email=row.email,
            meetings_joined=row.meetings_joined
        ))
    
    return counts
