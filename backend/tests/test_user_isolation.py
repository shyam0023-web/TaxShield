"""
Tests for user isolation (Issue 3) — User A cannot see User B's notices.
Uses manual override switching since dependency_overrides is global.
"""
import sys
import os
import pytest
from unittest.mock import AsyncMock, patch

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from httpx import AsyncClient, ASGITransport
from app.main import app
from app.database import engine, Base
from app.auth.deps import get_current_user
from app.models.user import User


@pytest.fixture(scope="module")
def anyio_backend():
    return "asyncio"


@pytest.fixture(autouse=True, scope="module")
async def setup_db():
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


USER_A = User(id="user-a-111", email="alice@test.com", hashed_password="fake", full_name="Alice", role="ca")
USER_B = User(id="user-b-222", email="bob@test.com", hashed_password="fake", full_name="Bob", role="ca")


MOCK_RESULT = {
    "processing_status": "complete",
    "raw_text": "Test notice text",
    "entities": {"GSTIN": [], "DIN": [], "SECTIONS": [], "llm_extracted": {}},
    "risk_level": "LOW",
    "risk_score": 0.2,
    "risk_reasoning": "test",
    "is_time_barred": False,
    "draft_reply": "Test draft",
    "current_agent": "agent4",
}


@pytest.fixture
async def client():
    """Single client — we switch user via dependency override before each request."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac
    app.dependency_overrides.pop(get_current_user, None)


def set_user(user: User):
    """Switch the authenticated user for subsequent requests."""
    app.dependency_overrides[get_current_user] = lambda: user


@pytest.mark.anyio
@patch("app.routes.notices.graph")
async def test_user_a_cannot_see_user_b_notices(mock_graph, client):
    """User A uploads a notice. User B should NOT see it in their list."""
    mock_graph.ainvoke = AsyncMock(return_value=MOCK_RESULT)

    # Upload as User A
    set_user(USER_A)
    resp_a = await client.post(
        "/api/notices/upload",
        files={"file": ("a_notice.pdf", b"%PDF-1.4 user a content", "application/pdf")},
    )
    assert resp_a.status_code == 202
    notice_a_id = resp_a.json()["id"]

    # Verify User A can see it
    set_user(USER_A)
    list_a = await client.get("/api/notices")
    ids_a = [n["id"] for n in list_a.json()["items"]]
    assert notice_a_id in ids_a, "User A should see their own notice"

    # Switch to User B — should NOT see User A's notice
    set_user(USER_B)
    list_b = await client.get("/api/notices")
    ids_b = [n["id"] for n in list_b.json()["items"]]
    assert notice_a_id not in ids_b, "User B should NOT see User A's notice"


@pytest.mark.anyio
@patch("app.routes.notices.graph")
async def test_user_b_cannot_get_user_a_notice_by_id(mock_graph, client):
    """User B tries to GET User A's notice by direct ID → 404."""
    mock_graph.ainvoke = AsyncMock(return_value=MOCK_RESULT)

    # Upload as User A
    set_user(USER_A)
    resp = await client.post(
        "/api/notices/upload",
        files={"file": ("private.pdf", b"%PDF-1.4 secret data", "application/pdf")},
    )
    notice_id = resp.json()["id"]

    # User B tries direct ID access
    set_user(USER_B)
    resp_b = await client.get(f"/api/notices/{notice_id}")
    assert resp_b.status_code == 404, "User B should get 404 for User A's notice"


@pytest.mark.anyio
@patch("app.routes.notices.graph")
async def test_each_user_sees_only_own_notices(mock_graph, client):
    """Both users upload. Each should see only their own."""
    mock_graph.ainvoke = AsyncMock(return_value=MOCK_RESULT)

    # User A uploads
    set_user(USER_A)
    resp_a = await client.post(
        "/api/notices/upload",
        files={"file": ("alice.pdf", b"%PDF-1.4 alice", "application/pdf")},
    )
    id_a = resp_a.json()["id"]

    # User B uploads
    set_user(USER_B)
    resp_b = await client.post(
        "/api/notices/upload",
        files={"file": ("bob.pdf", b"%PDF-1.4 bob", "application/pdf")},
    )
    id_b = resp_b.json()["id"]

    # User A lists → sees own, not B's
    set_user(USER_A)
    list_a = await client.get("/api/notices")
    ids_a = [n["id"] for n in list_a.json()["items"]]
    assert id_a in ids_a
    assert id_b not in ids_a

    # User B lists → sees own, not A's
    set_user(USER_B)
    list_b = await client.get("/api/notices")
    ids_b = [n["id"] for n in list_b.json()["items"]]
    assert id_b in ids_b
    assert id_a not in ids_b
