"""The MDT briefing for one case — the contract between data/AI work and the frontend.
Stubs in data/stubs/*.json must validate against `Case` (docs/stubs.md); the real AI pipeline will
later return the same shape, so the frontend never needs to know which one it got."""

import datetime as dt
from typing import Literal

from pydantic import BaseModel

from mdt_backend.provenance import Source, Statement


class TimelineEvent(BaseModel):
    date: dt.date
    kind: Literal[
        "diagnosis",
        "staging",
        "pathology",
        "surgery",
        "systemic",
        "radiotherapy",
        "imaging",
        "progression",
        "mdt",
    ]
    statement: Statement


class RedFlag(BaseModel):
    severity: Literal["high", "medium", "low"]
    statement: Statement  # cites both conflicting sources (e.g. lab + questionnaire)


class Section(BaseModel):
    """One specialist's view. id is one of: surgery, oncology, radiology, pathology, patient
    (bonus: nuclear, palliative, geriatric, genetics, coordinator)."""

    id: str
    title: str
    items: list[Statement]


class TrialMatch(BaseModel):
    trial: str  # trial id from the organisers' trial list
    verdict: Literal["eligible", "ineligible", "missing_data"]
    criteria: list[Statement]  # one per inclusion/exclusion criterion, with reason


class DecisionSupport(BaseModel):
    options: list[Statement]  # treatment options, each citing a guideline passage
    trials: list[TrialMatch]
    questions: list[Statement]  # 2–3 questions for the board to resolve


class BoardMember(BaseModel):
    """A member of the patient's previous MDT (the record's CareTeam), offered to the coordinator
    as the starting composition of the board."""

    name: str  # practitioner id, "" when the record names only the role
    role: str  # as recorded, e.g. "hepatobiliární chirurg"
    chair: bool = False


class TrendPoint(BaseModel):
    date: dt.date
    value: float
    source: Source  # the exact lab result / questionnaire answer


class Trend(BaseModel):
    """A measured value over time, taken directly from the records (not AI-generated)."""

    id: str  # e.g. "cea", "hb", "proms-fatigue"
    label: str  # e.g. "CEA", "Únava (PROMs)"
    unit: str  # e.g. "µg/l", "/10"
    ref_low: float | None = None  # reference range, drawn as a band
    ref_high: float | None = None
    axis: tuple[float, float] | None = None  # fixed y-axis, e.g. (0, 10) for PROMs scales
    points: list[TrendPoint]


class Case(BaseModel):
    id: str  # matches the stub filename
    patient: str  # FHIR reference, e.g. "Patient/123"
    label: str  # display name as in the mock data (synthetic only)
    tumour: str  # e.g. "colorectal", "breast", "lung"
    board: str | None = None  # which tumour board, e.g. "Mamární komise – karcinom prsu"
    mdt_date: dt.date | None = None  # planned meeting date
    question: Statement | None  # from the nomination (origin "human"); None = incomplete case
    summary: list[Statement]  # executive summary, readable in 30 s
    timeline: list[TimelineEvent]
    red_flags: list[RedFlag]
    sections: list[Section]
    decision_support: DecisionSupport
    trends: list[Trend] = []  # lab markers and PROMs over time, for the meeting charts
    previous_board: list[BoardMember] = []  # who sat on the patient's last MDT
