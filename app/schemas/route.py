# from pydantic import BaseModel
from datetime import datetime

from sqlmodel import SQLModel, Field
from sqlalchemy import Column, JSON, CheckConstraint

# reusable geo point payload
class Location(SQLModel):
    latitude: float = Field(sa_column_args=[CheckConstraint("-90 <= latitude AND latitude <= 90")])
    longitude: float = Field(sa_column_args=[CheckConstraint("-180 <= longitude AND longitude <= 180")])

# route request payload for OSRM trip generation
class RouteTripRequest(SQLModel):
    start: Location
    end: Location
    report_locations: list[Location] = Field(default_factory=list)

# route request paylod for OSRM trip generation for a reports under a specified barangay
class RouteTripRequestBarangay(SQLModel):
    start: Location
    end: Location
    barangay_id: int

# base route model
class RouteBase(SQLModel):
    route_id: int | None = Field(default=None, primary_key=True)
    waypoints: list[tuple[float, float]] = Field(sa_column=Column(JSON, nullable=False, default=[]))
    is_approved: bool = Field(default=False)
    date_approved: datetime | None = None
    collection_rate: float | None = Field(default=None)
    est_fuel_cost: float | None = Field(default=None)

# standard route model to be stored in database
class Route(RouteBase, table=True):
    __tablename__: str = "routes"

# public route model to be returned in API calls
class RoutePublic(RouteBase):
    pass

# route model for instantiation from JSON input
class RouteCreate(RouteBase):
    pass