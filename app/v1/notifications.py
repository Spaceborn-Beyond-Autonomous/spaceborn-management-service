# app/v1/notifications.py
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, delete
from typing import List
from app.deps import get_session_dep, AnyAuthenticated
from models.notification import Notification
from models.user import User
from schemas.notification import NotificationResponse

router = APIRouter(prefix="/notifications", tags=["notifications"])

@router.get("/", response_model=List[NotificationResponse])
async def get_my_notifications(
    session: AsyncSession = Depends(get_session_dep),
    user: User = Depends(AnyAuthenticated)
):
    # Fetch notifications for current user, newest first
    result = await session.execute(
        select(Notification)
        .where(Notification.user_id == user.id)
        .order_by(Notification.created_at.desc())
        .limit(20) # Limit to last 20 to keep header light
    )
    return result.scalars().all()

@router.patch("/{notif_id}/read")
async def mark_as_read(
    notif_id: int,
    session: AsyncSession = Depends(get_session_dep),
    user: User = Depends(AnyAuthenticated)
):
    # Verify ownership and update
    result = await session.execute(
        select(Notification).where(Notification.id == notif_id, Notification.user_id == user.id)
    )
    notification = result.scalar_one_or_none()
    
    if not notification:
        raise HTTPException(status_code=404, detail="Notification not found")

    notification.is_read = True
    await session.commit()
    return {"message": "Marked as read"}

@router.patch("/read-all")
async def mark_all_read(
    session: AsyncSession = Depends(get_session_dep),
    user: User = Depends(AnyAuthenticated)
):
    await session.execute(
        update(Notification)
        .where(Notification.user_id == user.id, Notification.is_read == False)
        .values(is_read=True)
    )
    await session.commit()
    return {"message": "All notifications marked as read"}

@router.delete("/{notif_id}")
async def delete_notification(
    notif_id: int,
    session: AsyncSession = Depends(get_session_dep),
    user: User = Depends(AnyAuthenticated)
):
    await session.execute(
        delete(Notification).where(Notification.id == notif_id, Notification.user_id == user.id)
    )
    await session.commit()
    return {"message": "Deleted"}