# from pydantic import BaseModel
from datetime import datetime
# from typing import Optional

from sqlmodel import SQLModel, Field
from sqlalchemy import Column, JSON

# base assignment model
class AssignmentBase(SQLModel):
    assigned_to_user_id: int # manually verify that this exists in `users` table
    route_id: int # manually verify that this exists in `routes` table

# standard assignment model to be stored in database
class Assignment(AssignmentBase, table=True):
    __tablename__: str = "assignments"

    assignment_id: int | None = Field(default=None, primary_key=True)
    is_started: bool | None = Field(default=False)
    is_completed: bool | None = Field(default=False)
    date_assigned: datetime | None = Field(default=None)
    date_completed: datetime | None = Field(default=None)
    deadline: datetime | None = Field(default=None)
    is_tracked_by_admin: bool | None = Field(default=False)
    current_truck_latlong: list[float] = Field(sa_column=Column(JSON, nullable=False, default=[0, 0]))

# public assignment model to be returned in API calls
class AssignmentPublic(AssignmentBase):
    assignment_id: int
    is_started: bool = Field(default=False)
    is_completed: bool = Field(default=False)
    date_assigned: datetime | None
    deadline: datetime | None
    date_completed: datetime | None = Field(default=None)
    is_tracked_by_admin: bool = Field(default=False)
    current_truck_latlong: list[float] = Field(sa_column=Column(JSON, nullable=False, default=[0, 0]))

# assignment model for instantiation with JSON input
class AssignmentCreate(AssignmentBase):
    pass