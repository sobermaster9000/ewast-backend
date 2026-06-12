from pydantic import BaseModel
from datetime import datetime
from typing import Optional

class Assignment(BaseModel):
    assignment_id: int
    assigned_to_user_id: int
    route_id: int
    is_started: bool = False
    is_completed: bool = False
    date_assigned: datetime
    date_completed: Optional[datetime]