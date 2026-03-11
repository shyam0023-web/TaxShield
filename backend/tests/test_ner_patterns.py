"""
Tests for NER Regex Patterns and GSTIN Validation (app.tools.notice_ner)
Pure-logic tests — only tests regex extraction and checksum, not LLM calls.
"""
import re
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from app.tools.patterns import (
    GSTIN_PATTERN, DIN_PATTERN, SECTION_PATTERN,
    AMOUNT_PATTERN, PAN_PATTERN, DATE_PATTERNS,
)
from app.tools.notice_ner import notice_ner


class TestGSTINValidation:
    """Tests for GSTIN regex + checksum validation"""

    def test_valid_gstin_matches(self):
        """Valid GSTIN format should match regex"""
        valid_gstins = [
            "27AAPFU0939F1ZV",
            "07AAACP1234Q1ZS",
            "29AABCT1332L1ZH",
        ]
        for gstin in valid_gstins:
            assert re.match(GSTIN_PATTERN, gstin), f"Should match: {gstin}"

    def test_invalid_gstin_no_match(self):
        """Invalid GSTIN format should NOT match"""
        invalid = [
            "12345",
            "ABCDEFGHIJKLMNO",
            "99AAAAA9999A9A9",  # state code 99 (invalid, but regex won't catch this)
        ]
        # Note: regex only checks format, checksum validation catches state codes
        for val in invalid[:2]:
            assert not re.match(GSTIN_PATTERN, val), f"Should NOT match: {val}"

    def test_gstin_checksum_valid(self):
        """Valid GSTIN should pass checksum (state code + PAN check)"""
        assert notice_ner.validate_gstin_checksum("27AAPFU0939F1ZV") is True
        assert notice_ner.validate_gstin_checksum("07AAACP1234Q1ZS") is True

    def test_gstin_checksum_invalid_state(self):
        """State code > 37 should fail"""
        assert notice_ner.validate_gstin_checksum("99AAPFU0939F1ZV") is False

    def test_gstin_checksum_wrong_length(self):
        """Non-15 char string should fail"""
        assert notice_ner.validate_gstin_checksum("27AAPFU") is False
        assert notice_ner.validate_gstin_checksum("") is False

    def test_gstin_extracted_from_text(self):
        """Should extract GSTINs from notice text"""
        text = "The GSTIN 27AAPFU0939F1ZV of the taxpayer as per records."
        matches = re.findall(GSTIN_PATTERN, text)
        assert len(matches) == 1
        assert matches[0] == "27AAPFU0939F1ZV"


class TestDINPattern:
    """Tests for DIN (Document Identification Number) regex"""

    def test_din_matches_valid(self):
        text = "DIN: ITBA012345678901234A"
        matches = re.findall(DIN_PATTERN, text)
        assert len(matches) == 1

    def test_din_no_false_positives_short(self):
        text = "Short text ABC123"
        matches = re.findall(DIN_PATTERN, text)
        assert len(matches) == 0


class TestSectionPattern:
    """Tests for Section number extraction"""

    def test_extracts_section_73(self):
        text = "Under Section 73 of the CGST Act"
        matches = re.findall(SECTION_PATTERN, text)
        assert "73" in matches

    def test_extracts_section_74(self):
        text = "proceedings under section 74"
        matches = re.findall(SECTION_PATTERN, text)
        assert "74" in matches

    def test_extracts_section_with_subsection(self):
        text = "As per Section 73(1) read with Section 75(4)"
        matches = re.findall(SECTION_PATTERN, text)
        assert "73(1)" in matches
        assert "75(4)" in matches

    def test_multiple_sections(self):
        text = "Section 73, Section 74, and Section 132 of the Act"
        matches = re.findall(SECTION_PATTERN, text)
        assert len(matches) == 3


class TestAmountPattern:
    """Tests for monetary amount extraction"""

    def test_extracts_inr_amount(self):
        text = "Demand of ₹5,00,000"
        matches = re.findall(AMOUNT_PATTERN, text)
        assert len(matches) > 0

    def test_extracts_plain_number(self):
        text = "Amount: 1234567"
        matches = re.findall(AMOUNT_PATTERN, text)
        assert len(matches) > 0

    def test_extracts_decimal_amount(self):
        text = "Interest: ₹ 12,345.67"
        matches = re.findall(AMOUNT_PATTERN, text)
        assert len(matches) > 0


class TestDatePatterns:
    """Tests for date extraction patterns"""

    def test_dd_mm_yyyy_dash(self):
        text = "Notice dated 15-01-2024"
        matches = re.findall(DATE_PATTERNS[0], text)
        assert "15-01-2024" in matches

    def test_dd_mm_yyyy_slash(self):
        text = "Notice dated 15/01/2024"
        matches = re.findall(DATE_PATTERNS[1], text)
        assert "15/01/2024" in matches

    def test_dd_month_yyyy(self):
        text = "Notice dated 15 January 2024"
        matches = re.findall(DATE_PATTERNS[2], text, re.IGNORECASE)
        assert len(matches) == 1


class TestPANPattern:
    """Tests for PAN pattern"""

    def test_pan_matches(self):
        matches = re.findall(PAN_PATTERN, "PAN: ABCDE1234F")
        assert "ABCDE1234F" in matches

    def test_pan_no_match_lowercase(self):
        matches = re.findall(PAN_PATTERN, "PAN: abcde1234f")
        assert len(matches) == 0
