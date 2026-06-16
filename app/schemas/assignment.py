# from pydantic import BaseModel
from datetime import datetime
# from typing import Optional

from sqlmodel import SQLModel, Field

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

# public assignment model to be returned in API calls
class AssignmentPublic(AssignmentBase):
    assignment_id: int
    is_started: bool = Field(default=False)
    is_completed: bool = Field(default=False)
    date_assigned: datetime
    date_completed: datetime | None = Field(default=None)

# assignment model for instantiation with JSON input
class AssignmentCreate(AssignmentBase):
    pass