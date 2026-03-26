"""
Tests for API Routes using FastAPI TestClient.
Mocks the LangGraph pipeline to test route logic independently.
"""
import sys
import os
import pytest
import uuid
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
    import app.models.user

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


@pytest.fixture
async def client():
    """Async test client for the FastAPI app (unauthenticated)."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


@pytest.fixture
async def auth_client():
    """Async test client with auth via dependency override."""
    from app.auth.deps import get_current_user
    from app.models.user import User

    # Create a fake user object (no DB needed)
    fake_user = User(
        id="test-user-id-000",
        email="test@taxshield.ai",
        hashed_password="fake",
        full_name="Test User",
        role="admin",
    )

    # Override the dependency so routes skip JWT validation
    app.dependency_overrides[get_current_user] = lambda: fake_user

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac

    # Clean up
    app.dependency_overrides.pop(get_current_user, None)



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
async def test_upload_rejects_non_pdf(auth_client):
    """Should reject non-PDF files with 400"""
    response = await auth_client.post(
        "/api/notices/upload",
        files={"file": ("test.txt", b"not a pdf", "text/plain")},
    )
    assert response.status_code == 400
    assert "PDF" in response.json()["detail"]


@pytest.mark.anyio
async def test_upload_rejects_empty_file(auth_client):
    """Should reject empty PDF with 400"""
    response = await auth_client.post(
        "/api/notices/upload",
        files={"file": ("empty.pdf", b"", "application/pdf")},
    )
    assert response.status_code == 400
    assert "Empty" in response.json()["detail"]


@pytest.mark.anyio
@patch("app.routes.notices.graph")
async def test_upload_success(mock_graph, auth_client):
    """Successful upload should return 202 with notice ID (pipeline runs in background)"""
    mock_graph.ainvoke = AsyncMock(return_value=MOCK_PIPELINE_RESULT)
    
    response = await auth_client.post(
        "/api/notices/upload",
        files={"file": ("test_notice.pdf", b"%PDF-1.4 test content", "application/pdf")},
    )
    assert response.status_code == 202
    data = response.json()
    assert "id" in data
    assert data["status"] == "processing"


@pytest.mark.anyio
@patch("app.routes.notices.graph")
async def test_upload_saves_to_db(mock_graph, auth_client):
    """Upload should create a notice in DB with 'processing' status"""
    mock_graph.ainvoke = AsyncMock(return_value=MOCK_PIPELINE_RESULT)
    
    # Upload returns 202 (background)
    response = await auth_client.post(
        "/api/notices/upload",
        files={"file": ("persist_test.pdf", b"%PDF-1.4 test", "application/pdf")},
    )
    assert response.status_code == 202
    notice_id = response.json()["id"]
    
    # Verify notice exists in DB (may still be processing)
    get_response = await auth_client.get(f"/api/notices/{notice_id}")
    assert get_response.status_code == 200
    data = get_response.json()
    assert data["id"] == notice_id


@pytest.mark.anyio
@patch("app.routes.notices.graph")
async def test_upload_pipeline_failure(mock_graph, auth_client):
    """Pipeline failure in background still returns 202 (error is saved to DB later)"""
    mock_graph.ainvoke = AsyncMock(side_effect=Exception("LLM timeout"))
    
    response = await auth_client.post(
        "/api/notices/upload",
        files={"file": ("fail_test.pdf", b"%PDF-1.4 test", "application/pdf")},
    )
    # Upload always returns 202 now — errors are handled in background
    assert response.status_code == 202


# ═══════════════════════════════════════════
# Notice List/Detail Tests
# ═══════════════════════════════════════════

@pytest.mark.anyio
async def test_list_notices(auth_client):
    """GET /api/notices should return a paginated response"""
    response = await auth_client.get("/api/notices")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, dict)
    assert "items" in data
    assert isinstance(data["items"], list)
    assert "total" in data
    assert "page" in data
    assert "page_size" in data
    assert "total_pages" in data


@pytest.mark.anyio
async def test_get_notice_not_found(auth_client):
    """GET /api/notices/{id} for nonexistent ID should return 404"""
    response = await auth_client.get("/api/notices/nonexistent-id-12345")
    assert response.status_code == 404


# ═══════════════════════════════════════════
# Notifications Tests
# ═══════════════════════════════════════════

@pytest.mark.anyio
async def test_notifications_endpoint(auth_client):
    """GET /api/notifications should return a list (requires auth after Issue 4A)"""
    response = await auth_client.get("/api/notifications")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)


# ═══════════════════════════════════════════
# Response Shape Tests (API Contract)
# ═══════════════════════════════════════════

@pytest.mark.anyio
@patch("app.routes.notices.graph")
async def test_upload_response_shape(mock_graph, auth_client):
    """Upload response must have exactly these fields"""
    mock_graph.ainvoke = AsyncMock(return_value=MOCK_PIPELINE_RESULT)
    
    response = await auth_client.post(
        "/api/notices/upload",
        files={"file": ("shape_test.pdf", b"%PDF-1.4 test", "application/pdf")},
    )
    data = response.json()
    # Issue 12A: Upload now returns 202 with background-processing fields
    required_fields = {"id", "case_id", "status", "message"}
    assert required_fields.issubset(set(data.keys())), f"Missing fields: {required_fields - set(data.keys())}"


@pytest.mark.anyio
@patch("app.routes.notices.graph")
async def test_notice_detail_response_shape(mock_graph, auth_client):
    """Notice detail must include all expected fields"""
    mock_graph.ainvoke = AsyncMock(return_value=MOCK_PIPELINE_RESULT)
    
    # Create a notice first
    upload_resp = await auth_client.post(
        "/api/notices/upload",
        files={"file": ("detail_shape.pdf", b"%PDF-1.4 test", "application/pdf")},
    )
    notice_id = upload_resp.json()["id"]
    
    # Get detail
    response = await auth_client.get(f"/api/notices/{notice_id}")
    data = response.json()
    
    required_fields = {
        "id", "case_id", "filename", "notice_text", "entities",
        "risk_level", "risk_score", "is_time_barred",
        "fy", "section", "notice_type", "demand_amount",
        "draft_reply", "draft_status", "status", "created_at",
    }
    assert required_fields.issubset(set(data.keys())), f"Missing: {required_fields - set(data.keys())}"

