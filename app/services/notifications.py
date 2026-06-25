from datetime import datetime
from email.message import EmailMessage
import smtplib
from sqlmodel import select
from app.schemas import Notification, User
from app.services.database import SessionDependency
from app.config import settings


def send_email(to_email: str, subject: str, body: str) -> None:
    if not settings.SMTP_HOST or not settings.SMTP_FROM_EMAIL:
        raise RuntimeError("SMTP settings are not configured")

    port = settings.SMTP_PORT or (465 if settings.SMTP_USE_SSL else 587)
    message = EmailMessage()
    message["From"] = settings.SMTP_FROM_EMAIL
    message["To"] = to_email
    message["Subject"] = subject
    message.set_content(body)

    if settings.SMTP_USE_SSL:
        smtp_class = smtplib.SMTP_SSL
    else:
        smtp_class = smtplib.SMTP

    with smtp_class(host=settings.SMTP_HOST, port=port, timeout=settings.SMTP_TIMEOUT_SECONDS) as smtp:
        if not settings.SMTP_USE_SSL and settings.SMTP_USE_TLS:
            smtp.starttls()
        if settings.SMTP_USERNAME and settings.SMTP_PASSWORD:
            smtp.login(settings.SMTP_USERNAME, settings.SMTP_PASSWORD)
        smtp.send_message(message)


def create_notification(session: SessionDependency, assignment_id: int, user_id: int, title: str, message: str) -> Notification:
    notification = Notification(
        assignment_id=assignment_id,
        user_id=user_id,
        title=title,
        message=message,
        is_read=False,
        created_at=datetime.utcnow()
    )
    session.add(notification)
    session.commit()
    session.refresh(notification)
    return notification


def get_user_notifications(session: SessionDependency, user_id: int) -> list[Notification]:
    return session.exec(select(Notification).where(Notification.user_id == user_id)).all()


def notify_user_by_email(session: SessionDependency, user_id: int, title: str, message: str) -> None:
    user = session.get(User, user_id)
    if not user or not user.email:
        raise RuntimeError("Cannot send email: user email not found")
    send_email(user.email, title, message)
