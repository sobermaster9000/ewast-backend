from pydantic import BaseModel, EmailStr
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
    user_id: int | None = Field(default=None, primary_key=None)
    firstname: str = Field(max_length=100)
    lastname: str = Field(max_length=100)
    email: str = Field(max_length=100, unique=True, index=True)
    role: Role

# standard user model to be stored in database
class User(UserBase, table=True):
    __tablename__: str = "users"

    password_hash: str
    date_created: datetime
    reject_tokens_before_timestamp: float # tokens created before this timestamp will be invalidated

# public user model to be returned in API calls
class UserPublic(UserBase):
    pass

# user model for instantiation from JSON input
class UserCreate(BaseModel):
    firstname: str
    lastname: str
    email: EmailStr
    password: str
    password_confirm: str
    role: Role
# class UserCreate(UserBase):
    # password: str = Field(max_length=100)
    # password_confirm: str = Field(max_length=100)

# user model for logins
class UserLogin(BaseModel):
    email: EmailStr
    password: str
# class UserLogin(SQLModel):
#     email: str = Field(max_length=100)
#     password: str = Field(max_length=100)