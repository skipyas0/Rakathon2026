"""A patient's MDT history, read-only: the previous MDT records and treatment decisions from the
health record (Composition), and every meeting of the patient recorded in this app. A new MDT never
overwrites an old one (MDT_ZASEDANI_PROCES.md §7)."""

import re

from fastapi import APIRouter

from mdt_backend import bundles
from mdt_backend.features import cases, records

router = APIRouter(prefix="/api/cases")


@router.get("/{case_id}/history")
def history(case_id: str) -> dict:
    patient = cases.get_case(case_id).patient  # 404 for an unknown case
    b = cases.record(p) if (p := cases.meetings().get(case_id)) else None
    documents = [
        {
            "reference": f"Composition/{r['id']}",
            "title": r.get("title", ""),
            "date": bundles.date_of(r),
            "author": b.name(r["author"][0]["reference"]) if r.get("author") else None,
            "sections": [
                {"title": s["title"], "text": re.sub("<[^>]+>", "", s["text"]["div"]).strip()}
                for s in r.get("section", [])
            ],
        }
        for r in (b.all("Composition") if b else [])
    ]
    meetings = []
    for other in cases.case_ids():
        c = cases.get_case(other)
        if c.patient == patient:
            r = records.get_record(other)
            meetings.append(
                {
                    "id": other,
                    "mdt_date": c.mdt_date,
                    "status": records.status(r),
                    "decision": r.decision,
                }
            )
    return {
        "documents": sorted(documents, key=lambda d: str(d["date"] or "")),
        "meetings": sorted(meetings, key=lambda m: str(m["mdt_date"] or "")),
    }
