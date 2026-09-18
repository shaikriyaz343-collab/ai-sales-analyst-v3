from backend.api.main import commercial_entitlements
from backend.api.services.auth import Principal
from backend.api.services.commercial_store import CommercialRepository


class MemoryStore:
    def __init__(self) -> None:
        self.items: dict[str, dict] = {}

    def read(self, key: str):
        return self.items.get(key)

    def write(self, key: str, value: dict) -> None:
        self.items[key] = value


def test_commercial_entitlements_route_is_read_only_and_exposes_catalog(monkeypatch) -> None:
    store = MemoryStore()
    repository = CommercialRepository(store)
    monkeypatch.setattr("backend.api.main.runtime_commercial_repository", lambda: repository)

    principal = Principal(
        "user-1",
        "user@example.com",
        "User",
        "org-1",
        "Org",
        "owner",
        "workspace-1",
        "Main Workspace",
    )

    response = commercial_entitlements(principal)

    assert response["organization_id"] == "org-1"
    assert response["subscription"]["plan_id"] == "trial"
    assert response["subscription"]["access_active"] is True
    assert response["entitlements"]["max_workspaces"] == 1
    assert set(plan["plan_id"] for plan in response["catalog"]) == {"trial", "starter", "growth"}
    assert response["usage"] == {}
    assert store.items == {}
