"""
Tests for Time-Bar Calculator (app.tools.timebar)
Tests the PRODUCTION code used by Agent 1, not the legacy watchdog module.
"""
import pytest
import sys
import os

# Ensure backend is on the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from app.tools.timebar import TimeBarCalculator, timebar


class TestTimeBarCalculator:
    """Tests for TimeBarCalculator.check_potential_timebar()"""

    # ═══ Section 73 (3-year limit) ═══

    def test_section_73_time_barred_old_fy(self):
        """FY 2017-18, notice in June 2025 → time-barred (COVID ext to 2021-12-31 + 3y = 2024-12-31)"""
        result = timebar.check_potential_timebar("15-06-2025", "2017-18")
        assert result["potentially_time_barred"] is True
        assert result["years_elapsed"] > 3

    def test_section_73_not_time_barred_recent_fy(self):
        """FY 2022-23, notice in 2024 → NOT time-barred"""
        result = timebar.check_potential_timebar("15-01-2024", "2022-23")
        assert result["potentially_time_barred"] is False

    def test_section_73_boundary_case(self):
        """FY 2020-21, notice on exactly 31-Dec-2024 → borderline"""
        result = timebar.check_potential_timebar("31-12-2024", "2020-21")
        # Due date for 2020-21 is extended to 2022-03-31 (COVID)
        # 3 years from 2022-03-31 = 2025-03-31
        # Notice on 2024-12-31 → NOT time-barred
        assert result["potentially_time_barred"] is False

    # ═══ COVID Extensions ═══

    def test_covid_extension_applied_2017_18(self):
        """FY 2017-18 should use extended due date 2021-12-31"""
        result = timebar.check_potential_timebar("15-01-2024", "2017-18")
        assert result["cbic_extension_applied"] is True
        assert "31-12-2021" in result["due_date_used"]

    def test_covid_extension_applied_2019_20(self):
        """FY 2019-20 should use extended due date 2022-03-31"""
        result = timebar.check_potential_timebar("15-06-2025", "2019-20")
        assert result["cbic_extension_applied"] is True

    def test_no_covid_extension_recent_fy(self):
        """FY 2022-23 should NOT have COVID extension"""
        result = timebar.check_potential_timebar("15-01-2024", "2022-23")
        assert result["cbic_extension_applied"] is False

    # ═══ Date Parsing ═══

    def test_date_format_dd_mm_yyyy(self):
        """Should parse DD-MM-YYYY"""
        result = timebar.check_potential_timebar("15-01-2024", "2022-23")
        assert "error" not in result

    def test_date_format_slash(self):
        """Should parse DD/MM/YYYY"""
        result = timebar.check_potential_timebar("15/01/2024", "2022-23")
        assert "error" not in result

    def test_date_format_iso(self):
        """Should parse YYYY-MM-DD"""
        result = timebar.check_potential_timebar("2024-01-15", "2022-23")
        assert "error" not in result

    def test_invalid_date_returns_error(self):
        """Invalid date should return error, not crash"""
        result = timebar.check_potential_timebar("not-a-date", "2022-23")
        assert result["potentially_time_barred"] is False
        assert "error" in result

    def test_invalid_fy_returns_error(self):
        """Invalid FY format should return error, not crash"""
        result = timebar.check_potential_timebar("15-01-2024", "invalid")
        assert result["potentially_time_barred"] is False
        assert "error" in result

    # ═══ FY Parsing ═══

    def test_fy_short_format(self):
        """Should handle FY like '2022-23' (2-digit end year)"""
        result = timebar.check_potential_timebar("15-01-2024", "2022-23")
        assert "error" not in result

    def test_fy_with_spaces(self):
        """Should handle FY with spaces like '2022 - 23'"""
        result = timebar.check_potential_timebar("15-01-2024", "2022 - 23")
        assert "error" not in result

    # ═══ Output Structure ═══

    def test_output_has_required_fields(self):
        """Output should always have these fields"""
        result = timebar.check_potential_timebar("15-01-2024", "2022-23")
        assert "potentially_time_barred" in result
        assert "requires_section_analysis" in result
        assert "years_elapsed" in result
        assert "financial_year" in result

    def test_output_requires_section_analysis(self):
        """Output should always flag that Agent 2 needs to verify"""
        result = timebar.check_potential_timebar("15-01-2024", "2022-23")
        assert result["requires_section_analysis"] is True

    def test_confidence_is_low(self):
        """Agent 1 time-bar is preliminary — confidence should be LOW"""
        result = timebar.check_potential_timebar("15-01-2024", "2022-23")
        assert result.get("confidence") == "LOW"

    # ═══ Section Limits (class constant) ═══

    def test_section_limits_exist(self):
        """SECTION_LIMITS should have at least 73, 74, 132"""
        limits = TimeBarCalculator.SECTION_LIMITS
        assert "73" in limits
        assert "74" in limits
        assert "132" in limits

    def test_section_73_limit_is_3(self):
        assert TimeBarCalculator.SECTION_LIMITS["73"] == 3

    def test_section_74_limit_is_5(self):
        assert TimeBarCalculator.SECTION_LIMITS["74"] == 5

    def test_section_132_no_limit(self):
        assert TimeBarCalculator.SECTION_LIMITS["132"] == 999
