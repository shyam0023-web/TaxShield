"""
TaxShield — Unit Tests for Section KB (Primary RAG Path)
Tests the curated markdown knowledge base search module.
"""
import pytest
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from app.retrieval.section_kb import SectionKB


class TestSectionKBLoad:
    """Tests for loading curated KB from disk."""

    def test_load_curated_kb(self):
        """KB should load all markdown files from data/curated_kb/."""
        kb = SectionKB()
        kb.load()
        assert kb._loaded is True
        assert len(kb._all_entries) > 0, "Should have loaded at least 1 KB entry"

    def test_load_creates_section_index(self):
        """After loading, section index should contain key sections."""
        kb = SectionKB()
        kb.load()
        sections = kb.get_all_sections()
        # Core sections from our curated KB
        for sec in ["73", "74", "75"]:
            assert sec in sections, f"Section {sec} should be indexed"


class TestSectionKBSearch:
    """Tests for search methods."""

    @pytest.fixture(autouse=True)
    def setup_kb(self):
        self.kb = SectionKB()
        self.kb.load()

    def test_search_by_section_73(self):
        """Section 73 should return curated KB entry."""
        results = self.kb.search_by_section("73")
        assert len(results) == 1
        assert results[0]["doc_id"] == "KB-73"
        assert results[0]["source"] == "curated_kb"
        assert results[0]["score"] == 1.0
        assert "limitation" in results[0]["text"].lower() or "time" in results[0]["text"].lower()

    def test_search_by_section_normalize(self):
        """Should normalize 'Section 73' → '73'."""
        results = self.kb.search_by_section("Section 73")
        assert len(results) == 1
        assert results[0]["doc_id"] == "KB-73"

    def test_search_by_section_with_subsection(self):
        """Should normalize '73(5)' → '73'."""
        results = self.kb.search_by_section("73(5)")
        assert len(results) == 1
        assert results[0]["doc_id"] == "KB-73"

    def test_search_by_section_nonexistent(self):
        """Nonexistent section should return empty list."""
        results = self.kb.search_by_section("999")
        assert len(results) == 0

    def test_search_by_sections_multiple(self):
        """Multi-section search should return deduplicated results."""
        results = self.kb.search_by_sections(["73", "74", "75"])
        doc_ids = [r["doc_id"] for r in results]
        assert "KB-73" in doc_ids
        assert "KB-74" in doc_ids
        assert "KB-75" in doc_ids
        # No duplicates
        assert len(doc_ids) == len(set(doc_ids))

    def test_search_din(self):
        """DIN circular should be retrievable."""
        results = self.kb.search_din()
        assert len(results) >= 1
        assert any("din" in r["doc_id"].lower() or "128" in r["doc_id"] for r in results)

    def test_search_by_query_fuzzy(self):
        """Keyword search should return relevant entries."""
        results = self.kb.search_by_query("limitation period demand notice")
        assert len(results) > 0, "Should find entries matching limitation/demand keywords"

    def test_search_by_query_no_match(self):
        """Completely irrelevant query should return empty."""
        results = self.kb.search_by_query("xyzzy foobar nonsense")
        assert len(results) == 0


class TestSectionKBEntryStructure:
    """Tests for KB entry content structure."""

    @pytest.fixture(autouse=True)
    def setup_kb(self):
        self.kb = SectionKB()
        self.kb.load()

    def test_entry_has_required_fields(self):
        """Each search result should have all required fields."""
        results = self.kb.search_by_section("73")
        assert len(results) == 1
        entry = results[0]
        required = ["doc_id", "text", "full_text", "title", "defense_points", "score", "source"]
        for field in required:
            assert field in entry, f"Missing field: {field}"

    def test_entry_has_defense_points(self):
        """Section 73 entry should have defense points."""
        results = self.kb.search_by_section("73")
        assert len(results[0]["defense_points"]) > 0, "Should have at least 1 defense point"

    def test_entry_has_key_ruling(self):
        """Key ruling text should be non-empty."""
        results = self.kb.search_by_section("73")
        assert len(results[0]["text"]) > 50, "Key ruling should be substantive"


class TestSectionKBReload:
    """Tests for hot-reload functionality."""

    def test_reload_clears_and_reloads(self):
        """reload() should clear indexes and re-read from disk."""
        kb = SectionKB()
        kb.load()
        count_before = len(kb._all_entries)

        kb.reload()
        count_after = len(kb._all_entries)

        assert count_after == count_before, "Reload should produce same entries"
        assert kb._loaded is True

    def test_get_all_sections_returns_sorted(self):
        """get_all_sections() should return sorted list."""
        kb = SectionKB()
        kb.load()
        sections = kb.get_all_sections()
        # Numeric sections should come first (sorted)
        numeric = [s for s in sections if s.isdigit()]
        assert numeric == sorted(numeric), "Numeric sections should be sorted"
