from datetime import date
import re
from pydantic import BaseModel, field_validator

class TimeBarResult(BaseModel):
    is_time_barred: bool
    fy: str
    section: int
    fy_end: date
    limitation_date: date
    notice_date: date
    delay_months: int

class TimeBarRequest(BaseModel):
    fy: str
    section: int
    notice_date: date

    @field_validator("fy")
    @classmethod
    def validate_fy(cls, v: str) -> str:
        pattern = r"^\d{4}-\d{2}$"
        if not re.match(pattern, v):
            raise ValueError("FY must be in format YYYY-YY (e.g., 2018-19)")
        return v

    @field_validator("section")
    @classmethod
    def validate_section(cls, v: int) -> int:
        if v not in (73, 74):
            raise ValueError("Section must be 73 or 74")
        return v

def calculate_timebar(request: TimeBarRequest) -> TimeBarResult:
    fy_end_year = int("20" + request.fy.split("-")[1])
    fy_end = date(fy_end_year, 3, 31)

    years = 3 if request.section == 73 else 5
    limitation_date = date(fy_end.year + years, fy_end.month, fy_end.day)

    is_time_barred = request.notice_date > limitation_date

    if is_time_barred:
        delay_months = (request.notice_date.year - limitation_date.year) * 12 + (
            request.notice_date.month - limitation_date.month
        )
    else:
        delay_months = 0

    return TimeBarResult(
        is_time_barred=is_time_barred,
        fy=request.fy,
        section=request.section,
        fy_end=fy_end,
        limitation_date=limitation_date,
        notice_date=request.notice_date,
        delay_months=delay_months,
    )
