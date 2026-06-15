# from pydantic import BaseModel
from datetime import datetime
from enum import Enum

from sqlmodel import SQLModel, Field

# helper enum for user roles
class Role(str, Enum):
    CITIZEN = "citizen"
    ADMIN = "admin"
    COLLECTOR = "collector"

# base user model
class UserBase(SQLModel):
    firstname: str = Field(max_length=100)
    lastname: str = Field(max_length=100)
    email: str = Field(max_length=100, unique=True, index=True)
    role: Role

# standard user model to be stored in database
class User(UserBase, table=True):
    __tablename__: str = "users"

    user_id: int = Field(primary_key=True)
    password_hash: str
    date_created: datetime
    token: str | None = Field(default=None)
    token_expiry: datetime | None = Field(default=None)

# public user model to be returned in API calls
class UserPublic(UserBase):
    pass

# user model for instantiation from JSON input
class UserCreate(UserBase):
    pass

# user model for logins
class UserLogin(SQLModel):
    email: str = Field(max_length=100)
    password: str = Field(max_length=100)