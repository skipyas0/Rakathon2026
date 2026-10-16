"""Ground rules of the project, encoded as types. Every piece of content shown to clinicians is a
Statement. See AGENTS.md "Ground rules" — do not bypass these models when returning content."""

import datetime as dt
from typing import Literal

from pydantic import BaseModel, model_validator

NOT_FOUND = "V dostupné dokumentaci se nenachází."  # required wording from the brief


class Source(BaseModel):
    """Pointer to the exact record a statement is based on."""

    reference: str  # FHIR reference, e.g. "DiagnosticReport/42" or "QuestionnaireResponse/7"
    title: str | None = None  # the record's title, e.g. "CT hrudníku, břicha a pánve"
    excerpt: str | None = None  # quoted passage the UI highlights on click
    date: dt.date | None = None
    author: str | None = None


class Statement(BaseModel):
    """origin: "ai" = machine-generated proposal (needs confirmation); "human" = written by a clinician
    in this app or the nomination; "record" = taken from the health record as-is (ground truth)."""

    text: str
    origin: Literal["ai", "human", "record"]
    sources: list[Source] = []
    model: str | None = None  # model + prompt version, required for AI output
    confirmed_by: str | None = None  # clinician who wrote or approved it
    confirmed_at: dt.datetime | None = None

    @model_validator(mode="after")
    def _enforce_ground_rules(self):
        if self.origin == "ai":
            if not self.model:
                raise ValueError("AI statement must record which model produced it")
            if not self.sources and not self.text.endswith(NOT_FOUND):
                raise ValueError(f"AI statement needs a source, or must end with {NOT_FOUND!r}")
        if self.origin == "record" and not self.sources:
            raise ValueError("Record statement must cite the record it comes from")
        if self.origin == "human" and not self.confirmed_by:
            raise ValueError("Human statement must name the clinician (confirmed_by)")
        return self

    @property
    def official(self) -> bool:
        """Only clinician-confirmed content may enter the official MDT record."""
        return self.confirmed_by is not None
