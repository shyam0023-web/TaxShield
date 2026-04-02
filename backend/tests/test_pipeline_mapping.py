"""
Unit tests for _map_pipeline_state_to_notice — the pure field-mapping function.
These were impossible to test before the refactor (required running the full pipeline).
"""
import sys
import os
import pytest
from datetime import datetime
from unittest.mock import MagicMock

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from app.routes.notices import _map_pipeline_state_to_notice
from app.models.notice import Notice


def make_notice() -> Notice:
    """Minimal Notice mock — no DB needed."""
    n = MagicMock(spec=Notice)
    return n


def make_state(**overrides) -> dict:
    """Base valid pipeline state for testing field mapping."""
    base = {
        "raw_text": "GST notice text here",
        "entities": {
            "GSTIN": [{"value": "27AABCA1234F1ZP", "valid": True}],
            "SECTIONS": ["73", "50"],
            "DIN": [],
            "llm_extracted": {
                "notice_type": "SCN",
                "financial_year": "2022-23",
                "notice_date": "01-01-2024",
                "demand_amount": {"total": 50000},
                "response_deadline": "01-02-2024",
            },
        },
        "notice_annotations": [{"role": "HEADER", "summary": "Notice ref"}],
        "processing_status": "complete",
        "risk_level": "HIGH",
        "risk_score": 0.85,
        "risk_reasoning": "High demand amount, time-barred risk",
        "is_time_barred": True,
        "time_bar_detail": {"potentially_time_barred": True},
        "draft_reply": "Dear Sir, We submit our reply...",
        "verification_status": "passed",
        "verification_score": 0.92,
        "verification_issues": [],
        "accuracy_report": {"score": 0.9},
    }
    base.update(overrides)
    return base


class TestMapPipelineStateToNotice:

    def test_maps_basic_text_fields(self):
        notice = make_notice()
        _map_pipeline_state_to_notice(notice, make_state())
        assert notice.notice_text == "GST notice text here"
        assert notice.processing_status == "complete"
        assert notice.risk_reasoning == "High demand amount, time-barred risk"

    def test_maps_risk_fields(self):
        notice = make_notice()
        _map_pipeline_state_to_notice(notice, make_state())
        assert notice.risk_level == "HIGH"
        assert notice.risk_score == 0.85
        assert notice.is_time_barred is True

    def test_maps_llm_extracted_fields(self):
        notice = make_notice()
        _map_pipeline_state_to_notice(notice, make_state())
        assert notice.fy == "2022-23"
        assert notice.notice_type == "SCN"
        assert notice.response_deadline == "01-02-2024"

    def test_picks_first_section_as_primary(self):
        notice = make_notice()
        _map_pipeline_state_to_notice(notice, make_state())
        assert notice.section == "73"  # First from ["73", "50"]

    def test_empty_sections_gives_empty_string(self):
        notice = make_notice()
        state = make_state()
        state["entities"]["SECTIONS"] = []
        _map_pipeline_state_to_notice(notice, state)
        assert notice.section == ""

    def test_demand_amount_parsed_from_dict(self):
        notice = make_notice()
        _map_pipeline_state_to_notice(notice, make_state())
        assert notice.demand_amount == 50000.0

    def test_demand_amount_plain_number(self):
        notice = make_notice()
        state = make_state()
        state["entities"]["llm_extracted"]["demand_amount"] = 12345
        _map_pipeline_state_to_notice(notice, state)
        assert notice.demand_amount == 12345.0

    def test_draft_reply_sets_draft_ready_status(self):
        notice = make_notice()
        _map_pipeline_state_to_notice(notice, make_state(draft_reply="Some reply"))
        assert notice.draft_status == "draft_ready"

    def test_empty_draft_reply_sets_pending(self):
        notice = make_notice()
        _map_pipeline_state_to_notice(notice, make_state(draft_reply=""))
        assert notice.draft_status == "pending"

    def test_missing_draft_reply_sets_pending(self):
        notice = make_notice()
        state = make_state()
        state.pop("draft_reply")
        _map_pipeline_state_to_notice(notice, state)
        assert notice.draft_status == "pending"

    def test_status_always_set_to_processed(self):
        notice = make_notice()
        _map_pipeline_state_to_notice(notice, make_state())
        assert notice.status == "processed"

    def test_verification_fields_mapped(self):
        notice = make_notice()
        _map_pipeline_state_to_notice(notice, make_state())
        assert notice.verification_status == "passed"
        assert notice.verification_score == 0.92
        assert notice.verification_issues == []

    def test_missing_llm_extracted_uses_defaults(self):
        """If entities has no llm_extracted key, all derived fields default gracefully."""
        notice = make_notice()
        state = make_state()
        state["entities"] = {"SECTIONS": ["73"], "GSTIN": []}
        _map_pipeline_state_to_notice(notice, state)
        assert notice.fy == ""
        assert notice.notice_type == ""
        assert notice.demand_amount == 0.0

    def test_risk_score_cast_to_float(self):
        """risk_score from pipeline may be int — should always become float."""
        notice = make_notice()
        _map_pipeline_state_to_notice(notice, make_state(risk_score=1))
        assert isinstance(notice.risk_score, float)

    def test_updated_at_is_set(self):
        notice = make_notice()
        _map_pipeline_state_to_notice(notice, make_state())
        assert notice.updated_at is not None
