"""Serves MDT briefings: the AI-augmented briefing when the agent has been run for the patient
(agent.py → data/ai_cases/), otherwise the deterministic one built from the patient's record
(from_fhir.py). Both are the same `Case` shape, so the frontend can't tell them apart. Patient
data come only from the IRIS FHIR server; while it's unreachable the API answers 503 (decision #24).
A case is one meeting about one patient: its id is the patient plus the planned MDT date
("p03-2026-10-21"), so a patient's next MDT gets its own case and record."""

import re
import time
from contextlib import contextmanager
from typing import Literal

import httpx
from fastapi import APIRouter, HTTPException

from mdt_backend import agent, bundles, fhir
from mdt_backend.briefing import Case
from mdt_backend.bundles import Bundle
from mdt_backend.from_fhir import build_case, planned_date
from mdt_backend.load_fhir import fhir_id

_AUTHOR_FIELDS = ("performer", "author", "requester", "recorder")

router = APIRouter(prefix="/api")


@contextmanager
def fhir_server():
    """Turns an unreachable FHIR server into 503; 4xx/5xx answers propagate as they are."""
    try:
        yield
    except httpx.TransportError:
        raise HTTPException(503, "FHIR server nedostupný") from None


def meeting_id(patient: str, b: Bundle) -> str:
    """ "p03-2026-10-21", or just "p03" without a planned date."""
    date = planned_date(b)
    return f"{patient}-{date}" if date else patient


def meetings() -> dict[str, str]:
    """Case id → patient: the patients nominated on the FHIR server (a `Task` for them)."""
    with fhir_server():
        tasks = [e["resource"] for e in fhir.get("Task", _count=200).get("entry", [])]
    found = {
        t["for"]["reference"].split("/")[-1].lower(): Bundle({"entry": [{"resource": t}]})
        for t in tasks
        if t.get("for", {}).get("reference", "").startswith("Patient/")
    }
    return {meeting_id(p, b): p for p, b in found.items()}


def case_ids() -> list[str]:
    return list(meetings())


def record(patient: str) -> Bundle:
    with fhir_server():
        return agent.Record(patient).bundle


def ai_status(patient: str) -> Literal["running", "done"] | None:
    """Whether the agent is briefing the patient now, has briefed them, or never ran for them."""
    marker = agent.running_path(patient)
    # ponytail: a run killed mid-way leaves its marker; treat it as stale after an hour (a full
    # batch takes ~10 min)
    if marker.exists() and time.time() - marker.stat().st_mtime < 3600:
        return "running"
    return "done" if (agent.OUT_DIR / f"{patient}.json").exists() else None


@router.get("/cases/{case_id}/ai")
def get_ai_status(case_id: str) -> dict:
    if (patient := meetings().get(case_id)) is None:
        raise HTTPException(404, f"No case {case_id!r}")
    return {"status": ai_status(patient)}


@router.get("/cases/{case_id}")
def get_case(case_id: str) -> Case:
    # lookups, not path joins: case_id never reaches the filesystem unchecked
    if patient := meetings().get(case_id):
        if (ai := agent.OUT_DIR / f"{patient}.json").exists():
            case = Case.model_validate_json(ai.read_text(encoding="utf-8"))
            return case.model_copy(update={"id": case_id})
        return build_case(case_id, record(patient))
    raise HTTPException(404, f"No case {case_id!r}")


def _from_iris(resource_type: str, resource_id: str) -> tuple[Bundle, dict] | None:
    """One resource by its dataset id (+ its author, for the name), read from the FHIR server."""
    try:
        r = fhir.get(f"{resource_type}/{fhir_id(resource_id)}")
    except httpx.HTTPStatusError:
        return None
    linked = []
    for field in _AUTHOR_FIELDS:
        v = r.get(field)
        v = v[0] if isinstance(v, list) and v else v
        if isinstance(v, dict) and re.fullmatch(
            r"(Practitioner|Organization)/[\w.-]+", ref := v.get("reference", "")
        ):
            try:
                linked.append(fhir.get(ref))
            except httpx.HTTPStatusError:
                pass
            break
    r = {**r, "id": resource_id}
    return Bundle({"entry": [{"resource": x} for x in (r, *linked)]}), r


@router.get("/sources/{resource_type}/{resource_id}")
def get_source(resource_type: str, resource_id: str) -> dict:
    """The full text of a source record, for the 'whole record' view in the source drawer."""
    if not re.fullmatch(r"[A-Z][A-Za-z]+", resource_type) or not re.fullmatch(
        r"[\w.-]+", resource_id
    ):
        raise HTTPException(404, "Záznam není v dostupných datech")
    with fhir_server():
        found = _from_iris(resource_type, resource_id)
    if not found:
        raise HTTPException(404, "Záznam není v dostupných datech")
    b, r = found
    return {
        "title": bundles.title_of(r),
        "date": bundles.date_of(r),
        "author": bundles.author_of(b, r),
        "text": bundles.text_of(r),
    }
