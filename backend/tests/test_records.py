import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError

from mdt_backend.app import app
from mdt_backend.features import records
from mdt_backend.features.records import Decision

FINAL = {
    "attendees": [{"name": "MUDr. A", "specialty": "Chirurg"}],
    "intent": "curative",
    "plan": "Resekce",
    "rationale": "Resekabilní",
    "guideline_compliant": True,
    "confirmed_by": "MUDr. Předseda",
}


def test_deviation_needs_reason():
    with pytest.raises(ValidationError):
        Decision(guideline_compliant=False)


def test_confirmed_decision_must_be_complete():
    with pytest.raises(ValidationError):
        Decision(**{**FINAL, "intent": None})
    Decision(**FINAL)


@pytest.fixture
def client(tmp_path, monkeypatch):
    monkeypatch.setattr(records, "RECORDS", tmp_path)
    return TestClient(app)


def status_of(client, case_id):
    return next(c["status"] for c in client.get("/api/cases").json() if c["id"] == case_id)


def test_phases_and_lock(client):
    assert status_of(client, "example") == "prep"
    prep = {"prepared_by": "MUDr. P", "question": ""}  # nomination question exists in the stub
    assert client.put("/api/cases/example/record", json={"prep": prep}).status_code == 200
    assert status_of(client, "example") == "meeting"

    task = {"what": "Informovat pacienta", "done": False}
    body = {"prep": prep, "decision": FINAL, "tasks": [task]}
    assert client.put("/api/cases/example/record", json=body).status_code == 200
    assert status_of(client, "example") == "followup"

    changed = {**body, "decision": {**FINAL, "plan": "Chemoterapie"}}
    assert client.put("/api/cases/example/record", json=changed).status_code == 409

    done = {**body, "tasks": [{**task, "done": True}]}  # tasks stay editable after the lock
    assert client.put("/api/cases/example/record", json=done).status_code == 200
    assert status_of(client, "example") == "closed"


def test_cannot_prepare_without_question(client):
    body = {"prep": {"prepared_by": "MUDr. P"}}
    assert client.put("/api/cases/lung-incomplete/record", json=body).status_code == 422
    body["prep"]["question"] = "Indikace k biopsii?"
    assert client.put("/api/cases/lung-incomplete/record", json=body).status_code == 200


def test_unknown_case_is_404(client):
    assert client.get("/api/cases/nope/record").status_code == 404
