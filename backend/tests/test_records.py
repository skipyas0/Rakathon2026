import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError

from mdt_backend.app import app
from mdt_backend.briefing import Case, DecisionSupport
from mdt_backend.features import cases, records
from mdt_backend.features.records import Decision, Triage
from mdt_backend.provenance import Statement

FINAL = {
    "attendees": [{"name": "MUDr. A", "specialty": "Chirurg"}],
    "intent": "curative",
    "plan": "Resekce",
    "rationale": "Resekabilní",
    "guideline_compliant": True,
    "consent": ["MUDr. A"],
    "confirmed_by": "Koordinátorka K",
}


def test_deviation_needs_reason():
    with pytest.raises(ValidationError):
        Decision(guideline_compliant=False)


def test_confirmed_decision_must_be_complete():
    with pytest.raises(ValidationError):
        Decision(**{**FINAL, "intent": None})
    with pytest.raises(ValidationError):  # consensus: every attendee must agree
        Decision(**{**FINAL, "consent": []})
    Decision(**FINAL)


def case(case_id: str, question: str | None) -> Case:
    q = question and Statement(text=question, origin="human", confirmed_by="MUDr. Odesílající")
    empty = DecisionSupport(options=[], trials=[], questions=[])
    return Case(id=case_id, patient="Patient/t", label="Test", tumour="breast", question=q,
                summary=[], timeline=[], red_flags=[], sections=[], decision_support=empty)  # fmt: skip


@pytest.fixture
def client(tmp_path, monkeypatch):
    # own test cases as stubs: the dataset isn't in git, so CI has no FHIR cases
    stubs = tmp_path / "stubs"
    stubs.mkdir()
    for c in (case("example", "Resekabilita?"), case("lung-incomplete", None)):
        (stubs / f"{c.id}.json").write_text(c.model_dump_json(), "utf-8")
    monkeypatch.setattr(cases, "STUBS", stubs)
    monkeypatch.setattr(records, "RECORDS", tmp_path / "records")
    return TestClient(app)


BOARD = [
    {"name": n, "specialty": s}
    for n, s in (("A", "surgery"), ("B", "oncology"), ("C", "radiology"))
]


def status_of(client, case_id):
    return next(c["status"] for c in client.get("/api/cases").json() if c["id"] == case_id)


def test_phases_and_lock(client):
    assert status_of(client, "example") == "prep"
    prep = {"prepared_by": "MUDr. P", "question": ""}  # nomination question exists in the stub
    assert client.put("/api/cases/example/record", json={"prep": prep}).status_code == 422  # board
    assert (
        client.put("/api/cases/example/record", json={"prep": prep, "board": BOARD}).status_code
        == 200
    )
    assert status_of(client, "example") == "meeting"
    agenda = {c["id"]: c for c in client.get("/api/cases").json()}
    assert agenda["example"]["specialties"] == ["oncology", "radiology", "surgery"]

    task = {"what": "Informovat pacienta", "done": False}
    body = {"prep": prep, "board": BOARD, "decision": FINAL, "tasks": [task]}
    assert client.put("/api/cases/example/record", json=body).status_code == 200
    assert status_of(client, "example") == "followup"

    changed = {**body, "decision": {**FINAL, "plan": "Chemoterapie"}}
    assert client.put("/api/cases/example/record", json=changed).status_code == 409

    done = {**body, "tasks": [{**task, "done": True}]}  # tasks stay editable after the lock
    assert client.put("/api/cases/example/record", json=done).status_code == 200
    assert status_of(client, "example") == "closed"


def test_cannot_prepare_without_question(client):
    body = {"prep": {"prepared_by": "MUDr. P"}, "board": BOARD}
    assert client.put("/api/cases/lung-incomplete/record", json=body).status_code == 422
    body["prep"]["question"] = "Indikace k biopsii?"
    assert client.put("/api/cases/lung-incomplete/record", json=body).status_code == 200


def test_triage_needs_assignee_or_reason():
    by = {"by": "K", "at": "2026-10-17T10:00:00Z"}
    with pytest.raises(ValidationError):
        Triage(action="before", **by)
    with pytest.raises(ValidationError):
        Triage(action="dismissed", **by)
    Triage(action="before", assignee="pathology", **by)


def test_unknown_case_is_404(client):
    assert client.get("/api/cases/nope/record").status_code == 404
