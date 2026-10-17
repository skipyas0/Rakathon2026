"""A board specialist's stanovisko and stance for one meeting (the specialist's journey). Only these
endpoints write them; the coordinator's record save keeps what is stored (records.put_record).
Vygenerovat runs the agent's specialist step on its own (agent.stanovisko: 3 LLM calls at low
reasoning effort, verdict only, ~20 s)."""

import httpx
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from mdt_backend import agent
from mdt_backend.config import settings
from mdt_backend.features import cases, records
from mdt_backend.features.records import CaseRecord
from mdt_backend.provenance import Statement

router = APIRouter(prefix="/api/cases")

_SIGNED = {"confirmed_by", "confirmed_at"}


class Update(BaseModel):
    """Fields left out stay as they are."""

    supports: bool | None = None
    # the specialist's own text (origin "human"), or the AI draft unchanged, now confirmed
    statement: Statement | None = None


def _open(case_id: str, specialty: str) -> CaseRecord:
    r = records._load(case_id)  # 404 for an unknown case
    if r.decision.confirmed_by:
        raise HTTPException(409, "Závěr je potvrzen a uzamčen")
    if specialty not in {m.specialty for m in r.board}:
        raise HTTPException(404, f"Odbornost {specialty!r} není v komisi")
    return r


@router.post("/{case_id}/stanovisko/{specialty}/generate")
def generate(case_id: str, specialty: str) -> CaseRecord:
    """The specialist's AI draft (blue, cited); replaces the stored stanovisko."""
    if specialty not in agent.SPECIALISTS:
        raise HTTPException(404, f"Pro odbornost {specialty!r} AI stanovisko nepřipravuje")
    _open(case_id, specialty)  # fail before the LLM calls, not after
    if not settings.azure_api_key:
        raise HTTPException(503, "AI návrh nelze vytvořit: chybí přístup k jazykovému modelu")
    with cases.fhir_server():
        rec = agent.Record(cases.meetings()[case_id])
    try:
        s = agent.stanovisko(rec, specialty)
    except httpx.HTTPStatusError as e:
        raise HTTPException(503, f"AI návrh nelze vytvořit (HTTP {e.response.status_code})") from e
    except (httpx.HTTPError, RuntimeError, KeyError) as e:
        raise HTTPException(503, f"AI návrh nelze vytvořit ({type(e).__name__})") from e
    if not s:
        raise HTTPException(502, "AI stanovisko nedoložilo zdroji, zkuste to znovu")
    r = _open(case_id, specialty)  # read again: others may have saved during the LLM calls
    r.stanoviska[specialty] = s
    records.save(case_id, r)
    return r


@router.patch("/{case_id}/stanovisko/{specialty}")
def update(case_id: str, specialty: str, u: Update) -> CaseRecord:
    r = _open(case_id, specialty)
    if u.supports is not None:
        r.board = [
            m.model_copy(update={"supports": u.supports}) if m.specialty == specialty else m
            for m in r.board
        ]
    if (s := u.statement) is not None:
        old = r.stanoviska.get(specialty)
        # AI text only as the agent wrote it; anything edited is the specialist's own (signed)
        if s.origin != "human" and (
            not old or s.model_dump(exclude=_SIGNED) != old.model_dump(exclude=_SIGNED)
        ):
            raise HTTPException(422, "Upravené stanovisko musí podepsat odborník")
        r.stanoviska[specialty] = s
    records.save(case_id, r)
    return r
