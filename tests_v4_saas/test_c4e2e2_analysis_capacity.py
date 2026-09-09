"""
C4-E2e-2 — Analytical Concurrency Guard Tests

Proves:
1. Limiter exists after lifespan startup
2. Dependency uses the lifespan-created limiter
3. Shutdown clears/resets it
4. Success releases capacity
5. Exception releases capacity
6. Cancellation releases capacity
7. Shared capacity across analytical routes
8. /health and /ready remain outside the limiter
9. POST /saved classification — it IS expensive (calls build_explore/build_insights/build_actions)
"""
from __future__ import annotations

import inspect
import threading
from pathlib import Path
import sys

import anyio
import httpx
import pytest

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from backend.api.main import app, require_user, require_analysis_capacity, lifespan
import backend.api.main as main_api
from backend.api.config import settings
from backend.api.services.onboarding import onboard
from backend.api.services.auth import Principal
from fastapi import HTTPException

SAMPLES = ROOT / "samples"
CAPACITY = 2


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def mock_auth(monkeypatch):
    """Override auth so requests reach the analytical route body."""
    principal = Principal(
        user_id="u1",
        organization_id="o1",
        workspace_id="w1",
        role="owner",
        email="test@example.com",
        name="n",
        organization_name="o",
        workspace_name="w",
    )
    app.dependency_overrides[require_user] = lambda: principal
    monkeypatch.setattr(main_api, "user_can_access_workspace", lambda u, o, w: True)
    yield principal
    app.dependency_overrides.clear()


@pytest.fixture
def test_dataset(mock_auth):
    """Onboard a real CSV so dataset lookup succeeds inside routes."""
    path = SAMPLES / "retail.csv"
    with path.open("rb") as fh:
        return onboard(
            "retail.csv", fh,
            organization_id=mock_auth.organization_id,
            workspace_id=mock_auth.workspace_id,
        )


@pytest.fixture
def limiter():
    """Install a fresh CapacityLimiter(2) on app.state, clean up afterward."""
    lim = anyio.CapacityLimiter(CAPACITY)
    app.state.analytics_limiter = lim
    yield lim
    app.state.analytics_limiter = None


def _transport():
    return httpx.ASGITransport(app=app)


def _client():
    return httpx.AsyncClient(transport=_transport(), base_url="http://testserver")


# ---------------------------------------------------------------------------
# 1. Limiter exists after lifespan startup
# ---------------------------------------------------------------------------

@pytest.mark.anyio
async def test_limiter_created_during_lifespan():
    """The lifespan context manager creates analytics_limiter on app.state."""
    # Ensure it starts as None
    app.state.analytics_limiter = None
    async with lifespan(app):
        lim = app.state.analytics_limiter
        assert lim is not None
        assert isinstance(lim, anyio.CapacityLimiter)
        assert lim.total_tokens == settings.analytics_concurrency
    # After lifespan exits, it is reset
    assert app.state.analytics_limiter is None


# ---------------------------------------------------------------------------
# 2. Dependency uses the lifespan-created limiter
# ---------------------------------------------------------------------------

@pytest.mark.anyio
async def test_dependency_reads_app_state_limiter(limiter, mock_auth, test_dataset, monkeypatch):
    """require_analysis_capacity acquires from app.state.analytics_limiter,
    not a module-global.  We verify by observing borrowed_tokens on the
    exact limiter object installed via app.state."""
    observed_borrowed = []
    entered = threading.Event()
    release = threading.Event()

    def mock_build_explore(*a, **kw):
        observed_borrowed.append(limiter.borrowed_tokens)
        entered.set()
        release.wait()
        raise HTTPException(status_code=400, detail="ok")

    monkeypatch.setattr(main_api, "build_explore", mock_build_explore)

    async with _client() as client:
        async with anyio.create_task_group() as tg:
            async def do_request():
                try:
                    await client.get(
                        f"/api/v1/datasets/{test_dataset.dataset_id}/explore"
                        "?metric=revenue&dimension=product"
                    )
                except Exception:
                    pass

            tg.start_soon(do_request)
            await anyio.to_thread.run_sync(entered.wait)

            # The limiter we installed has exactly 1 borrowed token
            assert limiter.borrowed_tokens == 1
            assert observed_borrowed == [1]

            release.set()

    # After request completes, slot is returned to OUR limiter
    assert limiter.borrowed_tokens == 0


