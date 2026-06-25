from datetime import datetime

from sqlmodel import SQLModel, Field


class NotificationBase(SQLModel):
    assignment_id: int
    user_id: int
    title: str
    message: str
    is_read: bool = Field(default=False)
    created_at: datetime = Field(default_factory=datetime.utcnow)


class Notification(NotificationBase, table=True):
    __tablename__: str = "notifications"

    notification_id: int | None = Field(default=None, primary_key=True)


class NotificationPublic(NotificationBase):
    notification_id: int


class NotificationCreate(NotificationBase):
    pass
