"""MDT agent pipeline offline: the LLM is mocked, the record comes from a fake FHIR server holding
the dataset. Skipped when the dataset folder isn't present (it's not in git)."""

import pytest
from conftest import BUNDLES
from fastapi.testclient import TestClient

from mdt_backend import agent
from mdt_backend.app import app
from mdt_backend.features import cases
from mdt_backend.knowledge import trials
from mdt_backend.provenance import NOT_FOUND

pytestmark = pytest.mark.skipif("p01" not in BUNDLES, reason="no dataset")

HB = {"ref": "Observation/P01-lab06-hb_f", "excerpt": "104"}
BAD_REF = {"ref": "Observation/NOPE", "excerpt": "x"}
INVENTED = {"ref": "DiagnosticReport/P01-img06", "excerpt": "bez nálezu, vše v pořádku"}


def fake_llm(system, user, schema, name):
    if name == "trials":
        return {
            "trials": [
                {
                    "id": tid,
                    "diagnosis": {"status": "unknown", "reason": NOT_FOUND, "refs": []},
                    "criteria": [
                        {"id": c["id"], "status": "unknown", "reason": NOT_FOUND, "refs": []}
                        for c in t["zarazeni"] + t["vyrazeni"]
                    ],
                }
                for tid, t in trials().items()
            ]
        }
    if name == "symptoms":
        return {
            "symptoms": [
                {"item": "nove-obtize", "concept": "bone_pain", "excerpt": "kyčel", "new": True},
                {"item": "neexistuje", "concept": "fever", "excerpt": "x", "new": True},
            ]
        }
    if name == "cacc":
        return {
            "prerequisites": [
                {
                    "id": "C1",
                    "item": "ESR1",
                    "why": "linie",
                    "area": "oncology",
                    "guideline_ids": ["PRS-1.3"],
                },
                {
                    "id": "C2",
                    "item": "Staging ≤ 6 týdnů",
                    "why": "aktuálnost",
                    "area": "radiology",
                    "guideline_ids": ["OBC-1.2"],
                },
            ],
            "expected_symptoms": [
                {"symptom": "bolest kostí", "basis": "kosti", "guideline_ids": []}
            ],
        }
    if name == "findings":
        return {
            "checklist": [
                {"id": "C1", "status": "chybi", "note": "", "refs": []},
                {"id": "C2", "status": "splneno", "note": "", "refs": [HB]},
            ],
            "findings": [
                {
                    "severity": "RED",
                    "kind": "chybejici_udaj",
                    "area": "oncology",
                    "text": "Chybí ESR1.",
                    "refs": [HB],
                    "guideline_ids": ["PRS-1.3", "KRC-1.1"],
                },
                {
                    "severity": "YELLOW",
                    "kind": "rozpor",
                    "area": "radiology",
                    "text": "Nedoložené tvrzení.",
                    "refs": [BAD_REF],
                    "guideline_ids": [],
                },
                {
                    "severity": "YELLOW",
                    "kind": "chybejici_udaj",
                    "area": "oncology",
                    "text": "Protokol studie",
                    "refs": [],
                    "guideline_ids": [],
                },
            ],
        }
    if name in ("summary_text", "opinion"):  # executive summary / specialist opinion as free text
        return {"text": "Hb klesá na 104 g/l [Observation/P01-lab06-hb_f]."}
    if name == "summary_extract":
        assert "Hb klesá" in user and "Chybí ESR1." in user  # known flags are passed on
        return {
            "points": [
                {"text": "Hb 104 g/l (2026-10-06).", "refs": [HB], "guideline_ids": []},
                {"text": "Bez zdroje.", "refs": [BAD_REF], "guideline_ids": []},
            ],
            "red_flags": [
                {"severity": "medium", "text": "Pokles Hb.", "refs": [HB], "guideline_ids": []},
                {"severity": "high", "text": "Chybí ESR1.", "refs": [HB], "guideline_ids": []},
            ],
            "timeline": [
                {"date": "2026-10-06", "kind": "systemic", "text": "Anémie.", "refs": [HB]},
                {"date": "2026-13-01", "kind": "systemic", "text": "Špatné datum.", "refs": [HB]},
            ],
        }
    if name == "indicators":
        assert "[QuestionnaireResponse/P01-prom02#unava]" in user
        return {
            "indicators": [
                {
                    "id": "HB",
                    "label": "Hemoglobin",
                    "unit": "g/l",
                    "why": "anémie",
                    "refs": [f"Observation/P01-lab0{i}-hb_f" for i in (1, 5, 6)] + ["X/1"],
                },
                {
                    "id": "unava",
                    "label": "Únava",
                    "unit": "",
                    "why": "",
                    "refs": [f"QuestionnaireResponse/P01-prom0{i}#unava" for i in (1, 2)],
                },
                {"id": "one", "label": "Jen jedno", "unit": "", "why": "", "refs": ["X/2"]},
            ]
        }
    if name == "preference":
        return {
            "stated": True,
            "points": [
                {
                    "text": "Pacientka si nepřeje chemoterapii.",
                    "refs": [
                        {
                            "ref": "ServiceRequest/P01-zad01",
                            "excerpt": "Nepřeje si znovu chemoterapii",
                        }
                    ],
                }
            ],
        }
    if name == "context":
        return {"refs": ["[Observation/P01-lab06-hb_f]", "Observation/NOPE"], "reason": ""}
    if name == "verdict":
        assert "[Observation/P01-lab06-hb_f]" in user and "[Observation/NOPE]" not in user
        assert user.startswith("Stanovisko:\nHb klesá")  # extracted from the free-text opinion
        return {
            "points": [{"text": "Hb 104 g/l.", "refs": [HB, INVENTED], "guideline_ids": []}],
            "verdict": {"text": "Bez námitek.", "refs": [], "guideline_ids": ["PRS-2.2"]},
            "missing": ["PET/CT"],
        }
    assert name == "recommend"
    assert "Pacientka si nepřeje chemoterapii. [ServiceRequest/P01-zad01]" in user
    return {
        "options": [
            {
                "rank": 2,
                "intent": "supportive",
                "text": "Druhá.",
                "refs": [],
                "guideline_ids": ["PRS-2.3"],
            },
            {
                "rank": 1,
                "intent": "palliative",
                "text": "První.",
                "refs": [HB],
                "guideline_ids": ["PRS-2.2"],
            },
            {
                "rank": 3,
                "intent": "curative",
                "text": "Bez pasáže.",
                "refs": [HB],
                "guideline_ids": ["XYZ-9.9"],
            },
        ],
        "preference": {
            "stated": True,
            "text": "Nechce chemoterapii.",
            "refs": [
                {"ref": "ServiceRequest/P01-zad01", "excerpt": "Nepřeje si znovu chemoterapii"}
            ],
            "matches_option": "1",
        },
        "questions": [{"text": "Doplnit ESR1?", "refs": [], "guideline_ids": ["PRS-1.3"]}],
    }


