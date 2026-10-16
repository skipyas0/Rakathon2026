"""Ground rules of the project, encoded as types. Every piece of content shown to clinicians is a
Statement. See AGENTS.md "Ground rules" — do not bypass these models when returning content."""

import datetime as dt
from typing import Literal

from pydantic import BaseModel, model_validator

NOT_FOUND = "V dostupné dokumentaci se nenachází."  # required wording from the brief


class Source(BaseModel):
    """Pointer to the exact record a statement is based on."""

    reference: str  # FHIR reference, e.g. "DiagnosticReport/42" or "QuestionnaireResponse/7"
    excerpt: str | None = None  # quoted passage the UI highlights on click
    date: dt.date | None = None
    author: str | None = None


class Statement(BaseModel):
    text: str
    origin: Literal["ai", "human"]
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
        if self.origin == "human" and not self.confirmed_by:
            raise ValueError("Human statement must name the clinician (confirmed_by)")
        return self

    @property
    def official(self) -> bool:
        """Only clinician-confirmed content may enter the official MDT record."""
        return self.confirmed_by is not None
