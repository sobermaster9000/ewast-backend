from pydantic import BaseModel
from datetime import datetime
# from typing import Optional
from enum import Enum

from sqlmodel import SQLModel, Field
from sqlalchemy import CheckConstraint, Column, JSON

from fastapi import UploadFile, Form

class AnnouncementBase(SQLModel):
    title: str
    content: str

class Announcement(AnnouncementBase, table=True):
    __tablename__: str = "announcements"

    announcement_id: int | None = Field(default=None, primary_key=True)
    date_published: datetime
    announced_by_user_id: int
    under_barangay_id: int | None = Field(default=None)
    image_url: str | None = Field(default=None, max_length=1000)

class AnnouncementPublic(AnnouncementBase):
    announcement_id: int
    date_published: datetime
    announced_by_user_id: int
    under_barangay_id: int | None = Field(default=None)
    image_url: str | None = Field(default=None, max_length=1000)

class AnnouncementCreate(AnnouncementBase):
    image: UploadFile

# temporary form parsing schema
class AnnouncementFormFields(BaseModel):
    title: str
    content: str

    @classmethod
    def as_form(
        cls,
        title: str = Form(...),
        content: str = Form(...),
    ):
        return cls(
            title=title,
            content=content
        )

