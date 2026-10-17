"""Závěr zasedání MDT from the template: the AI drafts only the history, with checked sources; the
board, the question and the conclusion come from the record. LLM mocked."""

import io

from docx import Document
from pypdf import PdfReader

from mdt_backend.features import export, records
from mdt_backend.provenance import NOT_FOUND

PATIENT = {"resourceType": "Patient", "id": "P09", "name": [{"text": "Pacientka P09 (fiktivní)"}]}
RESOURCES = [PATIENT, {"resourceType": "Condition", "id": "P09-dg1"}]


def template():
    return export.parse_template(export.TEMPLATE.read_text(encoding="utf-8"))


def test_template_structure():
    s = template()
    assert list(s) == ["HEADER", "BODY", "RESPONSE"]
    paths = [f.path for f in export.leaves(s["BODY"])]
    assert "Historie > Staging > CT" in paths and "Otázka na MDT" in paths


def test_header_from_board_and_patient_never_invented():
    s = template()
    d = records.Decision(attendees=[{"name": "", "specialty": "Chirurgie"},
                                    {"name": "MUDr. R", "specialty": "Radiologie"},
                                    {"name": "", "specialty": "Radiační onkologie"}])  # fmt: skip
    d.confirmed_by = "Koordinátorka K"  # the rest of a complete decision doesn't matter here
    export.fill_header(s["HEADER"], PATIENT, d, "GIT komise")
    values = {f.label: f.value for f in export.leaves(s["HEADER"])}
    assert values["Jméno, příjmení pacienta"] == "Pacientka P09 (fiktivní)"
    assert values["Rodné číslo (pojišťovna) pacienta"] == NOT_FOUND  # not in the dataset
    assert values["III.chirurgická klinika"] == "přítomen/a"
    assert values["Klinika zobrazovacích metod"] == "MUDr. R"
    assert values["Ústav Patologie"] == "–"  # not on the board
    assert values["Další odbornosti"] == "Radiační onkologie"
    assert values["Koordinátor/ka onkologické péče"] == "Koordinátorka K"
    assert s["HEADER"][0].label == "GIT komise, multidisciplinární tým"


def test_history_draft_drops_unknown_sources_and_skips_the_question(monkeypatch):
    seen = {}

    def fake_llm(system, user, schema, name):
        seen["fields"] = schema["properties"]
        return {k: {"hodnota": "C18.7", "zdroje": ["Condition/P09-dg1", "Condition/NOPE"]}
                for k in schema["properties"]}  # fmt: skip

    monkeypatch.setattr(export.llm, "chat_json", fake_llm)
    fields = export.draft_history(RESOURCES)
    assert "Otázka na MDT" not in fields  # comes from the nomination, never the AI
    assert fields["Historie > Základní diagnóza"] == {"value": "C18.7", "sources": ["Condition/P09-dg1"]}  # fmt: skip
    assert len(seen["fields"]) == len(fields)


def test_pdf_and_docx_mark_ai_values_and_list_sources():
    s = template()
    for f in export.leaves(s["BODY"]):
        f.value, f.sources = "C18.7", ["Condition/P09-dg1"]
    draft = {"created": "2026-10-17T10:00:00+00:00", "model": "m", "fields": {}}
    pdf = PdfReader(io.BytesIO(export.to_pdf("P09", s, draft)))
    text = "".join(p.extract_text() for p in pdf.pages)
    assert "Závěr zasedání MDT" in text and "Zdroj: Condition/P09-dg1" in text
    docx = Document(io.BytesIO(export.to_docx("P09", s, draft)))
    runs = [r for p in docx.paragraphs for r in p.runs if r.text == "C18.7"]
    assert runs and all(r.font.color.rgb == export.RGBColor(0x1C, 0x5E, 0xBF) for r in runs)
