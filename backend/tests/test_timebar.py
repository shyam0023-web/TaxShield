"""Tests for Time-Bar calculation"""
from datetime import date
import sys
sys.path.insert(0, '..')

from app.watchdog.timebar import calculate_timebar, TimeBarRequest

def test_section_73_time_barred():
    """Section 73: FY 2018-19 should be time-barred by Jan 2024"""
    request = TimeBarRequest(fy="2018-19", section=73, notice_date=date(2024, 1, 15))
    result = calculate_timebar(request)
    assert result.is_time_barred == True
    assert result.delay_months > 0

def test_section_74_not_time_barred():
    """Section 74: FY 2020-21 should NOT be time-barred by Jan 2024"""
    request = TimeBarRequest(fy="2020-21", section=74, notice_date=date(2024, 1, 15))
    result = calculate_timebar(request)
    assert result.is_time_barred == False

def test_section_73_valid():
    """Section 73: Recent FY should be valid"""
    request = TimeBarRequest(fy="2022-23", section=73, notice_date=date(2024, 1, 15))
    result = calculate_timebar(request)
    assert result.is_time_barred == False
