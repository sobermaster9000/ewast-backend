from pydantic import BaseModel
from typing import Any

from .report import ReportType
from .summary import Theme

class ReportCount(BaseModel):
    barangay_name: str
    count: int

class ReportTypeFreq(BaseModel):
    report_type: ReportType | str
    count: int

class BarangayStatistics(BaseModel):
    barangay_name: str
    report_count: int
    report_density_sq_m: float
    report_type_freq: list[ReportTypeFreq]
    report_themes: list[Theme]

class Statistics(BaseModel):
    report_count: int
    report_density_sq_m: float
    barangays_with_most_reports: list[ReportCount]
    report_type_freq: list[ReportTypeFreq]
    report_themes: list[Theme]
    barangay_stats: list[BarangayStatistics]

class ReportDensity(BaseModel):
    barangay_id: int
    barangay_name: str
    report_density_sq_m: float