from pydantic import BaseModel
from datetime import datetime
from typing import Optional
from enum import Enum

class ReportType(str, Enum):
    DUMMY = "dummy"

class Report(BaseModel):
    report_id: int
    image_url: str
    type: ReportType
    notes: Optional[str]
    latitude: float
    longitude: float
    barangay_id: int
    reported_by_user_id: int
    is_collected: bool = False
    date_reported: datetime