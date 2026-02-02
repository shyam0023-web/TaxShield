"""Tests for Hybrid Search"""
def test_search_returns_results():
    """Search should return list of results"""
    from app.retrieval.hybrid import searcher
    searcher.build_index()
    results = searcher.search("limitation period")
    assert len(results) > 0

def test_search_has_score():
    """Each result should have a score"""
    from app.retrieval.hybrid import searcher
    results = searcher.search("Section 73")
    for r in results:
        assert "score" in r
        assert r["score"] > 0
