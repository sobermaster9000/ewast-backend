# from pydantic import BaseModel

from sqlmodel import SQLModel, Field
from sqlalchemy import Column, JSON

# base barangay class
class BarangayBase(SQLModel):
    name: str = Field(max_length=100)
    bounds_coords: list[tuple[float, float]] = Field(sa_column=Column(JSON, nullable=False, default=[]))

# standard barangay class to be stored in database
class Barangay(BarangayBase, table=True):
    __tablename__: str = "barangays"

    barangay_id: int | None = Field(default=None, primary_key=True)
    ai_summary: str | None = Field(default=None)

# public barangay model to be returned in API calls
class BarangayPublic(BarangayBase):
    barangay_id: int
    ai_summary: str | None

# barangay class for instantiation with JSON input
class BarangayCreate(BarangayBase):
    pass