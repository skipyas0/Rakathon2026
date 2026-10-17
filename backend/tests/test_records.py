import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError

from mdt_backend import agent
from mdt_backend.app import app
from mdt_backend.briefing import Case, DecisionSupport
from mdt_backend.features import cases, export, records, report
from mdt_backend.features.records import Decision, Triage
from mdt_backend.provenance import Statement

FINAL = {
    "attendees": [{"name": "MUDr. A", "specialty": "Chirurg"}],
    "intents": ["curative"],
    "plan": "Resekce",
    "rationale": "Resekabilní",
    "guideline_compliant": True,
    "confirmed_by": "Koordinátor/ka",
    "confirmed_at": "2026-10-17T10:00:00Z",
}


def test_deviation_needs_reason():
    with pytest.raises(ValidationError):
        Decision(guideline_compliant=False)


def test_confirmed_decision_must_be_complete():
    with pytest.raises(ValidationError):
        Decision(**{**FINAL, "intents": []})
    Decision(**FINAL)
    Decision(**{**FINAL, "intents": ["palliative", "supportive"]})


def test_records_with_one_intent_still_load():
    assert Decision(intent="palliative").intents == ["palliative"]
    assert Decision(intent=None).intents == []
    final = {k: v for k, v in FINAL.items() if k != "intents"}
    Decision(**final, intent="curative")


def test_guideline_assessment_is_saved_with_decision():
    body = {
        **FINAL,
        "guideline_assessment": {
            "status": "deviation",
            "statement": {
                "text": "Postup se odchyluje od doporučení.",
                "origin": "ai",
                "model": "test",
                "sources": [
                    {
                        "reference": "guideline:PRS-3.3",
                        "title": "Doporučený postup",
                        "excerpt": "Relevantní pasáž.",
                    }
                ],
            },
            "compared_plan": "Resekce",
            "compared_rationale": "Zvolená možnost",
            "compared_intent": "curative",  # saved before several could be chosen
            "recommendation": "Doporučená systémová léčba",
            "recommendation_sources": [
                {
                    "reference": "guideline:PRS-3.3",
                    "title": "Doporučený postup",
                    "excerpt": "Relevantní pasáž.",
                }
            ],
        },
    }
    decision = Decision(**body)
    assert decision.guideline_assessment.statement.sources[0].reference == "guideline:PRS-3.3"
    assert decision.guideline_assessment.compared_intents == ["curative"]


def case(case_id: str, question: str | None) -> Case:
    q = question and Statement(text=question, origin="human", confirmed_by="MUDr. Odesílající")
    empty = DecisionSupport(options=[], trials=[], questions=[])
    return Case(id=case_id, patient="Patient/t", label="Test", tumour="breast", question=q,
                summary=[], timeline=[], red_flags=[], sections=[], decision_support=empty)  # fmt: skip


@pytest.fixture
def client(tmp_path, monkeypatch):
    # own test cases, served as finished agent briefings, so no FHIR server is needed
    test_cases = (case("example", "Resekabilita?"), case("lung-incomplete", None))
    for c in test_cases:
        (tmp_path / f"{c.id}.json").write_text(c.model_dump_json(), "utf-8")
    monkeypatch.setattr(agent, "OUT_DIR", tmp_path)
    monkeypatch.setattr(cases, "meetings", lambda: {c.id: c.id for c in test_cases})
    monkeypatch.setattr(cases, "record", lambda patient: cases.Bundle({"entry": []}))
    monkeypatch.setattr(records, "RECORDS", tmp_path / "records")
    monkeypatch.setattr(export, "DRAFTS", tmp_path / "zavery")  # no AI draft: history unfilled
    monkeypatch.setattr(
        report,
        "_evidence",
        lambda patient: [
            {"resourceType": "Patient", "id": "t", "name": [{"text": "Test"}]},
        ],
    )
    return TestClient(app)


BOARD = [
    {"name": n, "specialty": s}
    for n, s in (("A", "surgery"), ("B", "oncology"), ("C", "radiology"))
]


def status_of(client, case_id):
    return next(c["status"] for c in client.get("/api/cases").json() if c["id"] == case_id)


def reviewed(client, body):
    draft = {**body, "decision": {**body["decision"], "confirmed_by": None, "confirmed_at": None}}
    result = client.post("/api/cases/example/report", json=draft)
    assert result.status_code == 200, result.text
    return {**body, "decision": {**body["decision"], "report_revision": result.json()["revision"]}}


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
    body = reviewed(client, {"prep": prep, "board": BOARD, "decision": FINAL, "tasks": [task]})
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


def test_history_lists_the_patients_meetings(client):
    h = client.get("/api/cases/example/history").json()
    # both test cases belong to "Patient/t": one patient, two meetings
    assert {m["id"] for m in h["meetings"]} == {"example", "lung-incomplete"}
    assert h["documents"] == []  # no health record behind the test cases
    assert client.get("/api/cases/nope/history").status_code == 404


