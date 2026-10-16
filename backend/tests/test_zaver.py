"""MDT conclusion PDF pipeline, offline (LLM mocked). Run: uv run pytest tests/test_zaver.py"""

from pypdf import PdfReader

from mdt_backend import zaver

RESOURCES = [
    {
        "resourceType": "Patient",
        "id": "P09",
        "gender": "female",
        "birthDate": "1960",
        "name": [{"text": "Pacientka P09 (fiktivní)"}],
    },
    {"resourceType": "Condition", "id": "P09-dg1"},
]


def test_template_structure():
    s = zaver.parse_template(zaver.TEMPLATE.read_text(encoding="utf-8"))
    assert list(s) == ["HEADER", "BODY", "RESPONSE"]
    paths = [f.path for f in zaver.leaves(s["BODY"])]
    assert "Historie > Staging > CT" in paths
    assert "Poslední zobrazovací vyšetření > CT" in paths
    assert "Otázka na MDT" in paths
    assert not any(f.group for f in s["RESPONSE"] if f)


def test_header_is_dummy_and_complete():
    s = zaver.parse_template(zaver.TEMPLATE.read_text(encoding="utf-8"))
    zaver.fill_header(s["HEADER"], RESOURCES[0])
    values = {f.label: f.value for f in zaver.leaves(s["HEADER"])}
    assert values["Jméno, příjmení pacienta"] == "Pacientka P09 (fiktivní)"
    assert values["Rodné číslo (pojišťovna) pacienta"].startswith("60")
    assert "?" not in values.values()


def test_pipeline_with_mocked_llm(tmp_path, monkeypatch):
    calls = []

    def fake_chat_json(system, user, schema, name="odpoved"):
        calls.append(name)
        if name == "historie":
            return {
                k: {
                    "hodnota": "C50.4; pT2 pN1a",
                    "zdroje": ["Condition/P09-dg1", "Observation/made-up"],
                }
                for k in schema["properties"]
            }
        assert "C50.4" in user  # the recommendation sees the filled BODY
        return {"doporuceni": ["Paliativní systémová léčba"], "zduvodneni": "Progrese v játrech."}

    monkeypatch.setattr(zaver.fhir, "get_patient_record", lambda pid: RESOURCES)
    monkeypatch.setattr(zaver.llm, "chat_json", fake_chat_json)
    out = zaver.create_zaver("P09", tmp_path / "P09.pdf")

    assert calls == ["historie", "zaver_mdt"]
    md = out.with_suffix(".md").read_text(encoding="utf-8")
    assert "[Zdroj: Condition/P09-dg1]" in md  # hallucinated reference dropped
    assert "made-up" not in md
    assert "- Paliativní systémová léčba" in md
    text = "".join(p.extract_text() for p in PdfReader(out).pages)
    assert "Závěr MDT" in text and "Paliativní systémová léčba" in text
    assert "AI návrh" in text
