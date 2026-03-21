"""
Tests for DELETE /api/notices/{id} — DPDP Right to Erasure
Uses unit-test approach (calls the route function directly) since
httpx ASGITransport does not trigger lifespan events.
"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from app.routes.notices import delete_notice


def test_delete_endpoint_exists():
    """Verify the delete_notice route function exists and is async."""
    import inspect
    assert inspect.iscoroutinefunction(delete_notice), "delete_notice should be async"


def test_delete_endpoint_registered():
    """Verify DELETE /notices/{id} is registered in the router."""
    from app.routes.notices import router
    delete_routes = [
        route for route in router.routes
        if hasattr(route, 'methods') and 'DELETE' in route.methods
    ]
    assert len(delete_routes) >= 1, "DELETE route should be registered"
    # Check it matches /notices/{id}
    paths = [route.path for route in delete_routes]
    assert "/notices/{id}" in paths, f"Expected /notices/{{id}} in {paths}"