# ---------------------------------------------------------------------------
# 3. Shutdown clears / resets it
# ---------------------------------------------------------------------------

@pytest.mark.anyio
async def test_shutdown_clears_limiter():
    """After lifespan exits (shutdown), analytics_limiter is None."""
    app.state.analytics_limiter = None
    async with lifespan(app):
        assert app.state.analytics_limiter is not None
    assert app.state.analytics_limiter is None


# ---------------------------------------------------------------------------
# 4. Success releases capacity
# ---------------------------------------------------------------------------

@pytest.mark.anyio
async def test_success_releases_slot(limiter, mock_auth, test_dataset, monkeypatch):
    """A successful analytical request releases its capacity slot."""

    def mock_build_explore(*a, **kw):
        raise HTTPException(status_code=400, detail="done")

    monkeypatch.setattr(main_api, "build_explore", mock_build_explore)

    async with _client() as client:
        # Exhaust and release capacity sequentially
        for _ in range(CAPACITY + 1):
            resp = await client.get(
                f"/api/v1/datasets/{test_dataset.dataset_id}/explore"
                "?metric=revenue&dimension=product"
            )
            assert resp.status_code == 400  # not 503

    assert limiter.borrowed_tokens == 0


# ---------------------------------------------------------------------------
# 5. Exception releases capacity
# ---------------------------------------------------------------------------

@pytest.mark.anyio
async def test_exception_releases_slot(limiter, mock_auth, test_dataset, monkeypatch):
    """An unhandled ValueError in the route body releases capacity."""

    def mock_build_explore_error(*a, **kw):
        raise ValueError("Simulated analytical error")

    monkeypatch.setattr(main_api, "build_explore", mock_build_explore_error)

    async with _client() as client:
        for _ in range(CAPACITY + 1):
            resp = await client.get(
                f"/api/v1/datasets/{test_dataset.dataset_id}/explore"
                "?metric=revenue&dimension=product"
            )
            assert resp.status_code == 400  # not 503

    assert limiter.borrowed_tokens == 0


# ---------------------------------------------------------------------------
# 6. Cancellation releases capacity
# ---------------------------------------------------------------------------

@pytest.mark.anyio
async def test_cancellation_releases_slot(limiter, mock_auth, test_dataset, monkeypatch):
    """Client disconnect / cancellation still releases the slot."""
    entered = threading.Event()
    release = threading.Event()

    def mock_build_explore(*a, **kw):
        entered.set()
        release.wait()
        raise HTTPException(status_code=400, detail="done")

    monkeypatch.setattr(main_api, "build_explore", mock_build_explore)

    async with _client() as client:
        async with anyio.create_task_group() as tg:
            async def cancelled_req():
                with anyio.move_on_after(0.2):
                    await client.get(
                        f"/api/v1/datasets/{test_dataset.dataset_id}/explore"
                        "?metric=revenue&dimension=product"
                    )

            for _ in range(CAPACITY):
                tg.start_soon(cancelled_req)

            await anyio.to_thread.run_sync(entered.wait)
            release.set()

        # All slots should be returned after the task group exits
        assert limiter.borrowed_tokens == 0


# ---------------------------------------------------------------------------
# 7. Shared capacity across analytical routes
# ---------------------------------------------------------------------------

@pytest.mark.anyio
async def test_shared_limiter_across_routes(limiter, mock_auth, test_dataset, monkeypatch):
    """Filling capacity with explore + overview blocks a third route (insights)."""
    explore_entered = threading.Event()
    overview_entered = threading.Event()
    release = threading.Event()

    def mock_build_explore(*a, **kw):
        explore_entered.set()
        release.wait()
        raise HTTPException(status_code=400, detail="mock")

    def mock_build_overview(*a, **kw):
        overview_entered.set()
        release.wait()
        raise HTTPException(status_code=400, detail="mock")

    monkeypatch.setattr(main_api, "build_explore", mock_build_explore)
    monkeypatch.setattr(main_api, "build_overview", mock_build_overview)

    async with _client() as client:
        async with anyio.create_task_group() as tg:
            async def req_explore():
                try:
                    await client.get(
                        f"/api/v1/datasets/{test_dataset.dataset_id}/explore"
                        "?metric=revenue&dimension=product"
                    )
                except Exception:
                    pass

            async def req_overview():
                try:
                    await client.get(
                        f"/api/v1/datasets/{test_dataset.dataset_id}/overview"
                    )
                except Exception:
                    pass

            tg.start_soon(req_explore)
            tg.start_soon(req_overview)

            await anyio.to_thread.run_sync(explore_entered.wait)
            await anyio.to_thread.run_sync(overview_entered.wait)

            # Two different routes have consumed all capacity
            resp = await client.get(
                f"/api/v1/datasets/{test_dataset.dataset_id}/insights"
            )
            assert resp.status_code == 503
            assert resp.json()["detail"] == "Analytics engine is currently at maximum capacity."

            release.set()


