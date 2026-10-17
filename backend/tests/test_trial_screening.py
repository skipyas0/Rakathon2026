"""Preliminary screening semantics and citation gates, without a model or dataset."""

import datetime as dt
from types import SimpleNamespace

import pytest

from mdt_backend import agent, knowledge
from mdt_backend.bundles import Bundle
from mdt_backend.provenance import NOT_FOUND

CATALOG = {
    "TEST": {
        "id": "TEST",
        "akronym": "TEST",
        "diagnoza": "Karcinom prsu",
        "zarazeni": [{"id": "Z1", "text": "ECOG 0–1"}, {"id": "Z2", "text": "LVEF ≥ 50 %"}],
        "vyrazeni": [{"id": "V1", "text": "Předchozí PARP inhibitor"}],
    }
}
EVIDENCE = {"ref": "Observation/ecog", "excerpt": "1"}


@pytest.fixture
def screening(monkeypatch):
    monkeypatch.setattr(agent, "trials", lambda: CATALOG)
    monkeypatch.setattr(knowledge, "trials", lambda: CATALOG)
    bundle = Bundle(
        {
            "entry": [
                {
                    "resource": {
                        "resourceType": "Observation",
                        "id": "ecog",
                        "code": {"text": "ECOG"},
                        "valueInteger": 1,
                    }
                },
                {
                    "resource": {
                        "resourceType": "QuestionnaireResponse",
                        "id": "prom",
                        "item": [
                            {"linkId": "pain", "text": "Bolest", "answer": [{"valueInteger": 7}]},
                            {"linkId": "fatigue", "text": "Únava", "answer": [{"valueInteger": 2}]},
                        ],
                    }
                },
            ]
        }
    )

    def run(statuses, refs=None, mutate=None):
        output = {
            "trials": [
                {
                    "id": "TEST",
                    "diagnosis": {"status": "unknown", "reason": NOT_FOUND, "refs": []},
                    "criteria": [
                        {
                            "id": cid,
                            "status": status,
                            "reason": "Doložený nález.",
                            "refs": [EVIDENCE] if refs is None else refs,
                        }
                        for cid, status in zip(("Z1", "Z2", "V1"), statuses, strict=True)
                    ],
                }
            ]
        }
        if mutate:
            mutate(output)
        monkeypatch.setattr(agent, "chat_json", lambda *a, **kw: output)
        cite = agent.Citations(SimpleNamespace(bundle=bundle), {})
        trace = {"steps": {}}
        matches = agent.screen_trials("record", dt.date(2026, 10, 21), cite, trace)
        return matches[0], cite, trace

    return run


@pytest.mark.parametrize(
    ("statuses", "verdict"),
    [
        (("matched", "unknown", "unknown"), "eligible"),
        (("matched", "not_matched", "not_matched"), "eligible"),
        (("matched", "matched", "matched"), "ineligible"),
        (("unknown", "unknown", "matched"), "ineligible"),
        (("unknown", "unknown", "not_matched"), "missing_data"),
        (("not_matched", "not_matched", "not_matched"), "missing_data"),
    ],
)
def test_prefilter_priority(screening, statuses, verdict):
    match, _, trace = screening(statuses)
    assert match.verdict == verdict
    assert len(match.criteria) == 4
    assert set(trace["steps"]) == {"trials"}
    for cid, statement in zip(("Z1", "Z2", "V1"), match.criteria[1:], strict=True):
        assert statement.origin == "ai" and statement.model == agent.model_tag()
        assert {s.reference for s in statement.sources} == {
            f"trial:TEST#{cid}",
            "Observation/ecog",
        }


@pytest.mark.parametrize(
    "refs",
    [
        [],
        [{"ref": "Observation/nope", "excerpt": "1"}],
        [{"ref": "Observation/ecog", "excerpt": "invented quote"}],
        [{"ref": "Observation/ecog", "excerpt": ""}],
        [{"ref": "Observation/ecog", "excerpt": "eco"}],
        [{"ref": "Observation/ecog#fake", "excerpt": "1"}],
        [{"ref": "QuestionnaireResponse/prom#fake", "excerpt": "7"}],
        [{"ref": "QuestionnaireResponse/prom#fatigue", "excerpt": "7"}],
        [EVIDENCE, {"ref": "Observation/nope", "excerpt": "1"}],
    ],
)
def test_unsupported_outcomes_become_unknown(screening, refs):
    match, cite, _ = screening(("matched", "matched", "matched"), refs)
    assert match.verdict == "missing_data"
    assert all(s.text.endswith(NOT_FOUND) for s in match.criteria)
    assert all("Doložený nález" not in s.text for s in match.criteria)
    assert cite.rejected


def test_questionnaire_item_evidence(screening):
    match, cite, _ = screening(
        ("matched", "unknown", "not_matched"),
        [{"ref": "QuestionnaireResponse/prom#fatigue", "excerpt": "2"}],
    )
    assert match.verdict == "eligible"
    assert not cite.rejected
    assert match.criteria[1].sources[1].reference == "QuestionnaireResponse/prom#fatigue"


@pytest.mark.parametrize(
    ("status", "refs", "verdict"),
    [
        ("not_matched", [EVIDENCE], "ineligible"),
        ("matched", [EVIDENCE], "eligible"),
        ("unknown", [], "eligible"),
        ("not_matched", [], "eligible"),
        ("not_matched", [{"ref": "Observation/nope", "excerpt": "1"}], "eligible"),
    ],
)
def test_cancer_type_mismatch_takes_precedence_only_with_evidence(screening, status, refs, verdict):
    def mutate(output):
        output["trials"][0]["diagnosis"] = {
            "status": status,
            "reason": "Jiný typ nádoru.",
            "refs": refs,
        }

    match, _, _ = screening(("matched", "unknown", "not_matched"), mutate=mutate)
    assert match.verdict == verdict
    assert match.criteria[0].sources[0].reference == "trial:TEST#diagnosis"


@pytest.mark.parametrize("kind", ["study", "criterion", "duplicate"])
def test_incomplete_or_invalid_output_fails_explicitly(screening, kind):
    def mutate(output):
        if kind == "study":
            output["trials"][0]["id"] = "invented"
        elif kind == "criterion":
            output["trials"][0]["criteria"].pop()
        else:
            output["trials"].append(output["trials"][0])

    with pytest.raises(ValueError, match="Study screening returned"):
        screening(("matched", "matched", "not_matched"), mutate=mutate)


def test_missing_catalogue_fails_explicitly(monkeypatch):
    monkeypatch.setattr(agent, "trials", dict)
    with pytest.raises(ValueError, match="non-empty study catalogue"):
        agent.screen_trials("", None, None, {})
