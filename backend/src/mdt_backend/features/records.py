"""The MDT record for a case across the three phases: preparation (question, readiness), meeting
(specialists' notes, confirmed AI statements) and follow-up (decision, action plan).
ponytail: one JSON file per case in data/records/; swap for FHIR CarePlan/Task/Provenance
(or a DB) when export to the health record is built."""

import datetime as dt
from pathlib import Path
from typing import Literal

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, model_validator

from mdt_backend.features.cases import get_case, stub_paths

RECORDS = Path(__file__).parents[4] / "data" / "records"

router = APIRouter(prefix="/api/cases")


class Confirmation(BaseModel):
    by: str
    at: dt.datetime


class Note(BaseModel):
    """A specialist's view on their section, entered during the meeting."""

    text: str
    by: str
    at: dt.datetime


class Prep(BaseModel):
    question: str = ""  # MDT question as checked/refined by the preparing clinician
    questions: list[str] = []  # extra discussion questions added by clinicians
    prepared_by: str | None = None  # set = ready for the meeting
    prepared_at: dt.datetime | None = None


class Attendee(BaseModel):
    name: str
    specialty: str


class Decision(BaseModel):
    attendees: list[Attendee] = []
    intent: Literal["curative", "palliative", "supportive", "surveillance"] | None = None
    options_considered: str = ""
    plan: str = ""
    rationale: str = ""
    guideline_compliant: bool | None = None
    deviation_reason: str = ""
    dissent: str = ""
    trial: str = ""
    reevaluation: dt.date | None = None
    confirmed_by: str | None = None  # chair; set = final and locked
    confirmed_at: dt.datetime | None = None

    @model_validator(mode="after")
    def _final_decision_is_complete(self):
        if self.guideline_compliant is False and not self.deviation_reason.strip():
            raise ValueError("Odchylka od doporučených postupů vyžaduje zdůvodnění")
        if self.confirmed_by:
            missing = [f for f in ("plan", "rationale") if not getattr(self, f).strip()]
            if missing or not self.attendees or None in (self.guideline_compliant, self.intent):
                raise ValueError(
                    "Potvrzený závěr musí obsahovat přítomné, cíl léčby, postup, zdůvodnění "
                    "a soulad s postupy"
                )
        return self


class Task(BaseModel):
    what: str
    who: str = ""
    due: dt.date | None = None
    done: bool = False


class CaseRecord(BaseModel):
    confirmations: dict[str, Confirmation] = {}  # key = statement path, e.g. "summary.0"
    prep: Prep = Prep()
    notes: dict[str, Note] = {}  # key = section id, e.g. "surgery"
    decision: Decision = Decision()
    tasks: list[Task] = []


Status = Literal["prep", "meeting", "followup", "closed"]


def status(record: CaseRecord) -> Status:
    if record.decision.confirmed_by:
        return "closed" if record.tasks and all(t.done for t in record.tasks) else "followup"
    return "meeting" if record.prep.prepared_by else "prep"


def _path(case_id: str) -> Path:
    if case_id not in stub_paths():  # whitelist: case_id never reaches the filesystem unchecked
        raise HTTPException(404, f"No case {case_id!r}")
    return RECORDS / f"{case_id}.json"


def _load(case_id: str) -> CaseRecord:
    path = _path(case_id)
    return (
        CaseRecord.model_validate_json(path.read_text("utf-8")) if path.exists() else CaseRecord()
    )


@router.get("")
def agenda() -> list[dict]:
    """The meeting agenda: every case with its phase, for the home page."""
    out = []
    for case_id in stub_paths():
        c, r = get_case(case_id), _load(case_id)
        out.append(
            {
                "id": c.id,
                "label": c.label,
                "tumour": c.tumour,
                "question": r.prep.question or (c.question.text if c.question else ""),
                "flags": sum(f.severity == "high" for f in c.red_flags),
                "intent": r.decision.intent,
                "status": status(r),
            }
        )
    return out


@router.get("/{case_id}/record")
def get_record(case_id: str) -> CaseRecord:
    return _load(case_id)


@router.put("/{case_id}/record")
def put_record(case_id: str, record: CaseRecord) -> CaseRecord:
    old = _load(case_id)
    if old.decision.confirmed_by and record.decision != old.decision:
        raise HTTPException(409, "Závěr je potvrzen a uzamčen")
    if record.prep.prepared_by and not (record.prep.question.strip() or get_case(case_id).question):
        raise HTTPException(422, "Případ nelze připravit bez otázky pro komisi")
    RECORDS.mkdir(parents=True, exist_ok=True)
    _path(case_id).write_text(record.model_dump_json(indent=2), "utf-8")
    return record
