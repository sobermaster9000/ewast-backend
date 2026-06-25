from sqlmodel import SQLModel, Field
from sqlalchemy import Column, JSON
from pydantic import BaseModel
from typing import Any

class Theme(BaseModel):
    title: str
    codes: list[str]

class Summary(SQLModel, table=True):
    summary_id: int | None = Field(default=None, primary_key=True)
    general_summary: str | None = Field(default=None)
    general_themes: list[dict[str, Any]] = Field(sa_column=Column(JSON, default=[]))

class SummaryPublic(BaseModel):
    summary_id: int
    general_summary: str | None
    general_themes: list[Theme]

class GeneralSummary(BaseModel):
    general_summary: str

class BarangaySummary(BaseModel):
    barangay_id: int
    barangay_summary: str