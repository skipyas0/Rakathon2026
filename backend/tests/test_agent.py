"""MDT agent pipeline offline: the LLM is mocked, the record comes from the dataset bundle on disk.
Skipped when the dataset folder isn't present (it's not in git)."""

import pytest

from mdt_backend import agent
from mdt_backend.bundles import bundle_paths
from mdt_backend.provenance import NOT_FOUND

pytestmark = pytest.mark.skipif("p01" not in bundle_paths(), reason="no dataset")

HB = {"ref": "Observation/P01-lab06-hb_f", "excerpt": "104"}
BAD_REF = {"ref": "Observation/NOPE", "excerpt": "x"}
INVENTED = {"ref": "DiagnosticReport/P01-img06", "excerpt": "bez nálezu, vše v pořádku"}


def fake_llm(system, user, schema, name):
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
    if name == "context":
        return {"refs": ["[Observation/P01-lab06-hb_f]", "Observation/NOPE"], "reason": ""}
    if name == "verdict":
        assert "[Observation/P01-lab06-hb_f]" in user and "[Observation/NOPE]" not in user
        return {
            "points": [{"text": "Hb 104 g/l.", "refs": [HB, INVENTED], "guideline_ids": []}],
            "verdict": {"text": "Bez námitek.", "refs": [], "guideline_ids": ["PRS-2.2"]},
            "missing": ["PET/CT"],
        }
    assert name == "recommend"
    return {
        "options": [
            {"rank": 2, "text": "Druhá.", "refs": [], "guideline_ids": ["PRS-2.3"]},
            {"rank": 1, "text": "První.", "refs": [HB], "guideline_ids": ["PRS-2.2"]},
            {"rank": 3, "text": "Bez pasáže.", "refs": [HB], "guideline_ids": ["XYZ-9.9"]},
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
def result(monkeypatch):
    monkeypatch.setattr(agent, "chat_json", fake_llm)
    return agent.run("P01", source="file")


def test_output_is_a_valid_case_with_ai_statements(result):
    case, trace = result
    assert case.id == "p01" and case.patient == "Patient/P01"
    ai = [f for f in case.red_flags if f.statement.model == agent.model_tag()]
    assert [f.severity for f in ai] == ["high"]  # YELLOW finding had no valid source → dropped
    assert {s.reference for s in ai[0].statement.sources} == {
        "Observation/P01-lab06-hb_f",
        "guideline:PRS-1.3",
    }
    assert set(trace["steps"]) == {
        "cacc",
        "findings",
        "recommend",
        *(f"{k}:{s}" for k in ("context", "verdict") for s in agent.SPECIALISTS),
    }


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
