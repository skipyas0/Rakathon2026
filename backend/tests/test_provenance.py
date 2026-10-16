import pytest
from pydantic import ValidationError

from mdt_backend.provenance import NOT_FOUND, Source, Statement


def test_ai_statement_requires_source():
    with pytest.raises(ValidationError):
        Statement(text="ECOG 1", origin="ai", model="x")


def test_ai_statement_may_say_not_found():
    assert not Statement(text=NOT_FOUND, origin="ai", model="x").official


def test_ai_statement_requires_model():
    with pytest.raises(ValidationError):
        Statement(text="ECOG 1", origin="ai", sources=[Source(reference="Observation/1")])


def test_human_statement_requires_clinician():
    with pytest.raises(ValidationError):
        Statement(text="Neoadjuvant chemo", origin="human")


def test_confirmed_ai_statement_is_official():
    s = Statement(
        text="ECOG 1",
        origin="ai",
        model="x",
        sources=[Source(reference="Observation/1")],
        confirmed_by="MUDr. Test",
    )
    assert s.official and s.origin == "ai"
