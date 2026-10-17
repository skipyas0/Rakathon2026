"""FHIR bundles → Case, and the case endpoints over a fake FHIR server holding the dataset.
Skipped when the dataset folder isn't present (it's not in git)."""

import datetime as dt

import pytest
from conftest import BUNDLES, needs_dataset
from fastapi.testclient import TestClient

from mdt_backend import knowledge
from mdt_backend.app import app
from mdt_backend.bundles import Bundle
from mdt_backend.from_fhir import build_case
from mdt_backend.knowledge import guideline_source
from mdt_backend.provenance import Statement

pytestmark = needs_dataset


@pytest.mark.parametrize("case_id", BUNDLES)
def test_every_bundle_builds_a_valid_case(case_id):
    c = build_case(case_id, Bundle(BUNDLES[case_id]))
    assert c.question and c.question.origin == "human"  # the nomination's question, never AI
    assert c.summary and c.timeline and c.sections
    assert all(s.origin == "record" for s in c.summary)
    assert all(f.statement.origin == "ai" for f in c.red_flags)  # rule output must be confirmed
    assert all(len(t.points) > 1 for t in c.trends)


def test_p01_red_flags_match_the_data():
    if "p01" not in BUNDLES:
        pytest.skip("P01 not in dataset")
    flags = " ".join(f.statement.text for f in build_case("p01", Bundle(BUNDLES["p01"])).red_flags)
    assert "ECOG dle lékaře 1" in flags and "ECOG 2" in flags
    assert "Hemoglobin" in flags and "únava 8/10" in flags
    assert "CA 15-3 roste" in flags
    assert "kyčel" in flags  # new symptom from the questionnaire


def test_mdt_date_and_adverse_event():
    if "p05" not in BUNDLES:
        pytest.skip("P05 not in dataset")
    c = build_case("p05", Bundle(BUNDLES["p05"]))
    assert c.mdt_date == dt.date(2026, 10, 21)  # Task.restriction, as in the dataset README
    items = [s.text for sec in c.sections for s in sec.items]
    assert any(t.startswith("Nežádoucí účinek: ") and "PARP" in t for t in items)
    assert not any(t.startswith("Komorbidita: ") and "PARP" in t for t in items)


def test_guidelines_and_trials_load():
    passages, studies = knowledge.guidelines(), knowledge.trials()
    assert len(passages) == 42 and len(studies) == 6
    s = knowledge.guideline_source("KRC-1.1")
    assert s.reference == "guideline:KRC-1.1" and s.excerpt.startswith("U každého metastatického")
    assert "\n" not in passages["PRS-2.2"]["text"] and "elacestrant" in passages["PRS-2.2"]["text"]
    t = knowledge.trial_source("RKT-01", "V2")
    assert t.reference == "trial:RKT-01#V2" and "mozkové metastázy" in t.excerpt


def test_source_endpoint_returns_full_text(fake_fhir):
    c = TestClient(app)
    case_id = next(iter(BUNDLES))
    ref = build_case(case_id, Bundle(BUNDLES[case_id])).timeline[-1].statement.sources[0].reference
    r = c.get(f"/api/sources/{ref.split('#')[0]}")
    assert r.status_code == 200 and r.json()["text"]
    assert c.get("/api/sources/Patient/nope").status_code == 404


def test_case_ids_are_meetings(fake_fhir):
    from mdt_backend.features.cases import meetings

    ids = list(meetings())
    assert len(ids) == len(BUNDLES)  # one open meeting per patient in the dataset
    assert all(i[:3] in BUNDLES and dt.date.fromisoformat(i[4:]) for i in ids), ids


def test_previous_board_from_care_team():
    if "p03" not in BUNDLES:
        pytest.skip("P03 not in dataset")
    board = build_case("p03", Bundle(BUNDLES["p03"])).previous_board
    assert [m.name for m in board if m.chair] == ["LEK-P03-06"]  # "předseda GIT komise"
    assert any(m.role == "patolog" and m.name == "" for m in board)  # role without a member


def test_history_has_previous_mdt_records(fake_fhir):
    if "p03" not in BUNDLES:
        pytest.skip("P03 not in dataset")
    h = TestClient(app).get("/api/cases/p03-2026-10-21/history").json()
    assert [d["title"] for d in h["documents"]][-1] == "Rozhodnutí o léčbě"
    assert h["documents"][0]["sections"][0]["title"] == "Projednaná otázka"


def test_recommendation_examples_cite_real_passages(tmp_path, monkeypatch, fake_fhir):
    from mdt_backend import agent
    from mdt_backend.features.cases import meetings

    monkeypatch.setattr(agent, "OUT_DIR", tmp_path)  # no AI briefings
    client = TestClient(app)
    for case_id in meetings():
        r = client.get(f"/api/cases/{case_id}/recommendation").json()
        assert r["statement"]["model"] == "ukázka" and r["statement"]["sources"], case_id


def test_recommendation_is_the_agents_first_option(tmp_path, monkeypatch, fake_fhir):
    from mdt_backend import agent

    monkeypatch.setattr(agent, "OUT_DIR", tmp_path)
    case = build_case("p03", Bundle(BUNDLES["p03"]))
    option = Statement(
        text="Resekce.", origin="ai", model="m", sources=[guideline_source("KRC-2.3")]
    )
    case.decision_support.options = [option]
    case.decision_support.intent = "curative"
    (tmp_path / "p03.json").write_text(case.model_dump_json(), encoding="utf-8")
    r = TestClient(app).get("/api/cases/p03-2026-10-21/recommendation").json()
    assert r == {"intent": "curative", "statement": option.model_dump(mode="json")}
