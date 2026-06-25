from pydantic import BaseModel
from datetime import datetime
from typing import Any
from enum import Enum

from sqlmodel import SQLModel, Field
from sqlalchemy import CheckConstraint, Column, JSON

from .summary import Theme

from fastapi import UploadFile, Form

# helper enum for report types
class ReportType(str, Enum):
    DRAINAGE_BLOCKAGE = "Drainage Blockage"
    E_WASTE = "E-Waste"
    HAZARDOUS_WASTE = "Hazardous Waste"
    ORGANIC_WASTE = "Organic Waste"
    PLASTIC_WASTE = "Plastic Waste"
    BULKY_WASTE = "Bulky Waste"
    MIXED_WASTE = "Mixed Waste"
    OVERFLOWING_BIN_S = "Overflowing Bin/s"
    ILLEGAL_DUMPING = "Illegal Dumping"

# base report model
class ReportBase(SQLModel):
    type: ReportType
    notes: str | None = Field(default=None)
    latitude: float = Field(sa_column_args=[CheckConstraint("-90 <= latitude AND latitude <= 90")])
    longitude: float = Field(sa_column_args=[CheckConstraint("-180 <= longitude AND longitude <= 180")])

# standard report model to be stored in database
class Report(ReportBase, table=True):
    __tablename__: str = "reports"

    report_id: int | None = Field(default=None, primary_key=True)
    image_url: str | None = Field(default=None, max_length=1000)
    report_summary: str | None = Field(default=None)
    report_themes: list[dict[str, Any]] = Field(sa_column=Column(JSON, default=[]))
    reported_by_user_id: int # manually verify that this exists in `users` table
    under_barangay_id: int
    is_collected: bool = Field(default=False)
    date_reported: datetime

# public report model to be returned in API calls
class ReportPublic(ReportBase):
    report_id: int
    image_url: str | None = Field(default=None, max_length=1000)
    report_summary: str | None = Field(default=None)
    report_themes: list[Theme]
    reported_by_user_id: int # manually verify that this exists in `users` table
    under_barangay_id: int
    is_collected: bool = Field(default=False)
    date_reported: datetime

# report model for instantiation with multipart form input
class ReportCreate(ReportBase):
    image: UploadFile

# temporary form parsing schema
class ReportFormFields(BaseModel):
    type: ReportType
    notes: str | None = None
    latitude: float
    longitude: float

    # this class method allows FastAPI to parse fields from form-data sequentially
    @classmethod
    def as_form(
        cls,
        type: ReportType = Form(...),
        notes: str | None = Form(default=None),
        latitude: float = Form(...),
        longitude: float = Form(...),
    ):
        return cls(
            type=type,
            notes=notes,
            latitude=latitude,
            longitude=longitude
        )