def test_confirmed_conclusion_downloads_as_pdf(client):
    try:
        from mdt_backend.pdf import _font_paths

        _font_paths()
    except FileNotFoundError:
        pytest.skip("no TrueType font with Czech glyphs on this machine")
    assert client.get("/api/cases/example/zaver.pdf").status_code == 409  # not confirmed yet
    body = reviewed(client, {"board": BOARD, "decision": FINAL})
    assert client.put("/api/cases/example/record", json=body).status_code == 200
    r = client.get("/api/cases/example/zaver.pdf")
    assert r.status_code == 200 and r.content.startswith(b"%PDF")
    assert "inline" in r.headers["content-disposition"]  # previewed on the Export step
    r = client.get("/api/cases/example/zaver.docx")
    assert r.status_code == 200 and r.content.startswith(b"PK")  # docx = zip
    assert "attachment" in r.headers["content-disposition"]


def test_no_lock_without_consensus(client):
    against = [{**BOARD[0], "supports": False}, *BOARD[1:]]
    body = {"board": against, "decision": FINAL}
    assert client.put("/api/cases/example/record", json=body).status_code == 422
    body = reviewed(client, {**body, "board": BOARD})
    assert client.put("/api/cases/example/record", json=body).status_code == 200


def test_reset_deletes_even_a_confirmed_record(client):
    body = reviewed(client, {"board": BOARD, "decision": FINAL})
    assert client.put("/api/cases/example/record", json=body).status_code == 200
    assert client.delete("/api/cases/example/record").status_code == 204
    assert client.get("/api/cases/example/record").json()["decision"]["confirmed_by"] is None
    assert status_of(client, "example") == "prep"
    assert client.delete("/api/cases/nope/record").status_code == 404


def test_specialist_stanovisko_and_stance(client, monkeypatch):
    from mdt_backend.config import settings
    from mdt_backend.provenance import Source

    url = "/api/cases/example/stanovisko/surgery"
    assert client.patch(url, json={"supports": False}).status_code == 404  # not on the board yet
    assert client.put("/api/cases/example/record", json={"board": BOARD}).status_code == 200
    draft = Statement(
        text="Resekabilní.", origin="ai", model="m", sources=[Source(reference="X/1")]
    )
    monkeypatch.setattr(settings, "azure_api_key", "test")
    monkeypatch.setattr(agent, "Record", lambda patient: None)
    monkeypatch.setattr(agent, "stanovisko", lambda rec, key: draft)
    assert client.post(f"{url}/generate").json()["stanoviska"]["surgery"]["origin"] == "ai"

    edited = {**draft.model_dump(mode="json"), "text": "Neresekabilní.", "confirmed_by": "MUDr. A"}
    assert client.patch(url, json={"statement": edited}).status_code == 422  # AI text, edited
    signed = {**draft.model_dump(mode="json"), "confirmed_by": "MUDr. A"}
    assert client.patch(url, json={"statement": signed, "supports": False}).status_code == 200
    # the coordinator's stale copy (no stanovisko, everyone supports) doesn't overwrite them
    r = client.put("/api/cases/example/record", json={"board": BOARD}).json()
    assert r["stanoviska"]["surgery"]["confirmed_by"] == "MUDr. A"
    assert next(m for m in r["board"] if m["specialty"] == "surgery")["supports"] is False
    # anyone against blocks the lock, then the lock freezes the stanoviska
    assert client.put("/api/cases/example/record", json={**r, "decision": FINAL}).status_code == 422
    assert client.patch(url, json={"supports": True}).status_code == 200
    body = reviewed(client, {**r, "decision": FINAL})
    assert client.put("/api/cases/example/record", json=body).status_code == 200
    assert client.patch(url, json={"supports": False}).status_code == 409


def test_quick_picks_read_as_one_line_in_plans_order():
    d = Decision(
        choices={
            "surgery": [{"option": "Chirurgicky řešitelné", "text": "pravostranná hemikolektomie"}],
            "oncology": [
                {"option": "Neoadjuvantní léčba", "sub": ["Chemoterapie", "Radioterapie"]},
                {"option": "Symptomatická péče"},
            ],
        }
    )
    assert records.choices_text(d) == (
        "Onkologie: Neoadjuvantní léčba (Chemoterapie, Radioterapie), Symptomatická péče; "
        "Chirurgie: Chirurgicky řešitelné: pravostranná hemikolektomie"
    )
    assert records.choices_text(Decision()) == ""
    with pytest.raises(ValidationError):  # rows are Plán's, nothing else
        Decision(choices={"cardiology": [{"option": "x"}]})
