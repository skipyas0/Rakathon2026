"""FHIR bundles → Case. Skipped when the dataset folder isn't present (it's not in git)."""

import datetime as dt

import pytest
from fastapi.testclient import TestClient

from mdt_backend import knowledge
from mdt_backend.app import app
from mdt_backend.bundles import bundle_paths, load
from mdt_backend.from_fhir import build_case

BUNDLES = bundle_paths()
pytestmark = pytest.mark.skipif(not BUNDLES, reason="no dataset in settings.dataset_dir")


@pytest.mark.parametrize("case_id", BUNDLES)
def test_every_bundle_builds_a_valid_case(case_id):
    c = build_case(case_id, load(BUNDLES[case_id]))
    assert c.question and c.question.origin == "human"  # the nomination's question, never AI
    assert c.summary and c.timeline and c.sections
    assert all(s.origin == "record" for s in c.summary)
    assert all(f.statement.origin == "ai" for f in c.red_flags)  # rule output must be confirmed
    assert all(len(t.points) > 1 for t in c.trends)


def test_p01_red_flags_match_the_data():
    if "p01" not in BUNDLES:
        pytest.skip("P01 not in dataset")
    flags = " ".join(f.statement.text for f in build_case("p01", load(BUNDLES["p01"])).red_flags)
    assert "ECOG dle lékaře 1" in flags and "ECOG 2" in flags
    assert "Hemoglobin" in flags and "únava 8/10" in flags
    assert "CA 15-3 roste" in flags
    assert "kyčel" in flags  # new symptom from the questionnaire


def test_mdt_date_and_adverse_event():
    if "p05" not in BUNDLES:
        pytest.skip("P05 not in dataset")
    c = build_case("p05", load(BUNDLES["p05"]))
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


def test_source_endpoint_returns_full_text():
    c = TestClient(app)
    case_id = next(iter(BUNDLES))
    ref = build_case(case_id, load(BUNDLES[case_id])).timeline[-1].statement.sources[0].reference
    r = c.get(f"/api/sources/{ref.split('#')[0]}")
    assert r.status_code == 200 and r.json()["text"]
    assert c.get("/api/sources/Patient/nope").status_code == 404


def test_case_ids_are_meetings():
    from mdt_backend.features.cases import meetings

    ids = list(meetings())
    assert len(ids) == len(BUNDLES)  # one open meeting per patient in the dataset
    assert all(i[:3] in BUNDLES and dt.date.fromisoformat(i[4:]) for i in ids), ids