@pytest.fixture
def result(monkeypatch, fake_fhir):
    monkeypatch.setattr(agent, "chat_json", fake_llm)
    return agent.run("P01")


def test_output_is_a_valid_case_with_ai_statements(result):
    case, trace = result
    assert case.id == "p01" and case.patient == "Patient/P01"
    ai = [f for f in case.red_flags if f.statement.model == agent.model_tag()]
    # YELLOW finding had no valid source → dropped; then the summary's extra flag
    assert [(f.severity, f.statement.text) for f in ai] == [
        ("high", "Chybí ESR1."),
        ("medium", "Pokles Hb."),
    ]
    assert {s.reference for s in ai[0].statement.sources} == {
        "Observation/P01-lab06-hb_f",
        "guideline:PRS-1.3",
    }
    assert set(trace["steps"]) == {
        "cacc",
        "findings",
        "recommend",
        "summary_text",
        "summary_extract",
        "indicators",
        "preference",
        "symptoms",
        "trials",
        *(f"{k}:{s}" for k in ("context", "opinion", "verdict") for s in agent.SPECIALISTS),
    }


def test_symptom_classifier_output_is_checked(result):
    case, trace = result
    # the invented item is dropped; the classified hip pain still drives the alarm rule
    assert [s["concept"] for s in trace["symptoms"]] == ["bone_pain"]
    assert any("kyčel" in f.statement.text for f in case.red_flags)


def test_screening_feeds_all_catalogue_criteria_into_case(result):
    case, _ = result
    assert {t.trial for t in case.decision_support.trials} == set(trials())
    assert sum(len(t.criteria) for t in case.decision_support.trials) == 51
    assert all(t.verdict == "missing_data" for t in case.decision_support.trials)
    for trial in case.decision_support.trials:
        assert all(s.text.endswith(NOT_FOUND) for s in trial.criteria)
        assert all(
            s.sources[0].reference.startswith(f"trial:{trial.trial}#") for s in trial.criteria
        )


def test_citations_are_checked(result):
    case, trace = result
    reasons = {
        (r.get("ref") or r.get("guideline"), r["reason"]) for r in trace["rejected_citations"]
    }
    assert ("KRC-1.1", "not allowed") in reasons  # colorectal passage for a breast patient
    assert ("Observation/NOPE", "not in record") in reasons
    assert ("DiagnosticReport/P01-img06", "not verbatim") in reasons
    radiology = next(s for s in case.sections if s.id == "radiology")
    point = next(s for s in radiology.items if s.text == "Hb 104 g/l.")
    invented = next(s for s in point.sources if s.reference == "DiagnosticReport/P01-img06")
    assert invented.excerpt is None  # pointer kept, the made-up quote is not shown


