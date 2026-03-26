"""
TaxShield — Unit Tests for Agent 5 InEx Verifier (Citation Grounding)
Tests the deterministic (non-LLM) parts of Agent 5.
"""
import pytest
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from app.agents.agent5_verifier import Agent5Verifier


class TestCitationGrounding:
    """Tests for Stage 1: Citation Grounding (deterministic, no LLM)."""

    def setup_method(self):
        self.verifier = Agent5Verifier()

    def test_valid_sections_pass(self):
        """Draft citing known CGST sections should not flag issues."""
        draft = "Under Section 73 of the CGST Act, 2017, the limitation period is 3 years. Section 75 mandates a personal hearing."
        entities = {"SECTIONS": ["73", "75"]}

        result = self.verifier._check_citations(draft, [], entities)

        assert result["score"] >= 0.8
        # No critical issues for standard sections
        critical = [i for i in result["issues"] if i["severity"] == "critical"]
        assert len(critical) == 0

    def test_fabricated_section_flagged(self):
        """Draft citing a non-existent section should flag a warning."""
        draft = "As per Section 999 of the CGST Act, the taxpayer is entitled to relief."
        entities = {"SECTIONS": ["73"]}

        result = self.verifier._check_citations(draft, [], entities)

        warnings = [i for i in result["issues"] if i["severity"] == "warning"]
        assert len(warnings) >= 1
        assert any("999" in w["issue"] for w in warnings)

    def test_fabricated_circular_flagged(self):
        """Draft citing a circular not in KB should flag as critical."""
        draft = "As per Circular 999/99 dated 01.01.2025, this demand is invalid."
        entities = {"SECTIONS": []}

        result = self.verifier._check_citations(draft, [], entities)

        critical = [i for i in result["issues"] if i["severity"] == "critical"]
        assert len(critical) >= 1
        assert any("999/99" in c["issue"] for c in critical)

    def test_case_law_flagged(self):
        """Draft citing case law should flag as critical (unverifiable)."""
        draft = "As held in Kumar Industries v. Commissioner of CGST, this demand is barred."
        entities = {"SECTIONS": []}

        result = self.verifier._check_citations(draft, [], entities)

        critical = [i for i in result["issues"] if i["severity"] == "critical"]
        assert len(critical) >= 1
        assert any("case law" in c["issue"].lower() or "case" in c["issue"].lower() for c in critical)

    def test_no_citations_moderate_score(self):
        """Draft with no citations should get moderate score."""
        draft = "We respectfully submit that the demand is not sustainable."
        entities = {"SECTIONS": []}

        result = self.verifier._check_citations(draft, [], entities)

        assert result["score"] == 0.8
        assert result["total_cited"] == 0

    def test_sections_from_entities_accepted(self):
        """Sections present in entities should be accepted even if not standard."""
        draft = "Under Section 16 of the CGST Act, ITC can be claimed."
        entities = {"SECTIONS": ["16"]}

        result = self.verifier._check_citations(draft, [], entities)

        warnings = [i for i in result["issues"] if "16" in i.get("issue", "")]
        assert len(warnings) == 0  # Should not flag Section 16

    def test_circular_in_retrieved_docs_accepted(self):
        """Circular that exists in retrieved docs should not be flagged."""
        draft = "As per Circular 128/47 issued by CBIC, DIN is mandatory."
        circulars = [{"doc_id": "CBIC-CIR-128/47"}]
        entities = {"SECTIONS": []}

        result = self.verifier._check_citations(draft, circulars, entities)

        critical = [i for i in result["issues"] if "128/47" in i.get("issue", "")]
        assert len(critical) == 0  # Should be accepted

    def test_mixed_valid_and_invalid(self):
        """Draft with some valid and some invalid citations should have appropriate score."""
        draft = (
            "Under Section 73 of the CGST Act, the limitation is 3 years. "
            "However, as per Circular 999/88, this is extended."
        )
        entities = {"SECTIONS": ["73"]}

        result = self.verifier._check_citations(draft, [], entities)

        # Section 73 is valid, Circular 999/88 is not
        assert result["grounded_count"] < result["total_cited"]
        assert result["score"] < 1.0

    def test_llm_extracted_sections_accepted(self):
        """Sections from llm_extracted field in entities should be accepted."""
        draft = "Under Section 73 and Section 50, interest is applicable."
        entities = {
            "SECTIONS": [],
            "llm_extracted": {
                "sections_referenced": [73, 50]
            }
        }

        result = self.verifier._check_citations(draft, [], entities)

        warnings = [i for i in result["issues"] if i["severity"] == "warning"]
        assert len(warnings) == 0  # Both sections should be accepted


class TestCitationExtractionPatterns:
    """Tests for regex citation extraction accuracy."""

    def setup_method(self):
        self.verifier = Agent5Verifier()

    def test_extract_section_with_subsection(self):
        """Should extract 'Section 73(5)' correctly."""
        draft = "Under Section 73(5), the proper officer may issue an order."
        result = self.verifier._check_citations(draft, [], {"SECTIONS": ["73"]})
        assert "73(5)" in result["sections_cited"] or "73" in [s.split("(")[0] for s in result["sections_cited"]]

    def test_extract_multiple_sections(self):
        """Should extract all section references."""
        draft = "Section 73, Section 74, and Section 75 are all relevant here."
        result = self.verifier._check_citations(draft, [], {"SECTIONS": ["73", "74", "75"]})
        assert len(result["sections_cited"]) >= 3

    def test_extract_circular_reference(self):
        """Should extract circular number pattern."""
        draft = "Circular No. 128/47 mandates DIN for all communications."
        result = self.verifier._check_citations(draft, [], {"SECTIONS": []})
        assert "128/47" in result["circulars_cited"]
