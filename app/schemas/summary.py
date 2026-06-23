from sqlmodel import SQLModel, Field
from sqlalchemy import Column, JSON
from pydantic import BaseModel

class Summary(SQLModel, table=True):
    summary_id: int | None = Field(default=None, primary_key=True)
    general_summary: str | None = Field(default=None)
    general_themes: list[str] = Field(sa_column=Column(JSON, default=[]))

class GeneralSummary(BaseModel):
    general_summary: str

class BarangaySummary(BaseModel):
    barangay_id: int
    barangay_summary: str