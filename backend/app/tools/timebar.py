"""
TaxShield — Time-Bar Calculator
Dynamic deadline calculation with section awareness.
Agent 1 ONLY flags potential time-bar. Agent 2 makes final decision.
"""
from datetime import datetime
import logging

logger = logging.getLogger(__name__)


class TimeBarCalculator:
    """
    Preliminary time-bar check.
    
    Key rules:
    - Section 73: Normal cases → 3 year limit from due date of annual return
    - Section 74: Fraud/willful misstatement → 5 year limit
    - Section 132: Prosecution → no time limit
    
    Agent 1 only FLAGS. Agent 2 applies section-aware logic.
    """
    
    # Section → time limit (years)
    SECTION_LIMITS = {
        "73": 3,
        "74": 5,
        "129": 0,    # Detention — immediate
        "130": 0,    # Confiscation — immediate  
        "132": 999,  # Prosecution — no limit
    }
    
    # CBIC extension dates (COVID + other extensions)
    EXTENDED_DUE_DATES = {
        "2017-18": "2021-12-31",  # Extended due to COVID
        "2018-19": "2022-03-31",
        "2019-20": "2022-03-31",
        "2020-21": "2022-03-31",  # COVID extension
    }
    
    def check_potential_timebar(self, notice_date_str: str, 
                                 financial_year: str) -> dict:
        """
        Preliminary time-bar check. Returns flag only.
        Agent 2 makes final decision with section awareness.
        """
        try:
            # Parse notice date
            notice_date = None
            for fmt in ["%d-%m-%Y", "%d/%m/%Y", "%Y-%m-%d"]:
                try:
                    notice_date = datetime.strptime(notice_date_str, fmt)
                    break
                except ValueError:
                    continue
            
            if not notice_date:
                return {
                    "potentially_time_barred": False,
                    "error": f"Could not parse date: {notice_date_str}",
                    "requires_section_analysis": True
                }
            
            # Parse FY end date
            fy_end = self._get_fy_end_date(financial_year)
            if not fy_end:
                return {
                    "potentially_time_barred": False,
                    "error": f"Could not parse FY: {financial_year}",
                    "requires_section_analysis": True
                }
            
            # Check for CBIC extended due dates
            due_date_str = self.EXTENDED_DUE_DATES.get(financial_year)
            if due_date_str:
                due_date = datetime.strptime(due_date_str, "%Y-%m-%d")
            else:
                # Default: Annual return due date = 31 Dec of next FY
                due_date = datetime(fy_end.year, 12, 31)
            
            # Calculate years elapsed
            years_elapsed = (notice_date - due_date).days / 365.25
            
            return {
                "potentially_time_barred": years_elapsed > 3,  # Flag if exceeds shortest limit
                "years_elapsed": round(years_elapsed, 2),
                "financial_year": financial_year,
                "notice_date": notice_date_str,
                "due_date_used": due_date.strftime("%d-%m-%Y"),
                "cbic_extension_applied": financial_year in self.EXTENDED_DUE_DATES,
                "requires_section_analysis": True,
                "confidence": "LOW"  # Preliminary — Agent 2 decides
            }
            
        except Exception as e:
            logger.error(f"Time-bar check failed: {e}")
            return {
                "potentially_time_barred": False,
                "error": str(e),
                "requires_section_analysis": True
            }
    
    def _get_fy_end_date(self, financial_year: str) -> datetime:
        """Parse financial year string to end date (31-Mar)."""
        try:
            parts = financial_year.replace(" ", "").split("-")
            if len(parts) == 2:
                end_year = int(parts[1])
                if end_year < 100:
                    end_year += 2000
                return datetime(end_year, 3, 31)
        except (ValueError, IndexError):
            pass
        return None


# Singleton
timebar = TimeBarCalculator()
