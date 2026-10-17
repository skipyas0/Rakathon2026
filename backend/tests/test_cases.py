"""Case/source API reads patient data only from the FHIR server; 503 while it's unreachable."""

import httpx
from fastapi.testclient import TestClient

from mdt_backend import fhir
from mdt_backend.app import app
from mdt_backend.features import cases

client = TestClient(app)
DOWN = httpx.ConnectError("down")


def test_source_comes_from_fhir_server_with_dataset_id(monkeypatch):
    seen = []

    def get(path, **params):
        seen.append(path)
        if path.startswith("Practitioner/"):
            return {"resourceType": "Practitioner", "id": "LEK-1", "name": [{"text": "MUDr. X"}]}
        return {
            "resourceType": "Observation",
            "id": "P09-lab01-hb-f",
            "code": {"text": "Hemoglobin"},
            "valueQuantity": {"value": 104, "unit": "g/l"},
            "effectiveDateTime": "2026-10-06",
            "performer": [{"reference": "Practitioner/LEK-1"}],
        }

    monkeypatch.setattr(fhir, "get", get)
    r = client.get("/api/sources/Observation/P09-lab01-hb_f")
    assert r.status_code == 200
    assert seen == ["Observation/P09-lab01-hb-f", "Practitioner/LEK-1"]  # IRIS id ("_" → "-")
    assert r.json()["author"] == "MUDr. X" and "104" in r.json()["text"]


def test_source_not_on_server_is_404(monkeypatch):
    def get(path, **params):
        raise httpx.HTTPStatusError("404", request=httpx.Request("GET", "x"), response=None)

    monkeypatch.setattr(fhir, "get", get)
    assert client.get("/api/sources/Observation/nope").status_code == 404
    assert client.get("/api/sources/bad type/x").status_code == 404


def test_unreachable_server_is_503_not_a_crash(monkeypatch):
    def get(path, **params):
        raise DOWN

    monkeypatch.setattr(fhir, "get", get)
    assert client.get("/api/cases").status_code == 503
    assert client.get("/api/sources/Observation/x").json() == {"detail": "FHIR server nedostupný"}
    assert client.get("/api/health").json() == {"status": "ok", "fhir": False}


def test_cases_are_the_patients_nominated_on_the_server(monkeypatch):
    task = {
        "resourceType": "Task",
        "id": "P09-task01",
        "for": {"reference": "Patient/P09"},
        "restriction": {"period": {"start": "2026-10-21T14:00:00+02:00"}},
    }
    monkeypatch.setattr(fhir, "get", lambda path, **params: {"entry": [{"resource": task}]})
    assert cases.meetings() == {"p09-2026-10-21": "p09"}  # a patient without a Task is no case


def test_ai_status_follows_the_agent(tmp_path, monkeypatch):
    from mdt_backend import agent

    monkeypatch.setattr(agent, "OUT_DIR", tmp_path)
    monkeypatch.setattr(cases, "meetings", lambda: {"p09-2026-10-21": "p09"})
    status = lambda: client.get("/api/cases/p09-2026-10-21/ai").json()["status"]
    assert status() is None
    agent.running_path("P09").touch()
    assert status() == "running"
    (tmp_path / "p09.json").write_text("{}")
    agent.running_path("P09").unlink()
    assert status() == "done"
    assert client.get("/api/cases/nope/ai").status_code == 404
