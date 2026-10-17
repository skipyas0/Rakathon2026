import copy
import datetime as dt
import io
import json

import pytest
from fastapi.testclient import TestClient
from pypdf import PdfReader

from mdt_backend import llm
from mdt_backend.app import app
from mdt_backend.briefing import Case, DecisionSupport
from mdt_backend.features import cases, export, records, report
from mdt_backend.provenance import Source, Statement


@pytest.fixture
def setup(tmp_path, monkeypatch):
    case = Case(
        id="example",
        patient="Patient/p",
        label="Pacient test",
        tumour="breast",
        question=Statement(text="Postup?", origin="human", confirmed_by="Odesílající"),
        summary=[
            Statement(
                text="AI souhrn",
                origin="ai",
                model="test-model:prompt-v1",
                sources=[Source(reference="Observation/o#answer", excerpt="Původní hodnota")],
            )
        ],
        timeline=[],
        sections=[],
        red_flags=[],
        decision_support=DecisionSupport(options=[], trials=[], questions=[]),
    )
    resources = [
        {"resourceType": "Patient", "id": "p", "name": [{"text": "Pacient test"}]},
        {
            "resourceType": "Condition",
            "id": "c",
            "subject": {"reference": "Patient/p"},
            "code": {"text": "Diagnóza"},
        },
        {
            "resourceType": "Observation",
            "id": "o",
            "status": "final",
            "subject": {"reference": "Patient/p"},
            "code": {"text": "Nález"},
            "valueString": "Původní hodnota",
            "meta": {"versionId": "1"},
        },
    ]
    monkeypatch.setattr(records, "RECORDS", tmp_path)
    monkeypatch.setattr(records, "case_ids", lambda: ["example"])
    monkeypatch.setattr(cases, "get_case", lambda case_id: case)
    monkeypatch.setattr(report, "_evidence", lambda patient: copy.deepcopy(resources))
    monkeypatch.setattr(llm, "chat_json", lambda *a, **k: pytest.fail("No AI call is allowed"))
    client = TestClient(app)
    body = records.CaseRecord(
        board=[records.Member(name="A", specialty="oncology")],
        decision=records.Decision(
            attendees=[records.Attendee(name="A", specialty="Klinická onkologie")],
            intents=["palliative"],
            plan="Doporučený postup",
            rationale="Zdůvodnění",
            guideline_compliant=True,
        ),
        tasks=[records.Task(what="Kontrola", who="Onkologie", due=dt.date(2026, 12, 1))],
    ).model_dump(mode="json")
    return client, body, resources, case


def prepare(client, body):
    result = client.post("/api/cases/example/report", json=body)
    assert result.status_code == 200, result.text
    return result.json()


def final(body, revision):
    return {
        **body,
        "decision": {
            **body["decision"],
            "report_revision": revision,
            "confirmed_by": "Koordinátor/ka",
            "confirmed_at": "2026-10-17T10:00:00Z",
        },
    }


def test_confirmation_requires_a_prepared_report(setup):
    client, body, _, _ = setup
    result = client.put("/api/cases/example/record", json=final(body, None))
    assert result.status_code == 409
    assert "zprávu" in result.json()["detail"]
    assert client.get("/api/cases/example/zaver.fhir.json").status_code == 409


def test_report_contains_evidence_existing_ai_and_action_plan(setup):
    client, body, _, _ = setup
    snapshot = prepare(client, body)
    assert any(s["origin"] == "ai" for sec in snapshot["sections"] for s in sec["items"])
    assert any("Kontrola" in s["text"] for sec in snapshot["sections"] for s in sec["items"])
    assert any("mCODE" in warning for warning in snapshot["warnings"])
    assert prepare(client, body) == snapshot
    assert client.get("/api/cases/example/report").status_code == 409


@pytest.mark.parametrize("missing", ["patient", "referenced-source"])
def test_report_rejects_incomplete_evidence(setup, missing):
    client, body, resources, _ = setup
    if missing == "patient":
        resources.pop(0)
    else:
        resources[-1]["derivedFrom"] = [{"reference": "DiagnosticReport/missing"}]
    result = client.post("/api/cases/example/report", json=body)
    assert result.status_code == 422
    assert client.get("/api/cases/example/report").status_code == 409


def test_questionnaire_review_preserves_multiple_and_nested_answers():
    response = {
        "resourceType": "QuestionnaireResponse",
        "questionnaire": "https://example.org/Questionnaire/proms",
        "item": [
            {
                "linkId": "symptoms",
                "text": "Obtíže",
                "answer": [
                    {
                        "valueString": "Bolest",
                        "item": [{"linkId": "severity", "answer": [{"valueInteger": 7}]}],
                    },
                    {"valueString": "Únava"},
                ],
                "item": [{"linkId": "comment", "answer": [{"valueString": "Večer"}]}],
            }
        ],
    }
    text = report.evidence_text(response)
    for answer in ("Bolest", "Únava", "[severity]: 7", "[comment]: Večer"):
        assert answer in text


@pytest.mark.parametrize("change", ["plan", "source", "ai", "task", "board"])
def test_stale_revision_cannot_be_confirmed(setup, change):
    client, body, resources, case = setup
    snapshot = prepare(client, body)
    payload = final(body, snapshot["revision"])
    if change == "plan":
        payload["decision"]["plan"] = "Jiný postup"
    elif change == "source":
        resources[-1]["meta"]["versionId"] = "2"
    elif change == "ai":
        case.summary[0].text = "Změněný AI souhrn"
    elif change == "task":
        payload["tasks"][0]["who"] = "Někdo jiný"
    else:
        payload["board"][0]["name"] = "Jiný člen"
    result = client.put("/api/cases/example/record", json=payload)
    assert result.status_code == 409


