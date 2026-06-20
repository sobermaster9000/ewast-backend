from pydantic import BaseModel
from typing import Any

from .report import ReportType

class ReportCount(BaseModel):
    barangay_name: str
    count: int

class ReportTypeFreq(BaseModel):
    report_type: ReportType | str
    count: int

class BarangayStatistics(BaseModel):
    barangay_name: str
    report_count: int
    report_density: float
    report_type_freq: list[ReportTypeFreq]
    report_themes: list[str]

class Statistics(BaseModel):
    report_count: int
    report_density: float
    barangays_with_most_reports: list[ReportCount]
    report_type_freq: list[ReportTypeFreq]
    report_themes: list[str]
    barangay_stats: list[BarangayStatistics]