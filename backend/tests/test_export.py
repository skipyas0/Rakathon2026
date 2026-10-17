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
    d = records.Decision(attendees=[{"name": "MUDr. S", "specialty": "Chirurgie"},
                                    {"name": "MUDr. R", "specialty": "Radiologie"},
                                    {"name": "", "specialty": "Radiační onkologie"}])  # fmt: skip
    d.confirmed_by = "Koordinátor/ka"  # the rest of a complete decision doesn't matter here
    export.fill_header(s["HEADER"], PATIENT, d, "GIT komise")
    values = {f.label: f.value for f in export.leaves(s["HEADER"])}
    assert values["Jméno, příjmení pacienta"] == "Pacientka P09 (fiktivní)"
    assert values["Rodné číslo (pojišťovna) pacienta"] == NOT_FOUND  # not in the dataset
    assert values["III.chirurgická klinika"] == "Jméno, Chirurgie"
    assert values["Klinika zobrazovacích metod"] == "Jméno, Radiologie"
    assert values["Ústav Patologie"] == "–"  # not on the board
    assert "Další odbornosti" not in values
    assert values["Koordinátor/ka onkologické péče"] == "přítomen/a"
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


def _stanovisko(**kw):
    from mdt_backend.provenance import Source, Statement

    base = {"text": "Nadledvinu nutno ověřit (biopsie / MR).", "origin": "ai", "model": "m",
            "sources": [Source(reference="DiagnosticReport/P09-img1")]}  # fmt: skip
    return Statement(**{**base, **kw})


def test_imaging_field_is_the_radiologists_signed_opinion_only():
    rec = records.CaseRecord()
    value, sources = export.radiology_opinion(rec)
    assert value.startswith(export.NO_RADIOLOGY) and sources is None
    rec.stanoviska["radiology"] = _stanovisko()  # AI draft, not confirmed: never printed
    value, _ = export.radiology_opinion(rec)
    assert "Nadledvinu" not in value and "nepotvrdil" in value
    rec.stanoviska["radiology"] = _stanovisko(confirmed_by="Radiologie")
    value, sources = export.radiology_opinion(rec)
    assert "Nadledvinu" in value and "potvrdil(a) Radiologie" in value
    assert sources == ["DiagnosticReport/P09-img1"]  # AI → blue, cited
    rec.stanoviska["radiology"] = _stanovisko(origin="human", sources=[], model=None,
                                              confirmed_by="Radiologie")  # fmt: skip
    value, sources = export.radiology_opinion(rec)
    assert value.startswith("Nadledvinu") and sources is None  # the radiologist's own → black


def test_history_draft_never_fills_the_imaging_opinion(monkeypatch):
    monkeypatch.setattr(
        export.llm,
        "chat_json",
        lambda s, u, schema, name: {
            k: {"hodnota": "x", "zdroje": []} for k in schema["properties"]
        },
    )
    assert export.IMAGING not in {p.split(" > ")[-1] for p in export.draft_history(RESOURCES)}


def test_compliance_keeps_the_board_reasons_beside_the_ai_assessment():
    a = records.GuidelineAssessment(
        status="compliant",
        statement=_stanovisko(text="Postup odpovídá PLI-2.1.", model="m"),
        compared_plan="p", compared_rationale="r", compared_intent="curative",
        recommendation="x", recommendation_sources=[],
    )  # fmt: skip
    d = records.Decision(rationale="Kurativní záměr, pacient souhlasí.", guideline_compliant=True,
                         guideline_assessment=a)  # fmt: skip
    lines = {f.label: f for f in export.compliance_lines(d)}
    ai = lines["Hodnocení AI (m)"]
    assert ai.value.startswith("V souladu – Postup") and ai.sources  # AI, blue, cited
    assert lines["Zdůvodnění komise"].value == "Kurativní záměr, pacient souhlasí."
    assert lines["Zdůvodnění komise"].sources is None  # the board's words, black
    d = records.Decision(guideline_compliant=False, deviation_reason="Pacient odmítá operaci.")
    lines = {f.label: f.value for f in export.compliance_lines(d)}
    assert lines["Soulad dle komise"] == "Ne"  # no AI assessment: the board's own verdict
    assert lines["Důvod odchylky"] == "Pacient odmítá operaci."
    assert lines["Zdůvodnění komise"] == export.NOT_FILLED
