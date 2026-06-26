from pydantic import BaseModel

from sqlmodel import SQLModel, Field
from sqlalchemy import Column, JSON
from .summary import Theme
from typing import Any

# base barangay class
class BarangayBase(SQLModel):
    name: str = Field(unique=True, index=True, max_length=100)
    bounds_coords: list[tuple[float, float]] = Field(sa_column=Column(JSON, nullable=False, default=[]))

# standard barangay class to be stored in database
class Barangay(BarangayBase, table=True):
    __tablename__: str = "barangays"

    barangay_id: int = Field(primary_key=True)
    report_summary: str | None = Field(default=None)
    report_themes: list[dict[str, Any]] = Field(sa_column=Column(JSON, default=[]))

# public barangay model to be returned in API calls
class BarangayPublic(BarangayBase):
    barangay_id: int

# barangay class for instantiation with JSON input
class BarangayCreate(BarangayBase):
    pass

class BarangayFloodRisk(BaseModel):
    barangay_id: int
    barangay_name: str
    flood_risk: float
    normalized_flood_risk: float

class _GeoJSON_Properties(BaseModel):
    type: str
    level: str | int
    label: str
    locale: str
    country_id: str | int
    country_reference: str | int
    country_name: str
    region_id: str | int
    region_reference: str | int
    region_name: str
    province_id: str | int
    province_reference: str | int
    province_name: str | int
    city_id: str | int
    city_reference: str | int
    city_name: str
    barangay_id: str | int
    barangay_reference: str | int
    barangay_name: str

class _GeoJSON_Geometry(BaseModel):
    type: str
    coordinates: list[list[list[list[float]]]]

class GeoJSON(BaseModel):
    type: str
    properties: _GeoJSON_Properties
    geometry: _GeoJSON_Geometry

class BarangayWithGeoJSON(BaseModel):
    barangay_id: int
    barangay_name: str
    geojson: GeoJSON