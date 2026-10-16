"""The MDT record for a case across the three phases: preparation (question, readiness), meeting
(specialists' notes, confirmed AI statements) and follow-up (decision, action plan).
ponytail: one JSON file per case in data/records/; swap for FHIR CarePlan/Task/Provenance
(or a DB) when export to the health record is built."""

import datetime as dt
from pathlib import Path
from typing import Literal

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, model_validator

from mdt_backend.features.cases import case_ids, get_case

RECORDS = Path(__file__).parents[4] / "data" / "records"

router = APIRouter(prefix="/api/cases")

MIN_SPECIALTIES = 3  # brief: at least 3 specialist roles


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


class Member(BaseModel):
    """Board member for this meeting, chosen by the coordinator."""

    name: str
    specialty: str  # section id, e.g. "surgery" (frontend SPECIALTIES)
    chair: bool = False


class Triage(BaseModel):
    """The coordinator's routing of a finding (red flag or missing data). Routing only: the
    finding itself is confirmed by a clinician."""

    action: Literal["meeting", "before", "dismissed"]
    assignee: str | None = None  # specialty that resolves it before the meeting
    reason: str = ""  # why it was dismissed
    resolution: str = ""  # the assignee's answer
    by: str
    at: dt.datetime

    @model_validator(mode="after")
    def _complete(self):
        if self.action == "before" and not self.assignee:
            raise ValueError("Nález k vyřešení předem musí mít přiřazenou odbornost")
        if self.action == "dismissed" and not self.reason.strip():
            raise ValueError("Zamítnutí nálezu vyžaduje důvod")
        return self


class Layout(BaseModel):
    """How this case's briefing is shown: section order, hidden sections, detail level."""

    order: list[str] = []  # section ids; [] = the briefing's own order
    hidden: list[str] = []
    detail: Literal["bullets", "narrative"] = "bullets"


class Attendee(BaseModel):
    name: str
    specialty: str


class Decision(BaseModel):
    attendees: list[Attendee] = []
    intent: Literal["curative", "palliative", "supportive", "surveillance", "deferred"] | None = (
        None
    )
    options_considered: str = ""
    plan: str = ""
    rationale: str = ""
    guideline_compliant: bool | None = None
    deviation_reason: str = ""
    dissent: str = ""
    trial: str = ""
    reevaluation: dt.date | None = None
    consent: list[str] = []  # attendees who agreed, ticked by the coordinator (consensus of all)
    confirmed_by: str | None = None  # who recorded it (coordinator); set = final and locked
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
            if {a.name for a in self.attendees} - set(self.consent):
                raise ValueError("Závěr vyžaduje souhlas všech přítomných členů komise")
        return self


class Task(BaseModel):
    what: str
    who: str = ""
    due: dt.date | None = None
    done: bool = False


class PatientStance(BaseModel):
    """The patient's own decision on the MDT recommendation; it never changes the recommendation."""

    stance: Literal["accepts", "refuses", "discuss"]
    note: str = ""
    by: str
    at: dt.datetime


class CaseRecord(BaseModel):
    confirmations: dict[str, Confirmation] = {}  # key = statement path, e.g. "summary.0"
    prep: Prep = Prep()
    notes: dict[str, Note] = {}  # key = section id, e.g. "surgery"
    decision: Decision = Decision()
    tasks: list[Task] = []
    board: list[Member] = []
    triage: dict[str, Triage] = {}  # key = statement path of the finding, e.g. "red_flags.0"
    layout: Layout = Layout()
    # specialty → section ids it sees; absent = its own section + the patient's
    visibility: dict[str, list[str]] = {}
    # after the meeting: recommendation (decision) ≠ patient's stance ≠ agreed plan ≠ care (tasks)
    patient_stance: PatientStance | None = None
    agreed_plan: str = ""


Status = Literal["prep", "meeting", "followup", "closed"]


def status(record: CaseRecord) -> Status:
    if record.decision.confirmed_by:
        return "closed" if record.tasks and all(t.done for t in record.tasks) else "followup"
    return "meeting" if record.prep.prepared_by else "prep"


def _path(case_id: str) -> Path:
    if case_id not in case_ids():  # whitelist: case_id never reaches the filesystem unchecked
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
    for case_id in case_ids():
        c, r = get_case(case_id), _load(case_id)
        out.append(
            {
                "id": c.id,
                "label": c.label,
                "tumour": c.tumour,
                "question": r.prep.question or (c.question.text if c.question else ""),
                "board": c.board,
                "mdt_date": c.mdt_date,
                "flags": sum(f.severity == "high" for f in c.red_flags),
                "intent": r.decision.intent,
                "status": status(r),
                "specialties": sorted({m.specialty for m in r.board}),  # who may open it
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
    if record.prep.prepared_by and len({m.specialty for m in record.board}) < MIN_SPECIALTIES:
        raise HTTPException(422, f"Komise musí mít alespoň {MIN_SPECIALTIES} odbornosti")
    RECORDS.mkdir(parents=True, exist_ok=True)
    _path(case_id).write_text(record.model_dump_json(indent=2), "utf-8")
    return record
