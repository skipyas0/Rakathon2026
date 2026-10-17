from fastapi.testclient import TestClient

from mdt_backend.app import app
from mdt_backend.features import compliance
from mdt_backend.provenance import Source, Statement

client = TestClient(app)


def cited_recommendation():
    return {
        "intent": "palliative",
        "statement": Statement(
            text="Pokračovat v anti-HER2 léčbě.",
            origin="ai",
            model="test-model",
            sources=[
                Source(
                    reference="guideline:PRS-3.3",
                    title="Doporučený postup",
                    excerpt="Pokračovat v léčbě.",
                )
            ],
        ),
    }


def test_assessment_compares_plan_and_returns_original_guideline_source(monkeypatch):
    captured = {}
    monkeypatch.setattr(
        compliance.recommendation, "recommendation", lambda case_id: cited_recommendation()
    )
    monkeypatch.setattr(
        compliance,
        "guidelines",
        lambda: {"PRS-3.3": {"title": "Systémová léčba", "text": "Pokračovat v léčbě."}},
    )
    monkeypatch.setattr(
        compliance,
        "guideline_source",
        lambda passage_id: Source(
            reference=f"guideline:{passage_id}",
            title="Původní doporučený postup",
            excerpt="Pokračovat v léčbě.",
        ),
    )

    def fake_llm(system, user, schema, name):
        captured.update(system=system, user=user, schema=schema, name=name)
        return {
            "status": "deviation",
            "reason": "Zvolená resekce se liší od doporučené pokračující léčby.",
            "guideline_ids": ["PRS-3.3"],
        }

    monkeypatch.setattr(compliance, "chat_json", fake_llm)
    response = client.post(
        "/api/cases/example/guideline-assessment",
        json={
            "intents": ["curative", "supportive"],
            "plan": "Resekce",
            "rationale": "Komise ji preferuje.",
        },
    )

    assert response.status_code == 200
    result = response.json()["assessment"]
    assert result["status"] == "deviation"
    assert result["recommendation_sources"][0]["reference"] == "guideline:PRS-3.3"
    assert "Resekce" in captured["user"] and "Komise ji preferuje." in captured["user"]
    assert "curative, supportive" in captured["user"]
    assert result["compared_intents"] == ["curative", "supportive"]
    assert "Pokračovat v léčbě." in captured["user"]
    assert captured["name"] == "guideline_compliance"
    assert result["statement"]["sources"][0]["reference"] == "guideline:PRS-3.3"


def test_assessment_rejects_uncited_or_unknown_guideline_references(monkeypatch):
    monkeypatch.setattr(
        compliance.recommendation, "recommendation", lambda case_id: cited_recommendation()
    )
    monkeypatch.setattr(
        compliance,
        "guidelines",
        lambda: {"PRS-3.3": {"title": "Systémová léčba", "text": "Pokračovat v léčbě."}},
    )
    monkeypatch.setattr(
        compliance, "guideline_source", lambda _: Source(reference="guideline:PRS-3.3")
    )
    monkeypatch.setattr(
        compliance,
        "chat_json",
        lambda *args, **kwargs: {
            "status": "compliant",
            "reason": "V pořádku.",
            "guideline_ids": ["OBC-1.1"],
        },
    )

    response = client.post(
        "/api/cases/example/guideline-assessment",
        json={"intents": ["palliative"], "plan": "Léčba", "rationale": "Důvod"},
    )
    assert response.status_code == 502
