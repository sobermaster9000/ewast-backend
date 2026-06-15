# from pydantic import BaseModel
from datetime import datetime

from sqlmodel import SQLModel, Field
from sqlalchemy import Column, JSON

# base route model
class RouteBase(SQLModel):
    waypoints: list[tuple[float, float]] = Field(sa_column=Column(JSON, nullable=False, default=[]))

# standard route model to be stored in database
class Route(RouteBase, table=True):
    __tablename__: str = "routes"

    route_id: int = Field(primary_key=True)
    is_approved: bool = Field(default=False)
    date_approved: datetime

# public route model to be returned in API calls
class RoutePublic(RouteBase):
    pass

# route model for instantiation from JSON input
class RouteCreate(RouteBase):
    pass