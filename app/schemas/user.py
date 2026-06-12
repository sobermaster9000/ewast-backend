from pydantic import BaseModel
from datetime import datetime
from enum import Enum

class Role(str, Enum):
    CITIZEN = "citizen"
    ADMIN = "admin"
    COLLECTOR = "collector"

class User(BaseModel):
    user_id: int
    firstname: str
    lastname: str
    password_hash: str
    role: Role
    date_created: datetime