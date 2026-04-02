"""
Tests for app.utils — parse_llm_extracted() and parse_demand_amount()
These two functions are used by 8+ files. If they break, every agent breaks.
"""
import sys
import os
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from app.utils import parse_llm_extracted, parse_demand_amount


# ═══════════════════════════════════════════
# parse_llm_extracted()
# ═══════════════════════════════════════════

class TestParseLlmExtracted:

    def test_already_dict(self):
        """If llm_extracted is already a dict, pass through."""
        entities = {"llm_extracted": {"notice_type": "SCN"}}
        result = parse_llm_extracted(entities)
        assert result == {"notice_type": "SCN"}

    def test_valid_json_string(self):
        """If llm_extracted is a valid JSON string, parse it."""
        entities = {"llm_extracted": '{"notice_type": "SCN", "fy": "2022-23"}'}
        result = parse_llm_extracted(entities)
        assert result["notice_type"] == "SCN"
        assert result["fy"] == "2022-23"

    def test_invalid_json_string(self):
        """If llm_extracted is garbage string, return empty dict."""
        entities = {"llm_extracted": "not valid json {{{"}
        result = parse_llm_extracted(entities)
        assert result == {}

    def test_missing_key(self):
        """If llm_extracted key doesn't exist, return empty dict."""
        entities = {"GSTIN": []}
        result = parse_llm_extracted(entities)
        assert result == {}

    def test_none_value(self):
        """If llm_extracted is None, return empty dict."""
        entities = {"llm_extracted": None}
        result = parse_llm_extracted(entities)
        assert result == {}

    def test_empty_entities(self):
        """Empty entities dict → empty result."""
        result = parse_llm_extracted({})
        assert result == {}

    def test_non_dict_entities(self):
        """If entities itself is not a dict (edge case), return empty."""
        result = parse_llm_extracted("not a dict")
        assert result == {}

    def test_list_value(self):
        """If llm_extracted is a list (unexpected), return empty dict."""
        entities = {"llm_extracted": [1, 2, 3]}
        result = parse_llm_extracted(entities)
        assert result == {}

    def test_nested_json_string(self):
        """Nested dict inside JSON string should parse correctly."""
        entities = {"llm_extracted": '{"demand_amount": {"igst": 0, "total": 50000}}'}
        result = parse_llm_extracted(entities)
        assert result["demand_amount"]["total"] == 50000


# ═══════════════════════════════════════════
# parse_demand_amount()
# ═══════════════════════════════════════════

class TestParseDemandAmount:

    def test_dict_with_total(self):
        """Standard format: {"total": 50000}."""
        llm_data = {"demand_amount": {"igst": 0, "cgst": 25000, "sgst": 25000, "total": 50000}}
        assert parse_demand_amount(llm_data) == 50000.0

    def test_plain_number(self):
        """Demand as plain integer."""
        llm_data = {"demand_amount": 12345}
        assert parse_demand_amount(llm_data) == 12345.0

    def test_plain_float(self):
        """Demand as float."""
        llm_data = {"demand_amount": 99999.50}
        assert parse_demand_amount(llm_data) == 99999.50

    def test_missing_key(self):
        """No demand_amount key → 0."""
        assert parse_demand_amount({}) == 0.0

    def test_none_value(self):
        """demand_amount is None → 0."""
        assert parse_demand_amount({"demand_amount": None}) == 0.0

    def test_dict_with_zero_total(self):
        """Total is 0 → 0."""
        llm_data = {"demand_amount": {"total": 0}}
        assert parse_demand_amount(llm_data) == 0.0

    def test_dict_with_none_total(self):
        """Total is None → 0 (the `or 0` fallback)."""
        llm_data = {"demand_amount": {"total": None}}
        assert parse_demand_amount(llm_data) == 0.0

    def test_string_value(self):
        """Demand as string (unexpected) → 0."""
        llm_data = {"demand_amount": "fifty thousand"}
        assert parse_demand_amount(llm_data) == 0.0
