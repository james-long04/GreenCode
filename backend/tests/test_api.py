import time

from fastapi.testclient import TestClient

from app.main import app
from tests.conftest import requires_db


def test_rules_endpoint_needs_no_db():
    with TestClient(app) as c:
        rules = c.get("/api/rules").json()
        assert any(r["rule_id"] == "PY001" for r in rules) and any(r["rule_id"] == "SQL001" for r in rules)
        assert len(c.get("/api/suite/cases").json()) >= 20


@requires_db
def test_project_analysis_optimisation_flow():
    with TestClient(app) as c:
        assert c.get("/api/health").json()["database"] is True
        pid = c.post("/api/projects", json={"name": "api"}).json()["id"]
        body = {"project_id": pid, "name": "x", "language": "python", "source": "def solve(xs):\n    return sorted(xs)[0]\n",
                "case_spec": {"entry_point": "solve", "tests": [{"name": "t", "args": "([3,1,2],)"}],
                              "benchmark": {"setup": "xs=list(range(5000,0,-1))", "call": "solve(xs)"}}}
        a = c.post("/api/analyses", json=body).json()
        assert [f["rule_id"] for f in a["findings"]] == ["PY007"]
        o = c.post("/api/optimisations", json={"analysis_id": a["id"], "condition": "greencode"})
        assert o.status_code == 202
        oid = o.json()["id"]
        for _ in range(100):
            status = c.get(f"/api/optimisations/{oid}").json()["status"]
            if status in {"benchmarked", "rejected", "failed"}:
                break
            time.sleep(0.2)
        assert status == "benchmarked"
        assert c.get("/api/results/summary", params={"project_id": pid}).json()["total_runs"] == 1
        assert c.get("/api/carbon-factors").json()
        assert c.delete(f"/api/projects/{pid}").status_code == 204
