"""Tests for Hybrid Search"""
import os
import sys
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

_DATA_DIR = os.path.join(os.path.dirname(__file__), '..', 'data', 'circulars')
_HAS_DATA = os.path.isdir(_DATA_DIR) and len(os.listdir(_DATA_DIR)) > 0


@pytest.mark.skipif(not _HAS_DATA, reason="RAG knowledge base (data/circulars/) is empty")
def test_search_returns_results():
    """Search should return list of results"""
    from app.retrieval.hybrid import searcher
    searcher.build_index()
    results = searcher.search("limitation period")
    assert len(results) > 0


@pytest.mark.skipif(not _HAS_DATA, reason="RAG knowledge base (data/circulars/) is empty")
def test_search_has_score():
    """Each result should have a score"""
    from app.retrieval.hybrid import searcher
    results = searcher.search("Section 73")
    for r in results:
        assert "score" in r
        assert r["score"] > 0

