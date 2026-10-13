"""Admin API. Settings, logs and the token guard need no database."""

from fastapi.testclient import TestClient

from app.config import clear_runtime_overrides, effective_admin_token, get_settings, set_runtime_overrides
from app.main import app
from tests.conftest import requires_db


AUTH = {"X-Admin-Token": effective_admin_token()}


def teardown_function() -> None:
    clear_runtime_overrides()


def test_runtime_overrides_apply_and_validate():
    base = get_settings().benchmark_repetitions
    set_runtime_overrides({"benchmark_repetitions": base + 5})
    assert get_settings().benchmark_repetitions == base + 5
    try:
        set_runtime_overrides({"database_url": "postgresql://x"})
        raise AssertionError("database_url must not be adjustable")
    except ValueError:
        pass
    clear_runtime_overrides()
    assert get_settings().benchmark_repetitions == base


def test_settings_endpoint_masks_credentials_and_rejects_bad_values():
    with TestClient(app) as c:
        body = c.get("/api/admin/settings", headers=AUTH).json()
        assert ":***@" in body["values"]["database_url"] or "@" not in body["values"]["database_url"]
        assert "admin_token" not in body["values"]
        assert c.put("/api/admin/settings", json={"values": {"benchmark_repetitions": "lots"}}, headers=AUTH).status_code == 422
        ok = c.put("/api/admin/settings", json={"values": {"benchmark_repetitions": 3}}, headers=AUTH)
        assert ok.status_code == 200 and ok.json()["overrides"] == {"benchmark_repetitions": 3}
        assert c.delete("/api/admin/settings", headers=AUTH).json()["overrides"] == {}


def test_logs_endpoint_returns_recent_records():
    with TestClient(app) as c:
        rows = c.get("/api/admin/logs", params={"limit": 50}, headers=AUTH).json()
        assert isinstance(rows, list)
        assert all({"time", "level", "logger", "message"} <= set(r) for r in rows)


def test_admin_token_guard(monkeypatch):
    monkeypatch.setenv("GREENCODE_ADMIN_TOKEN", "secret")
    get_settings.cache_clear()
    try:
        with TestClient(app) as c:
            assert c.get("/api/admin/settings", headers=AUTH).status_code == 401
            assert c.get("/api/admin/settings", headers={"X-Admin-Token": "secret"}).status_code == 200
            assert c.get("/api/rules").status_code == 200  # non-admin routes stay open
    finally:
        monkeypatch.delenv("GREENCODE_ADMIN_TOKEN")
        get_settings.cache_clear()


@requires_db
def test_overview_and_carbon_factor_crud():
    with TestClient(app) as c:
        ov = c.get("/api/admin/overview", headers=AUTH).json()
        assert "counts" in ov["store"] and ov["host"]["python"]
        created = c.post("/api/admin/carbon-factors", json={"region": "ZZ", "year": 2030, "grams_co2e_per_kwh": 1.5,
                                                            "source": "test"}, headers=AUTH)
        assert created.status_code == 201, created.text
        fid = created.json()["id"]
        dup = c.post("/api/admin/carbon-factors", json={"region": "ZZ", "year": 2030, "grams_co2e_per_kwh": 1.5,
                                                        "source": "test"}, headers=AUTH)
        assert dup.status_code == 409
        upd = c.put(f"/api/admin/carbon-factors/{fid}", json={"region": "ZZ", "year": 2030, "grams_co2e_per_kwh": 2.0,
                                                               "source": "test", "notes": "edited"}, headers=AUTH)
        assert upd.status_code == 200 and upd.json()["notes"] == "edited"
        assert c.delete(f"/api/admin/carbon-factors/{fid}", headers=AUTH).status_code == 204
        assert c.post("/api/admin/maintenance/mark-stuck-failed", headers=AUTH).json()["updated"] >= 0
        assert c.get("/api/admin/export/results.csv", headers=AUTH).status_code == 200