def test_approved_fhir_export_is_frozen_and_needs_no_live_server(setup, monkeypatch):
    client, body, _, _ = setup
    snapshot = prepare(client, body)
    result = client.put("/api/cases/example/record", json=final(body, snapshot["revision"]))
    assert result.status_code == 200, result.text

    def no_read(*args, **kwargs):
        pytest.fail("Approved exports must not read current clinical evidence")

    monkeypatch.setattr(report, "_evidence", no_read)
    monkeypatch.setattr(cases, "get_case", no_read)
    monkeypatch.setattr(records, "case_ids", no_read)
    output = client.get("/api/cases/example/zaver.fhir.json")
    assert output.status_code == 200
    assert output.headers["content-type"].startswith("application/fhir+json")
    assert output.content == client.get("/api/cases/example/zaver.fhir.json").content
    bundle = output.json()
    assert bundle["type"] == "document"
    assert bundle["entry"][0]["resource"]["resourceType"] == "Composition"
    full_urls = {e["fullUrl"] for e in bundle["entry"]}

    def check(value):
        if isinstance(value, dict):
            if isinstance(value.get("reference"), str):
                assert value["reference"] in full_urls
            for v in value.values():
                check(v)
        elif isinstance(value, list):
            for v in value:
                check(v)

    check(bundle)
    clinical = {e["resource"]["resourceType"]: e["resource"] for e in bundle["entry"]}
    assert clinical["CarePlan"]["intent"] == "proposal"
    assert clinical["Task"]["restriction"]["period"]["end"].endswith("+01:00")
    provenance = [
        e["resource"] for e in bundle["entry"] if e["resource"]["resourceType"] == "Provenance"
    ]
    claim = next(p for p in provenance if p.get("extension"))
    assert "test-model:prompt-v1" in json.dumps(claim)
    assert "Observation/o#answer" in json.dumps(claim)


def test_template_exports_are_separate_from_fhir_approval(setup, monkeypatch):
    client, body, resources, _ = setup
    records.save("example", records.CaseRecord.model_validate(final(body, None)))
    monkeypatch.setattr(cases, "meetings", lambda: {"example": "p"})
    monkeypatch.setattr(
        cases, "record", lambda patient: cases.Bundle({"entry": [{"resource": resources[0]}]})
    )
    draft = {
        "created": "2026-10-17T10:00:00+00:00",
        "model": "test-template-model",
        "fields": {
            "Historie > Základní diagnóza": {
                "value": "Historie pro formulář",
                "sources": ["Condition/c"],
            }
        },
    }
    monkeypatch.setattr(export, "load_draft", lambda case_id: draft)
    # A cached template draft remains usable after confirmation without an LLM call.
    assert client.post("/api/cases/example/zaver/draft").status_code == 200
    sections, used = export.filled("example")
    assert list(sections) == ["HEADER", "BODY", "RESPONSE"]
    assert used == draft
    pdf = client.get("/api/cases/example/zaver.pdf")
    assert pdf.status_code == 200
    text = "".join(p.extract_text() for p in PdfReader(io.BytesIO(pdf.content)).pages)
    assert "Historie pro formulář" in text
    assert "Ke kontrole lékařem" in " ".join(text.split())
    assert "Doporučený postup" in text
    assert "AI souhrn" not in text
    assert "mCODE" not in text
    assert "Revize zprávy" not in text
    assert client.get("/api/cases/example/zaver.docx").status_code == 200
    assert client.get("/api/cases/example/zaver.fhir.json").status_code == 409


def test_approved_task_updates_do_not_rewrite_historical_report(setup):
    client, body, _, _ = setup
    snapshot = prepare(client, body)
    payload = final(body, snapshot["revision"])
    assert client.put("/api/cases/example/record", json=payload).status_code == 200
    before = client.get("/api/cases/example/zaver.fhir.json").content
    payload["tasks"][0]["done"] = True
    assert client.put("/api/cases/example/record", json=payload).status_code == 200
    assert client.get("/api/cases/example/zaver.fhir.json").content == before


def test_legacy_confirmation_is_not_silently_approved(setup):
    client, body, _, _ = setup
    records.save("example", records.CaseRecord.model_validate(final(body, None)))
    assert client.get("/api/cases/example/report").status_code == 409
    assert client.get("/api/cases/example/zaver.fhir.json").status_code == 409


def test_legacy_report_can_be_reviewed_without_resetting_the_decision(setup):
    client, body, _, _ = setup
    legacy = final(body, None)
    records.save("example", records.CaseRecord.model_validate(legacy))
    snapshot = prepare(client, legacy)
    changed = final(body, snapshot["revision"])
    changed["decision"]["plan"] = "Jiný postup"
    assert client.put("/api/cases/example/record", json=changed).status_code == 409
    unsigned = {**legacy, "decision": body["decision"]}
    assert client.put("/api/cases/example/record", json=unsigned).status_code == 409
    result = client.put("/api/cases/example/record", json=final(body, snapshot["revision"]))
    assert result.status_code == 200, result.text
    assert client.get("/api/cases/example/zaver.fhir.json").status_code == 200


def test_report_revision_cannot_escape_storage(setup):
    client, body, _, _ = setup
    result = client.put("/api/cases/example/record", json=final(body, "../../x"))
    assert result.status_code == 422
