from pydantic import BaseModel
from datetime import datetime

class Route(BaseModel):
    route_id: int
    waypoints: list[tuple[float, float]]
    is_approved: bool
    date_approved: datetime