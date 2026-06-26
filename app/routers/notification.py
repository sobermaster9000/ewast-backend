from fastapi import APIRouter, HTTPException
from sqlmodel import select
from app.schemas import Notification, NotificationPublic
from app.services.database import SessionDependency
from app.services import notifications

router = APIRouter()

@router.get("/notifications/user/{user_id}", response_model=list[NotificationPublic])
def get_notifications(user_id: int, session: SessionDependency) -> list[NotificationPublic]:
    notifications_list = notifications.get_user_notifications(session, user_id)
    return notifications_list

@router.get("/notifications/{notification_id}", response_model=NotificationPublic)
def get_notification(notification_id: int, session: SessionDependency) -> NotificationPublic:
    notification = session.get(Notification, notification_id)
    if not notification:
        raise HTTPException(status_code=404, detail="Notification not found")
    return notification

@router.post("/notifications/{notification_id}/read", response_model=NotificationPublic)
def mark_notification_read(notification_id: int, session: SessionDependency) -> NotificationPublic:
    notification = session.get(Notification, notification_id)
    if not notification:
        raise HTTPException(status_code=404, detail="Notification not found")
    notification.is_read = True
    session.add(notification)
    session.commit()
    session.refresh(notification)
    return notification
