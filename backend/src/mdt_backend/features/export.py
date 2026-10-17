"""The confirmed conclusion as a PDF download: the official record, human decisions only (nothing
in it needs an AI label). Rendered with pdf.PdfDoc (embedded font with Czech glyphs)."""

import tempfile
from pathlib import Path
from zoneinfo import ZoneInfo

from fastapi import APIRouter, HTTPException
from fastapi.responses import Response

from mdt_backend.features import cases, records
from mdt_backend.pdf import GREY, PdfDoc, Run

router = APIRouter(prefix="/api/cases")
PRAGUE = ZoneInfo("Europe/Prague")  # stored times are UTC; the record shows local time

INTENTS = {
    "curative": "Kurativní",
    "palliative": "Paliativní",
    "supportive": "Podpůrná péče",
    "surveillance": "Sledování",
    "deferred": "Odloženo",
}


@router.get("/{case_id}/zaver.pdf")
def zaver_pdf(case_id: str) -> Response:
    c = cases.get_case(case_id)  # 404 for an unknown case
    r = records.get_record(case_id)
    d = r.decision
    if not d.confirmed_by:
        raise HTTPException(409, "Závěr zatím není potvrzen")
    at = f", {d.confirmed_at.astimezone(PRAGUE):%d. %m. %Y %H:%M}" if d.confirmed_at else ""
    rows = [
        ("Otázka pro komisi", r.prep.question or (c.question.text if c.question else "Chybí")),
        ("Komise", ", ".join(a.specialty for a in d.attendees)),
        ("Léčebný záměr", INTENTS.get(d.intent or "", "")),
        ("Zvolený postup", d.plan),
        ("Zdůvodnění", d.rationale),
        (
            "Soulad s doporučenými postupy",
            "Ano" if d.guideline_compliant else f"Ne – {d.deviation_reason}",
        ),
        ("Potvrdil(a)", f"{d.confirmed_by}{at} (konsenzus komise)"),
    ]
    mdt = c.mdt_date and f"MDT {c.mdt_date:%d. %m. %Y}"
    doc = PdfDoc(f"Závěr MDT – {c.label}", footer=f"Závěr zasedání MDT · {c.label}")
    doc.paragraph([Run("Závěr zasedání MDT", bold=True)], size=16)
    doc.paragraph([Run(" · ".join(x for x in (c.label, c.board, mdt) if x), color=GREY)], size=9)
    for label, value in rows:
        doc.space(10)
        doc.paragraph([Run(label, bold=True)], size=10)
        doc.paragraph(value or "–", size=11)
    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / "zaver.pdf"
        doc.save(path)
        data = path.read_bytes()
    name = f"zaver-mdt-{case_id}.pdf"
    return Response(
        data,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{name}"'},
    )
