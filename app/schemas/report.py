# from pydantic import BaseModel
from datetime import datetime
# from typing import Optional
from enum import Enum

from sqlmodel import SQLModel, Field
from sqlalchemy import CheckConstraint

from fastapi import UploadFile

# helper enum for report types
class ReportType(str, Enum):
    DUMMY = "dummy" # change to proper report types

# base report model
class ReportBase(SQLModel):
    type: ReportType
    notes: str | None = Field(default=None)
    latitude: float = Field(sa_column_args=[CheckConstraint("-180 <= latitude AND latitude <= 180")])
    longitude: float = Field(sa_column_args=[CheckConstraint("-90 <= longitude AND longitude <= 90")])

# standard report model to be stored in database
class Report(ReportBase, table=True):
    __tablename__: str = "reports"

    report_id: int = Field(primary_key=True)
    image_url: str | None = Field(default=None, max_length=1000)
    ai_summary: str | None = Field(default=None)
    reported_by_user_id: int # manually verify that this exists in `users` table
    is_collected: bool = Field(default=False)
    date_reported: datetime

# public report model to be returned in API calls
class ReportPublic(ReportBase):
    report_id: int
    image_url: str | None = Field(default=None, max_length=1000)
    ai_summary: str | None = Field(default=None)
    reported_by_user_id: int # manually verify that this exists in `users` table
    is_collected: bool = Field(default=False)
    date_reported: datetime

# report model for instantiation with multipart form input
class ReportCreate(ReportBase):
    image: UploadFile