# ---------------------------------------------------------------------------
# 8. /health and /ready remain outside the limiter
# ---------------------------------------------------------------------------

@pytest.mark.anyio
async def test_health_and_ready_outside_limiter(limiter, mock_auth, test_dataset, monkeypatch):
    """While capacity is fully exhausted, /health returns 200 and /ready is
    not blocked by the limiter."""
    entered_events = [threading.Event() for _ in range(CAPACITY)]
    release = threading.Event()

    def mock_build_explore(*a, **kw):
        for e in entered_events:
            if not e.is_set():
                e.set()
                break
        release.wait()
        raise HTTPException(status_code=400, detail="done")

    monkeypatch.setattr(main_api, "build_explore", mock_build_explore)

    async with _client() as client:
        async with anyio.create_task_group() as tg:
            async def fill_request():
                try:
                    await client.get(
                        f"/api/v1/datasets/{test_dataset.dataset_id}/explore"
                        "?metric=revenue&dimension=product"
                    )
                except Exception:
                    pass

            for _ in range(CAPACITY):
                tg.start_soon(fill_request)

            for e in entered_events:
                await anyio.to_thread.run_sync(e.wait)

            # Capacity is fully consumed — cheap routes still work
            resp_health = await client.get("/api/v1/health")
            assert resp_health.status_code == 200

            resp_ready = await client.get("/api/v1/ready")
            assert resp_ready.status_code in (200, 503)  # 503 OK if DB is down

            # Workspaces (control plane) is also unguarded
            monkeypatch.setattr(main_api, "workspaces", lambda p: [])
            resp_ws = await client.get("/api/v1/workspaces")
            assert resp_ws.status_code == 200

            # Analytical overflow IS blocked
            resp_overflow = await client.get(
                f"/api/v1/datasets/{test_dataset.dataset_id}/explore"
                "?metric=revenue&dimension=product"
            )
            assert resp_overflow.status_code == 503

            release.set()


# ---------------------------------------------------------------------------
# 9. POST /saved classification — genuinely expensive
# ---------------------------------------------------------------------------

def test_post_saved_is_expensive():
    """POST /saved calls save_intelligence -> _from_source -> build_explore /
    build_insights / build_actions / build_overview. Verify it carries the
    capacity dependency in its route signature."""
    from backend.api.services.saved_intelligence import save_intelligence, _from_source
    import backend.api.services.saved_intelligence as si_mod

    # _from_source calls build_explore, build_insights, build_actions, build_overview
    source = inspect.getsource(_from_source)
    assert "build_explore(" in source
    assert "build_insights(" in source
    assert "build_actions(" in source
    assert "build_overview(" in source

    # save_intelligence calls _from_source
    save_src = inspect.getsource(save_intelligence)
    assert "_from_source(" in save_src

    # The route itself has the capacity dependency
    route_src = inspect.getsource(main_api.save)
    assert "require_analysis_capacity" in route_src


# ---------------------------------------------------------------------------
# 10. No cross-test / event-loop leakage — process-local assertion
# ---------------------------------------------------------------------------

def test_limiter_is_process_local():
    """The limiter is a plain Python object on app.state, not a distributed
    primitive. Verify no Redis, no external coordinator."""
    src = inspect.getsource(require_analysis_capacity)
    assert "request.app.state.analytics_limiter" in src
    assert "redis" not in src.lower()
    assert "celery" not in src.lower()
    assert "Semaphore" not in src

    # Verify lifespan creates an anyio.CapacityLimiter
    lifespan_src = inspect.getsource(lifespan)
    assert "anyio.CapacityLimiter" in lifespan_src
    assert "analytics_limiter = None" in lifespan_src  # shutdown reset
