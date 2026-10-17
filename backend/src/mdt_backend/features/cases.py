"""Serves MDT briefings: the AI-augmented briefing when the agent has been run for the case
(agent.py → data/ai_cases/), otherwise the deterministic one built from the patient's record
(from_fhir.py), or hand-made stubs in data/stubs/. All are the same `Case` shape, so the frontend
can't tell them apart. Patient data come from the IRIS FHIR server; the bundles on disk are only
a fallback while the server is unreachable (decision #18)."""

import re
from pathlib import Path

import httpx
from fastapi import APIRouter, HTTPException

from mdt_backend import agent, bundles, fhir
from mdt_backend.briefing import Case
from mdt_backend.bundles import Bundle
from mdt_backend.from_fhir import build_case
from mdt_backend.load_fhir import fhir_id

STUBS = Path(__file__).parents[4] / "data" / "stubs"
_AUTHOR_FIELDS = ("performer", "author", "requester", "recorder")

router = APIRouter(prefix="/api")


def stub_paths() -> dict[str, Path]:
    return {p.stem: p for p in sorted(STUBS.glob("*.json"))}


def patient_case_ids() -> list[str]:
    try:
        return [p.lower() for p in agent.patient_ids()]
    except httpx.HTTPError:
        return list(bundles.bundle_paths())


def case_ids() -> list[str]:
    return [*patient_case_ids(), *stub_paths()]


def _record(case_id: str) -> Bundle:
    try:
        return agent.Record(case_id, "iris").bundle
    except httpx.HTTPError:
        if path := bundles.bundle_paths().get(case_id):
            return bundles.load(path)
        raise HTTPException(503, "FHIR server nedostupný") from None


@router.get("/cases/{case_id}")
def get_case(case_id: str) -> Case:
    # lookups, not path joins: case_id never reaches the filesystem unchecked
    if case_id in patient_case_ids():
        if (ai := agent.OUT_DIR / f"{case_id}.json").exists():
            return Case.model_validate_json(ai.read_text(encoding="utf-8"))
        return build_case(case_id, _record(case_id))
    if path := stub_paths().get(case_id):
        return Case.model_validate_json(path.read_text(encoding="utf-8"))
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
    try:
        found = _from_iris(resource_type, resource_id)
    except httpx.HTTPError:  # server unreachable
        found = bundles.find(f"{resource_type}/{resource_id}")
    if not found:
        raise HTTPException(404, "Záznam není v dostupných datech")
    b, r = found
    return {
        "title": bundles.title_of(r),
        "date": bundles.date_of(r),
        "author": bundles.author_of(b, r),
        "text": bundles.text_of(r),
    }
