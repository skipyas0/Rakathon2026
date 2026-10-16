"""Every stub (if any) must match the contract. Run: cd backend && uv run pytest tests/test_stubs.py"""

import pytest

from mdt_backend.briefing import Case
from mdt_backend.features.cases import STUBS

FILES = sorted(STUBS.glob("*.json"))


@pytest.mark.parametrize("path", FILES, ids=lambda p: p.name)
def test_stub_is_valid_case(path):
    case = Case.model_validate_json(path.read_text(encoding="utf-8"))
    assert case.id == path.stem, "case id must match the filename"
    for flag in case.red_flags:
        assert len(flag.statement.sources) >= 2, (
            f"red flag needs both sources: {flag.statement.text}"
        )
