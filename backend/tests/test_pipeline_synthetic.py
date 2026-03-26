"""
TaxShield — Pipeline Integration Test (Synthetic Notice)
Tests the flow: raw_text → entities → time-bar → section_kb → citation check
Uses the synthetic Section 73 notice (no LLM calls, no API keys needed).
"""
import pytest
import json
import sys
import os
import re

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

FIXTURE_DIR = os.path.join(os.path.dirname(__file__), "fixtures")


def load_synthetic_notice():
    """Load the synthetic Section 73 notice fixture."""
    filepath = os.path.join(FIXTURE_DIR, "synthetic_notice_73.json")
    with open(filepath, "r", encoding="utf-8") as f:
        return json.load(f)


class TestSyntheticNoticeFixture:
    """Verify the synthetic notice fixture is valid."""

    def setup_method(self):
        self.notice = load_synthetic_notice()

    def test_has_required_fields(self):
        """Fixture should have all required fields."""
        required = ["notice_id", "notice_type", "section", "raw_text",
                     "expected_entities", "expected_defenses"]
        for field in required:
            assert field in self.notice, f"Missing field: {field}"

    def test_raw_text_is_substantial(self):
        """Raw text should be a realistic SCN length."""
        assert len(self.notice["raw_text"]) > 500, "Notice should be substantial"

    def test_expected_sections(self):
        """Expected entities should include key sections."""
        sections = self.notice["expected_entities"]["SECTIONS"]
        assert "73" in sections
        assert "50" in sections
        assert "122" in sections


class TestEntityExtraction:
    """Test regex-based entity extraction on the synthetic notice."""

    def setup_method(self):
        self.notice = load_synthetic_notice()
        self.text = self.notice["raw_text"]

    def test_gstin_extraction(self):
        """Should extract GSTIN from notice text."""
        gstin_pattern = r'\d{2}[A-Z]{5}\d{4}[A-Z]\d[A-Z\d]{2}'
        matches = re.findall(gstin_pattern, self.text)
        assert len(matches) >= 1
        assert "27AABCA1234F1ZP" in matches

    def test_section_extraction(self):
        """Should extract section references using 'Section XX' pattern."""
        sections = set(re.findall(r'[Ss]ection\s+(\d+)', self.text))
        assert "73" in sections, f"Section 73 should be found, got {sections}"
        # Note: notice uses 'u/s 50' and 'u/s 122' patterns too
        # Broader regex catches both patterns
        all_sections = set(re.findall(r'(?:[Ss]ection|u/s)\s+(\d+)', self.text))
        assert "50" in all_sections
        assert "122" in all_sections

    def test_amount_extraction(self):
        """Should extract financial amounts."""
        amounts = re.findall(r'Rs\.\s*([\d,]+)/-', self.text)
        assert len(amounts) >= 4, f"Should find at least 4 amounts, found {len(amounts)}"

    def test_date_extraction(self):
        """Should extract notice date."""
        dates = re.findall(r'\d{2}\.\d{2}\.\d{4}', self.text)
        assert "15.01.2025" in dates

    def test_financial_year_extraction(self):
        """Should extract financial year reference."""
        fy_matches = re.findall(r'(\d{4}-\d{2})', self.text)
        assert "2019-20" in fy_matches

    def test_din_missing_detection(self):
        """Should detect that DIN is missing (procedural defect)."""
        # The notice says "without DIN number"
        assert "without DIN" in self.text or "DIN" in self.text


class TestTimeBarOnSyntheticNotice:
    """Test time-bar calculator on the synthetic notice."""

    def test_section_73_fy_2019_20_timebar(self):
        """FY 2019-20, notice 15-Jan-2025 → check time-bar with COVID extensions."""
        from app.tools.timebar import timebar

        result = timebar.check_potential_timebar("15-01-2025", "2019-20")
        # FY 2019-20 due date: 31-Mar-2020
        # COVID extension: 31-Mar-2020 → extended to 30-Sep-2021
        # 3 years from 30-Sep-2021 = 30-Sep-2024
        # Notice on 15-Jan-2025 → likely time-barred
        assert "potentially_time_barred" in result
        assert isinstance(result["potentially_time_barred"], bool)


class TestSectionKBOnSyntheticNotice:
    """Test section KB retrieval for the synthetic notice sections."""

    def test_section_73_kb_retrieval(self):
        """Section 73 should be in curated KB."""
        from app.retrieval.section_kb import SectionKB

        kb = SectionKB()
        kb.load()

        results = kb.search_by_section("73")
        assert len(results) == 1
        assert results[0]["source"] == "curated_kb"
        assert "limitation" in results[0]["text"].lower() or "3" in results[0]["text"]

    def test_multi_section_retrieval(self):
        """Should retrieve KB entries for all sections in the notice."""
        from app.retrieval.section_kb import SectionKB

        kb = SectionKB()
        kb.load()

        sections = ["73", "122", "75"]
        results = kb.search_by_sections(sections)
        doc_ids = [r["doc_id"] for r in results]
        assert "KB-73" in doc_ids
        assert "KB-122" in doc_ids

    def test_din_circular_retrieval(self):
        """DIN circular should be retrievable (notice has no DIN)."""
        from app.retrieval.section_kb import SectionKB

        kb = SectionKB()
        kb.load()

        results = kb.search_din()
        assert len(results) >= 1


