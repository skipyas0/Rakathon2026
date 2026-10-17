"""Shared test data. The organisers' dataset isn't in git, so tests using it skip without it (CI)."""

import json

import httpx
import pytest

from mdt_backend import fhir, load_fhir
from mdt_backend.config import settings

# Patient ("p01") → the dataset's bundle JSON (pacienti/P01_bundle.json or pacienti/P01/…)
BUNDLES = {
    p.name.split("_")[0].lower(): json.loads(p.read_text("utf-8"))
    for p in sorted((settings.dataset_dir / "pacienti").rglob("*_bundle.json"))
}
needs_dataset = pytest.mark.skipif(not BUNDLES, reason="no dataset (it's not in git)")


@pytest.fixture
def fake_fhir(monkeypatch):
    """The FHIR server holding the dataset as `mdt-load-fhir` stores it (ids with "_" rewritten,
    the original kept as a tag), answering `fhir.get` and `fhir.get_patient_record`."""
    by_patient = {
        p.upper(): [e["resource"] for e in load_fhir.to_transaction(b)["entry"]]
        for p, b in BUNDLES.items()
    }
    stored = {f"{r['resourceType']}/{r['id']}": r for rs in by_patient.values() for r in rs}

    def get(path, **params):
        if "/" not in path:  # a search, e.g. Task?_count=200
            return {
                "entry": [{"resource": r} for r in stored.values() if r["resourceType"] == path]
            }
        if path in stored:
            return stored[path]
        req = httpx.Request("GET", f"http://fhir/{path}")
        raise httpx.HTTPStatusError("404", request=req, response=httpx.Response(404, request=req))

    monkeypatch.setattr(fhir, "get", get)
    monkeypatch.setattr(fhir, "get_patient_record", lambda pid: by_patient[pid])
