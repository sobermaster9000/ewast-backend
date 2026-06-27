from pydantic import BaseModel, field_validator
from datetime import datetime
from typing import Any, Optional
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
    address: str | None = Field(default=None)

# standard report model to be stored in database
class Report(ReportBase, table=True):
    __tablename__: str = "reports"

    report_id: int | None = Field(default=None, primary_key=True)
    image_url: str | None = Field(default=None, max_length=1000)
    report_summary: str | None = Field(default=None)
    report_themes: list[dict[str, Any]] = Field(sa_column=Column(JSON, default=[]))
    reported_by_user_id: int  # manually verify that this exists in `users` table
    under_barangay_id: int | None = Field(default=None)  # None when coords are outside all barangays
    is_collected: bool = Field(default=False)
    date_reported: datetime

# public report model to be returned in API calls
class ReportPublic(ReportBase):
    report_id: int
    image_url: str | None = Field(default=None, max_length=1000)
    report_summary: str | None = Field(default=None)
    report_themes: list[Theme]
    reported_by_user_id: int  # manually verify that this exists in `users` table
    under_barangay_id: int | None = None  # None when coords are outside all barangays
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

    @field_validator('latitude', mode='before')
    @classmethod
    def validate_latitude(cls, v: Any) -> float:
        """Reject null / non-numeric values with a clear error instead of the
        generic Pydantic message, and clamp to the valid [-90, 90] range."""
        try:
            val = float(v)
        except (TypeError, ValueError):
            raise ValueError('latitude must be a numeric value, not null')
        if not (-90 <= val <= 90):
            raise ValueError('latitude must be between -90 and 90')
        return val

    @field_validator('longitude', mode='before')
    @classmethod
    def validate_longitude(cls, v: Any) -> float:
        """Reject null / non-numeric values with a clear error instead of the
        generic Pydantic message, and clamp to the valid [-180, 180] range."""
        try:
            val = float(v)
        except (TypeError, ValueError):
            raise ValueError('longitude must be a numeric value, not null')
        if not (-180 <= val <= 180):
            raise ValueError('longitude must be between -180 and 180')
        return val

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

class ReportLocation(BaseModel):
    report_id: int
    latitude: float
    longitude: float