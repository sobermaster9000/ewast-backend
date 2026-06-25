# from pydantic import BaseModel

from sqlmodel import SQLModel, Field
from sqlalchemy import Column, JSON
from .summary import Theme

# base barangay class
class BarangayBase(SQLModel):
    name: str = Field(unique=True, index=True, max_length=100)
    bounds_coords: list[tuple[float, float]] = Field(sa_column=Column(JSON, nullable=False, default=[]))

# standard barangay class to be stored in database
class Barangay(BarangayBase, table=True):
    __tablename__: str = "barangays"

    barangay_id: int = Field(primary_key=True)
    report_summary: str | None = Field(default=None)
    report_themes: list[Theme] = Field(sa_column=Column(JSON, default=[]))

# public barangay model to be returned in API calls
class BarangayPublic(BarangayBase):
    barangay_id: int

# barangay class for instantiation with JSON input
class BarangayCreate(BarangayBase):
    pass