"""
Tests for API Routes using FastAPI TestClient.
Mocks the LangGraph pipeline to test route logic independently.
"""
import sys
import os
import pytest
from unittest.mock import patch, AsyncMock, MagicMock
from datetime import datetime

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from httpx import AsyncClient, ASGITransport
from app.main import app
from app.database import get_db, AsyncSessionLocal, init_db, engine, Base


# ═══════════════════════════════════════════
# Fixtures
# ═══════════════════════════════════════════

@pytest.fixture(scope="module")
def anyio_backend():
    return "asyncio"


@pytest.fixture(autouse=True, scope="module")
async def setup_db():
    """Create tables before tests, drop after."""
    # Import models so Base knows about them
    import app.models.notice
    import app.models.draft
    import app.models.case

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


@pytest.fixture
async def client():
    """Async test client for the FastAPI app."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


# ═══════════════════════════════════════════
# Saved LLM Responses (Issue 12A)
# ═══════════════════════════════════════════

MOCK_PIPELINE_RESULT = {
    "case_id": "test_notice.pdf",
    "processing_status": "complete",
    "raw_text": "This is a test GST notice under Section 73 for FY 2022-23.",
    "entities": {
        "GSTIN": [{"value": "27AAPFU0939F1ZV", "valid": True}],
        "DIN": [],
        "SECTIONS": ["73"],
        "llm_extracted": {
            "notice_type": "SCN",
            "financial_year": "2022-23",
            "notice_date": "15-01-2024",
            "demand_amount": {"total": 50000},
            "response_deadline": "15-02-2024",
        },
    },
    "notice_annotations": [
        {"paragraph": 1, "role": "HEADER", "summary": "Notice reference"},
        {"paragraph": 2, "role": "FACTS", "summary": "ITC mismatch claim"},
    ],
    "risk_level": "LOW",
    "risk_score": 0.3,
    "risk_reasoning": "Scrutiny notice, low demand amount",
    "is_time_barred": False,
    "time_bar_detail": {"potentially_time_barred": False},
    "draft_reply": "Dear Sir/Madam, We are in receipt of the notice...",
    "current_agent": "agent4",
}


# ═══════════════════════════════════════════
# Health Route Tests
# ═══════════════════════════════════════════

@pytest.mark.anyio
async def test_health_endpoint(client):
    """GET /health should return status ok"""
    response = await client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"


# ═══════════════════════════════════════════
# Notice Upload Tests
# ═══════════════════════════════════════════

@pytest.mark.anyio
async def test_upload_rejects_non_pdf(client):
    """Should reject non-PDF files with 400"""
    response = await client.post(
        "/api/notices/upload",
        files={"file": ("test.txt", b"not a pdf", "text/plain")},
    )
    assert response.status_code == 400
    assert "PDF" in response.json()["detail"]


@pytest.mark.anyio
async def test_upload_rejects_empty_file(client):
    """Should reject empty PDF with 400"""
    response = await client.post(
        "/api/notices/upload",
        files={"file": ("empty.pdf", b"", "application/pdf")},
    )
    assert response.status_code == 400
    assert "Empty" in response.json()["detail"]


@pytest.mark.anyio
@patch("app.routes.notices.graph")
async def test_upload_success(mock_graph, client):
    """Successful upload should return notice ID and risk level"""
    mock_graph.ainvoke = AsyncMock(return_value=MOCK_PIPELINE_RESULT)
    
    response = await client.post(
        "/api/notices/upload",
        files={"file": ("test_notice.pdf", b"%PDF-1.4 test content", "application/pdf")},
    )
    assert response.status_code == 200
    data = response.json()
    assert "id" in data
    assert data["risk_level"] == "LOW"
    assert data["status"] == "processed"


@pytest.mark.anyio
@patch("app.routes.notices.graph")
async def test_upload_saves_to_db(mock_graph, client):
    """Upload should persist notice to database"""
    mock_graph.ainvoke = AsyncMock(return_value=MOCK_PIPELINE_RESULT)
    
    # Upload
    response = await client.post(
        "/api/notices/upload",
        files={"file": ("persist_test.pdf", b"%PDF-1.4 test", "application/pdf")},
    )
    notice_id = response.json()["id"]
    
    # Verify it's in the DB via GET
    get_response = await client.get(f"/api/notices/{notice_id}")
    assert get_response.status_code == 200
    data = get_response.json()
    assert data["id"] == notice_id
    assert data["risk_level"] == "LOW"
    assert data["notice_type"] == "SCN"


@pytest.mark.anyio
@patch("app.routes.notices.graph")
async def test_upload_pipeline_failure(mock_graph, client):
    """Pipeline failure should return 500 and save error to DB"""
    mock_graph.ainvoke = AsyncMock(side_effect=Exception("LLM timeout"))
    
    response = await client.post(
        "/api/notices/upload",
        files={"file": ("fail_test.pdf", b"%PDF-1.4 test", "application/pdf")},
    )
    assert response.status_code == 500
    assert "Processing failed" in response.json()["detail"]


# ═══════════════════════════════════════════
# Notice List/Detail Tests
# ═══════════════════════════════════════════

@pytest.mark.anyio
async def test_list_notices(client):
    """GET /api/notices should return a list"""
    response = await client.get("/api/notices")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)


@pytest.mark.anyio
async def test_get_notice_not_found(client):
    """GET /api/notices/{id} for nonexistent ID should return 404"""
    response = await client.get("/api/notices/nonexistent-id-12345")
    assert response.status_code == 404


# ═══════════════════════════════════════════
# Notifications Tests
# ═══════════════════════════════════════════

@pytest.mark.anyio
async def test_notifications_endpoint(client):
    """GET /api/notifications should return a list"""
    response = await client.get("/api/notifications")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)


# ═══════════════════════════════════════════
# Response Shape Tests (API Contract)
# ═══════════════════════════════════════════

@pytest.mark.anyio
@patch("app.routes.notices.graph")
async def test_upload_response_shape(mock_graph, client):
    """Upload response must have exactly these fields"""
    mock_graph.ainvoke = AsyncMock(return_value=MOCK_PIPELINE_RESULT)
    
    response = await client.post(
        "/api/notices/upload",
        files={"file": ("shape_test.pdf", b"%PDF-1.4 test", "application/pdf")},
    )
    data = response.json()
    required_fields = {"id", "case_id", "risk_level", "status", "draft_status"}
    assert required_fields.issubset(set(data.keys())), f"Missing fields: {required_fields - set(data.keys())}"


@pytest.mark.anyio
@patch("app.routes.notices.graph")
async def test_notice_detail_response_shape(mock_graph, client):
    """Notice detail must include all expected fields"""
    mock_graph.ainvoke = AsyncMock(return_value=MOCK_PIPELINE_RESULT)
    
    # Create a notice first
    upload_resp = await client.post(
        "/api/notices/upload",
        files={"file": ("detail_shape.pdf", b"%PDF-1.4 test", "application/pdf")},
    )
    notice_id = upload_resp.json()["id"]
    
    # Get detail
    response = await client.get(f"/api/notices/{notice_id}")
    data = response.json()
    
    required_fields = {
        "id", "case_id", "filename", "notice_text", "entities",
        "risk_level", "risk_score", "is_time_barred",
        "fy", "section", "notice_type", "demand_amount",
        "draft_reply", "draft_status", "status", "created_at",
    }
    assert required_fields.issubset(set(data.keys())), f"Missing: {required_fields - set(data.keys())}"