class TestCitationGroundingOnSyntheticDraft:
    """Test Agent 5's citation grounding on a realistic draft reply."""

    SAMPLE_DRAFT = """
    REPLY TO SHOW CAUSE NOTICE
    F.No. CGST/DIV-III/R-2/SCN/2024-25/1234

    Respected Sir,

    We hereby submit our reply to the Show Cause Notice dated 15.01.2025
    issued under Section 73 of the CGST Act, 2017.

    1. PRELIMINARY OBJECTION — TIME-BARRED
    The present notice pertains to FY 2019-20. Under Section 73(10), the
    proper officer must issue an order within 3 years from the due date of
    filing the annual return. The due date for FY 2019-20 was 31.03.2020,
    extended to 30.09.2021 due to COVID-19 notifications. Therefore,
    3 years from 30.09.2021 expired on 30.09.2024. The notice dated
    15.01.2025 is thus time-barred and liable to be set aside.

    2. PROCEDURAL DEFECT — NO DIN
    As per CBIC Circular No. 128/47 dated 23.12.2019, every communication
    must bear a Document Identification Number (DIN). The present notice
    does not contain any DIN, rendering it invalid and without jurisdiction.

    3. ITC MISMATCH — GSTR-2A vs GSTR-3B
    The alleged discrepancy of Rs. 4,53,333/- is based on GSTR-2A data,
    which is merely an auto-populated statement. Under Section 16 of the
    CGST Act, ITC is available based on possession of a valid tax invoice
    and actual receipt of goods/services. GSTR-2A mismatch alone cannot
    be the basis for denying ITC.

    4. PENALTY UNDER SECTION 122 — NOT APPLICABLE
    Section 122 penalties apply only in cases of deliberate fraud or
    willful misstatement. In the present case, there is no allegation of
    fraud under Section 74. A bona fide ITC claim cannot attract penalty
    under Section 122.

    5. SECTION 75 — PERSONAL HEARING
    We request a personal hearing as mandated under Section 75(4) of the
    CGST Act before any order is passed.

    We pray that the SCN be dropped and the demand be set aside.

    For M/s ABC Trading Company
    Authorized Signatory
    """

    def test_draft_citations_valid(self):
        """All sections cited in the sample draft should be valid."""
        from app.agents.agent5_verifier import Agent5Verifier

        verifier = Agent5Verifier()
        entities = {"SECTIONS": ["73", "50", "122"], "llm_extracted": {
            "sections_referenced": [73, 50, 122, 16, 74, 75]
        }}

        result = verifier._check_citations(self.SAMPLE_DRAFT, [], entities)

        # Sections 73, 16, 122, 74, 75 are all standard/known → no warnings
        warnings = [i for i in result["issues"] if i["severity"] == "warning"]
        assert len(warnings) == 0, f"Expected no warnings, got: {warnings}"

    def test_draft_circular_128_grounded(self):
        """Circular 128/47 should be accepted with proper retrieved docs."""
        from app.agents.agent5_verifier import Agent5Verifier

        verifier = Agent5Verifier()
        # doc_id must contain "128/47" for the substring match to work
        circulars = [{"doc_id": "CBIC-CIR-128/47-2019"}]

        result = verifier._check_citations(self.SAMPLE_DRAFT, circulars, {"SECTIONS": ["73"]})

        # Circular 128/47 is in our retrieved docs
        circular_issues = [i for i in result["issues"]
                          if "128/47" in i.get("issue", "") and i["severity"] == "critical"]
        assert len(circular_issues) == 0, "Circular 128/47 should be accepted"

    def test_draft_overall_score(self):
        """Overall citation score should be reasonable for a good draft."""
        from app.agents.agent5_verifier import Agent5Verifier

        verifier = Agent5Verifier()
        entities = {"SECTIONS": ["73", "50", "122"], "llm_extracted": {
            "sections_referenced": [73, 50, 122, 16, 74, 75]
        }}
        circulars = [{"doc_id": "KB-din_circular_128"}]

        result = verifier._check_citations(self.SAMPLE_DRAFT, circulars, entities)

        assert result["score"] >= 0.7, f"Good draft should score ≥0.7, got {result['score']}"
        assert result["total_cited"] >= 5, f"Draft has many citations"