def test_missing_data_uses_required_wording(result):
    case, _ = result
    gaps = [s for sec in case.sections for s in sec.items if s.text.endswith(NOT_FOUND)]
    texts = {s.text for s in gaps}
    assert f"ESR1: {NOT_FOUND}" in texts and f"PET/CT: {NOT_FOUND}" in texts
    assert f"Protokol studie: {NOT_FOUND}" in texts  # unsourced missing-data finding kept as a gap
    assert all(not s.sources and s.origin == "ai" for s in gaps)


def test_options_follow_guidelines_and_mention_preference(result):
    case, _ = result
    opts = case.decision_support.options
    assert [o.text.split(" ")[0] for o in opts] == ["První.", "Druhá."]  # by rank, max 2
    assert case.decision_support.intent == "palliative"  # the first option's
    assert all(any(s.reference.startswith("guideline:") for s in o.sources) for o in opts)
    assert "Preference pacienta: Nechce chemoterapii." in opts[0].text
    assert any(s.reference == "ServiceRequest/P01-zad01" for s in opts[0].sources)
    assert "Preference" not in opts[1].text
    assert [q.text for q in case.decision_support.questions] == ["Doplnit ESR1?"]


def test_compare_runs(result):
    case, _ = result
    cmp = agent.compare(case, case)
    assert cmp["first_option_passages_jaccard"] == 1.0
    assert cmp["option_counts"] == [2, 2]


def test_executive_summary_feeds_summary_flags_and_timeline(result):
    case, trace = result
    assert case.summary[0].text == "Hb 104 g/l (2026-10-06)." and case.summary[0].origin == "ai"
    assert case.summary[1].origin == "record"  # the record facts follow the AI points
    ai_flags = [f.statement.text for f in case.red_flags if f.statement.model]
    assert ai_flags.count("Chybí ESR1.") == 1 and "Pokles Hb." in ai_flags  # no duplicates
    anaemia = [e for e in case.timeline if e.statement.text == "Anémie."]
    assert len(anaemia) == 1 and anaemia[0].statement.origin == "ai"
    assert [e.date for e in case.timeline] == sorted(e.date for e in case.timeline)
    assert any(r.get("reason") == "date" for r in trace["rejected_citations"])


def test_indicator_values_come_from_the_record(result):
    case, trace = result
    hb, fatigue = case.trends[:2]
    assert [p.value for p in hb.points] == [128, 116, 104] and hb.unit == "g/l"
    assert hb.ref_low is not None  # reference range from the record, not the model
    assert [p.source.reference for p in fatigue.points] == [
        "QuestionnaireResponse/P01-prom01#unava",
        "QuestionnaireResponse/P01-prom02#unava",
    ]
    assert fatigue.unit == "/10" and fatigue.axis == (0, 10)
    assert not any(t.label == "Jen jedno" for t in case.trends)  # < 2 points
    ids = [t.id for t in case.trends]
    assert len(ids) == len(set(ids))
    assert not any(t.id == "proms-unava" for t in case.trends)  # covered by the AI series
    assert {"ref": "X/1", "reason": "no value", "where": "indicators.0"} in trace[
        "rejected_citations"
    ]


def test_preference_leads_patient_section(result):
    case, _ = result
    patient = next(s for s in case.sections if s.id == "patient")
    assert patient.items[0].text == "Pacientka si nepřeje chemoterapii."
    assert patient.items[0].sources[0].reference == "ServiceRequest/P01-zad01"
    assert case.preference == patient.items[: len(case.preference)]  # also on its own for Pacient


def test_pipeline_output_reaches_the_meeting_journey(result, tmp_path, monkeypatch):
    case, trace = result
    monkeypatch.setattr(agent, "OUT_DIR", tmp_path)
    agent.save(case, trace, out_dir=tmp_path)
    meeting = next(mid for mid, patient in cases.meetings().items() if patient == case.id)
    client = TestClient(app)

    response = client.get(f"/api/cases/{meeting}")
    assert response.status_code == 200
    served = response.json()
    assert served == {**case.model_dump(mode="json"), "id": meeting}
    assert len(served["decision_support"]["trials"]) == 6
    assert served["preference"] and served["previous_board"]
    assert any(f["statement"]["model"].startswith("pravidla-v2:") for f in served["red_flags"])

    recommendation = client.get(f"/api/cases/{meeting}/recommendation").json()
    assert recommendation["intent"] == "palliative"
    assert recommendation["statement"] == case.decision_support.options[0].model_dump(mode="json")
    assert client.get(f"/api/cases/{meeting}/ai").json() == {"status": "done"}
