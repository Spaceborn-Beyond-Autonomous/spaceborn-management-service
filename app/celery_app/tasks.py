from celery import shared_task
from sqlalchemy.orm import Session
from app.db.database import SessionLocal
from app.db.models import User, Meeting
from fastapi_mail import MessageSchema
from app.core.email import fm
from app.core.settings import settings
import traceback
import logging
from models import Team, User, meeting

logger = logging.getLogger("celery")

# Utility: DB Session
def get_db():
    db = SessionLocal()
    try:
        return db
    finally:
        db.close()

@shared_task(bind=True, max_retries=3, name="send_account_credentials")
def send_account_credentials(self, email: str):
    db: Session = get_db()
    try:
        user: User = db.query(User).filter(User.alternative_email == email).first()
        if not user:
            raise Exception("User not found")

        # ---- RESET LINK ----
        reset_link = f"{settings.FRONTEND_URL}/reset-password/{user.id}/token123/"

        html = f"""
        <p>Hi <b>{user.full_name}</b>,</p>
        <p>Your account has been created on Spaceborn.</p>
        <p><b>Login Email:</b> {user.email}</p>
        <p><b>Set Password:</b> <a href="{reset_link}">Click here</a></p>
        """

        message = MessageSchema(
            subject="Welcome to Spaceborn - Set Your Password",
            recipients=[user.email],
            body=html,
            subtype="html"
        )

        fm.send_message(message)
        return f"Email sent to {user.email}"

    except Exception as e:
        logger.error(f"Error: {e}\n{traceback.format_exc()}")
        raise self.retry(exc=e, countdown=60)


@shared_task(bind=True, name="send_meeting_reminder")
def meeting_reminder(self, meeting_id: int):
    db = get_db()
    try:
        meeting: Meeting = db.query(meeting).filter(meeting.id == meeting_id).first()
        if not meeting:
            return "Meeting not found"

        team_members = (
            db.query(User)
            .join(Team, Team.id == meeting.team_id)
            .all()
        )

        if not team_members:
            return "No members in team"

        for member in team_members:
            body = f"""
            Hi {member.full_name},
            This is a reminder for the upcoming meeting:

            Title: {meeting.title}
            Date: {meeting.date}
            Time: {meeting.start_time}
            Link: {meeting.link}
            """

            msg = MessageSchema(
                subject=f"Meeting Reminder: {meeting.title}",
                recipients=[member.email],
                body=body,
                subtype="plain"
            )

            fm.send_message(msg)

        return f"Sent {len(team_members)} reminders."

    except Exception as e:
        logger.error(str(e))
        raise self.retry(exc=e, countdown=120)
