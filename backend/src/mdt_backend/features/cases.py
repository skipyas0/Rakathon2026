"""Serves MDT briefings. ponytail: reads stubs from data/stubs/; swap for the AI pipeline later,
keeping the `Case` response shape."""

from pathlib import Path

from fastapi import APIRouter, HTTPException

from mdt_backend.briefing import Case

STUBS = Path(__file__).parents[4] / "data" / "stubs"

router = APIRouter(prefix="/api/cases")


def _stubs() -> dict[str, Path]:
    return {p.stem: p for p in sorted(STUBS.glob("*.json"))}


@router.get("")
def list_cases() -> list[dict]:
    cases = (Case.model_validate_json(p.read_text(encoding="utf-8")) for p in _stubs().values())
    return [{"id": c.id, "label": c.label, "tumour": c.tumour} for c in cases]


@router.get("/{case_id}")
def get_case(case_id: str) -> Case:
    path = _stubs().get(case_id)  # lookup, not path join: no traversal via case_id
    if not path:
        raise HTTPException(404, f"No case {case_id!r}")
    return Case.model_validate_json(path.read_text(encoding="utf-8"))
