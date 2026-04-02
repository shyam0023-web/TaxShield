"""
Tests for Auth Routes (register, login, me) and Draft Routes (approve, reject, edit).
Issue 10A: These are the highest-risk untested surfaces.
"""
import sys
import os
import pytest
from unittest.mock import patch, AsyncMock

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from httpx import AsyncClient, ASGITransport
from app.main import app
from app.database import engine, Base


# ═══════════════════════════════════════════
# Fixtures
# ═══════════════════════════════════════════

@pytest.fixture(scope="module")
def anyio_backend():
    return "asyncio"


@pytest.fixture(autouse=True, scope="module")
async def setup_db():
    """Create tables before tests, drop after."""
    import app.models.notice
    import app.models.draft
    import app.models.case
    import app.models.user
    import app.models.audit_log

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


@pytest.fixture
async def client():
    """Unauthenticated client."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


@pytest.fixture
async def auth_client():
    """Authenticated client via dependency override."""
    from app.auth.deps import get_current_user
    from app.models.user import User

    fake_user = User(
        id="test-user-auth-001",
        email="authtest@taxshield.ai",
        hashed_password="fake",
        full_name="Auth Test User",
        role="admin",
    )
    app.dependency_overrides[get_current_user] = lambda: fake_user
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac
    app.dependency_overrides.pop(get_current_user, None)


# ═══════════════════════════════════════════
# Auth: Register Tests
# ═══════════════════════════════════════════

@pytest.mark.anyio
async def test_register_success(client):
    """POST /api/auth/register with valid data should return token + user"""
    response = await client.post("/api/auth/register", json={
        "email": "newuser@test.com",
        "password": "securepass123",
        "full_name": "New User",
    })
    assert response.status_code == 200
    data = response.json()
    assert "token" in data
    assert data["user"]["email"] == "newuser@test.com"
    assert data["user"]["role"] == "ca"  # default role


@pytest.mark.anyio
async def test_register_duplicate_email(client):
    """Registering same email twice should return 409"""
    payload = {
        "email": "duplicate@test.com",
        "password": "securepass123",
        "full_name": "Dup User",
    }
    # First registration
    await client.post("/api/auth/register", json=payload)
    # Second should fail
    response = await client.post("/api/auth/register", json=payload)
    assert response.status_code == 409
    assert "already registered" in response.json()["detail"]


@pytest.mark.anyio
async def test_register_short_password(client):
    """Password < 8 chars should return 400"""
    response = await client.post("/api/auth/register", json={
        "email": "shortpw@test.com",
        "password": "abc",
        "full_name": "Short PW",
    })
    assert response.status_code == 400
    assert "8 characters" in response.json()["detail"]


@pytest.mark.anyio
async def test_register_invalid_email(client):
    """Invalid email format should return 422"""
    response = await client.post("/api/auth/register", json={
        "email": "not-an-email",
        "password": "securepass",
        "full_name": "Bad Email",
    })
    assert response.status_code == 422  # Pydantic validation error


# ═══════════════════════════════════════════
# Auth: Login Tests
# ═══════════════════════════════════════════

@pytest.mark.anyio
async def test_login_success(client):
    """Login with correct credentials should return token"""
    # Register first
    await client.post("/api/auth/register", json={
        "email": "loginuser@test.com",
        "password": "correctpass1",
        "full_name": "Login User",
    })
    # Login
    response = await client.post("/api/auth/login", json={
        "email": "loginuser@test.com",
        "password": "correctpass1",
    })
    assert response.status_code == 200
    data = response.json()
    assert "token" in data
    assert data["user"]["email"] == "loginuser@test.com"


@pytest.mark.anyio
async def test_login_wrong_password(client):
    """Login with wrong password should return 401"""
    # Register
    await client.post("/api/auth/register", json={
        "email": "wrongpw@test.com",
        "password": "correctpass1",
        "full_name": "Wrong PW",
    })
    # Login with wrong password
    response = await client.post("/api/auth/login", json={
        "email": "wrongpw@test.com",
        "password": "wrongpassword",
    })
    assert response.status_code == 401
    assert "Invalid" in response.json()["detail"]


@pytest.mark.anyio
async def test_login_nonexistent_email(client):
    """Login with unknown email should return 401"""
    response = await client.post("/api/auth/login", json={
        "email": "noone@test.com",
        "password": "anypass",
    })
    assert response.status_code == 401


# ═══════════════════════════════════════════
# Auth: Me Endpoint
# ═══════════════════════════════════════════

@pytest.mark.anyio
async def test_me_unauthenticated(client):
    """GET /api/auth/me without token should return 401/403"""
    response = await client.get("/api/auth/me")
    assert response.status_code in (401, 403)


@pytest.mark.anyio
async def test_me_authenticated(auth_client):
    """GET /api/auth/me with valid token should return user data"""
    response = await auth_client.get("/api/auth/me")
    assert response.status_code == 200
    data = response.json()
    assert data["email"] == "authtest@taxshield.ai"
    assert "id" in data
    assert "role" in data


# ═══════════════════════════════════════════
# Draft: Approve/Reject/Edit Tests
# ═══════════════════════════════════════════

@pytest.mark.anyio
@patch("app.routes.notices.graph")
async def test_approve_draft(mock_graph, auth_client):
    """POST /api/notices/{id}/approve should set draft_status to approved"""
    mock_graph.ainvoke = AsyncMock(return_value={
        "raw_text": "test", "entities": {"SECTIONS": [], "llm_extracted": {}},
        "risk_level": "LOW", "risk_score": 0.1, "draft_reply": "Draft text",
        "is_time_barred": False, "current_agent": "agent4",
    })
    # Create notice
    upload = await auth_client.post(
        "/api/notices/upload",
        files={"file": ("approve.pdf", b"%PDF-1.4 test", "application/pdf")},
    )
    notice_id = upload.json()["id"]

    # We need the notice to have a draft_reply for approval to work.
    # Since pipeline runs in background, directly set it via the edit endpoint.
    await auth_client.put(f"/api/notices/{notice_id}/draft", json={
        "draft_reply": "Test draft for approval",
    })

    # Approve
    response = await auth_client.post(f"/api/notices/{notice_id}/approve", json={
        "feedback": "Looks good",
    })
    assert response.status_code == 200
    assert response.json()["draft_status"] == "approved"


@pytest.mark.anyio
@patch("app.routes.notices.graph")
async def test_reject_draft(mock_graph, auth_client):
    """POST /api/notices/{id}/reject should set draft_status to rejected"""
    mock_graph.ainvoke = AsyncMock(return_value={
        "raw_text": "test", "entities": {"SECTIONS": [], "llm_extracted": {}},
        "risk_level": "LOW", "risk_score": 0.1, "draft_reply": "Draft text",
        "is_time_barred": False, "current_agent": "agent4",
    })
    upload = await auth_client.post(
        "/api/notices/upload",
        files={"file": ("reject.pdf", b"%PDF-1.4 test", "application/pdf")},
    )
    notice_id = upload.json()["id"]

    await auth_client.put(f"/api/notices/{notice_id}/draft", json={
        "draft_reply": "Test draft for rejection",
    })

    response = await auth_client.post(f"/api/notices/{notice_id}/reject", json={
        "feedback": "Needs more citations",
    })
    assert response.status_code == 200
    assert response.json()["draft_status"] == "rejected"


@pytest.mark.anyio
@patch("app.routes.notices.graph")
async def test_edit_draft(mock_graph, auth_client):
    """PUT /api/notices/{id}/draft should update draft text and reset status"""
    mock_graph.ainvoke = AsyncMock(return_value={
        "raw_text": "test", "entities": {"SECTIONS": [], "llm_extracted": {}},
        "risk_level": "LOW", "risk_score": 0.1, "draft_reply": "Original draft",
        "is_time_barred": False, "current_agent": "agent4",
    })
    upload = await auth_client.post(
        "/api/notices/upload",
        files={"file": ("edit.pdf", b"%PDF-1.4 test", "application/pdf")},
    )
    notice_id = upload.json()["id"]

    response = await auth_client.put(f"/api/notices/{notice_id}/draft", json={
        "draft_reply": "Human-edited draft text",
    })
    assert response.status_code == 200
    data = response.json()
    assert data["draft_status"] == "draft_ready"
    assert data["draft_reply"] == "Human-edited draft text"


@pytest.mark.anyio
async def test_approve_nonexistent_notice(auth_client):
    """Approving a nonexistent notice should return 404"""
    response = await auth_client.post("/api/notices/fake-id/approve", json={
        "feedback": "nope",
    })
    assert response.status_code == 404


@pytest.mark.anyio
async def test_edit_draft_unauthenticated(client):
    """PUT /api/notices/{id}/draft without auth should return 401/403"""
    response = await client.put("/api/notices/any-id/draft", json={
        "draft_reply": "hack attempt",
    })
    assert response.status_code in (401, 403)
