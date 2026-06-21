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

# base route model
class RouteBase(SQLModel):
    waypoints: list[tuple[float, float]] = Field(sa_column=Column(JSON, nullable=False, default=[]))

# standard route model to be stored in database
class Route(RouteBase, table=True):
    __tablename__: str = "routes"

    route_id: int | None = Field(default=None, primary_key=True)
    is_approved: bool = Field(default=False)
    date_approved: datetime | None = None

# public route model to be returned in API calls
class RoutePublic(RouteBase):
    pass

# route model for instantiation from JSON input
class RouteCreate(RouteBase):
    pass