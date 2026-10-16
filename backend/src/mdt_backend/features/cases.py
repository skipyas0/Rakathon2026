"""Serves MDT briefings: built from the FHIR bundles (from_fhir.py), the AI-augmented version of
that briefing when the agent has been run for the case (agent.py → data/ai_cases/), or hand-made
stubs in data/stubs/. All are the same `Case` shape, so the frontend can't tell them apart."""

from pathlib import Path

from fastapi import APIRouter, HTTPException

from mdt_backend import agent, bundles
from mdt_backend.briefing import Case
from mdt_backend.from_fhir import build_case

STUBS = Path(__file__).parents[4] / "data" / "stubs"

router = APIRouter(prefix="/api")


def stub_paths() -> dict[str, Path]:
    return {p.stem: p for p in sorted(STUBS.glob("*.json"))}


def case_ids() -> list[str]:
    return [*bundles.bundle_paths(), *stub_paths()]


@router.get("/cases/{case_id}")
def get_case(case_id: str) -> Case:
    # lookups, not path joins: case_id never reaches the filesystem unchecked
    if path := bundles.bundle_paths().get(case_id):
        if (ai := agent.OUT_DIR / f"{case_id}.json").exists():
            return Case.model_validate_json(ai.read_text(encoding="utf-8"))
        return build_case(case_id, bundles.load(path))
    if path := stub_paths().get(case_id):
        return Case.model_validate_json(path.read_text(encoding="utf-8"))
    raise HTTPException(404, f"No case {case_id!r}")


@router.get("/sources/{resource_type}/{resource_id}")
def get_source(resource_type: str, resource_id: str) -> dict:
    """The full text of a source record, for the 'whole record' view in the source drawer."""
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
