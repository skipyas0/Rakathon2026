"""Thin read client for the FHIR server. Returns raw FHIR JSON; map to domain models elsewhere."""

import json
import sys
from collections import defaultdict

import httpx

from mdt_backend.config import settings

# Patient-linked types that Patient/$everything misses because their link to the patient is
# outside the R4 Patient compartment (Task.for), fetched with an extra `?patient=` search.
_OUTSIDE_COMPARTMENT = ("Task",)


def _auth() -> tuple[str, str] | None:
    return (settings.fhir_user, settings.fhir_password) if settings.fhir_user else None


def get(path: str, **params) -> dict:
    """GET a FHIR resource or search, e.g. get("Patient", name="Novak") or get("Patient/123")."""
    r = httpx.get(f"{settings.fhir_base_url}/{path}", params=params, auth=_auth(), timeout=10)
    r.raise_for_status()
    return r.json()


def _all_resources(path: str, **params) -> list[dict]:
    """All resources of a searchset/$everything Bundle, following `next` paging links."""
    bundle = get(path, **params)
    resources = [e["resource"] for e in bundle.get("entry", [])]
    while nxt := next(
        (lk["url"] for lk in bundle.get("link", []) if lk["relation"] == "next"), None
    ):
        r = httpx.get(nxt, auth=_auth(), timeout=30)
        r.raise_for_status()
        bundle = r.json()
        resources += [e["resource"] for e in bundle.get("entry", [])]
    return resources


def get_patient_record(patient_id: str) -> list[dict]:
    """Every resource for one patient: Patient/$everything (the patient, everything in their
    compartment, plus referenced Practitioners/Organizations) + the types it misses. Deduplicated."""
    resources = _all_resources(f"Patient/{patient_id}/$everything")
    for rtype in _OUTSIDE_COMPARTMENT:
        resources += _all_resources(rtype, patient=patient_id)
    unique = {f"{r['resourceType']}/{r['id']}": r for r in resources}
    return list(unique.values())


def format_patient_record(resources: list[dict]) -> str:
    """Human-readable dump: Patient first, then one section per resource type, each resource as
    indented JSON (UTF-8, so Czech text stays readable)."""
    by_type: dict[str, list[dict]] = defaultdict(list)
    for r in resources:
        by_type[r["resourceType"]].append(r)
    types = sorted(by_type, key=lambda t: (t != "Patient", t))
    counts = ", ".join(f"{t} {len(by_type[t])}" for t in types)
    out = [f"{len(resources)} resources: {counts}"]
    for t in types:
        out.append(f"\n{'=' * 80}\n{t} ({len(by_type[t])})\n{'=' * 80}")
        for r in sorted(by_type[t], key=lambda r: r["id"]):
            out.append(f"--- {t}/{r['id']}")
            out.append(json.dumps(r, indent=2, ensure_ascii=False))
    return "\n".join(out)


def print_patient_record(patient_id: str) -> None:
    """Fetch the complete structured record of one patient and pretty-print it to stdout."""
    print(format_patient_record(get_patient_record(patient_id)))


def main() -> None:
    """CLI: uv run mdt-patient P01"""
    if len(sys.argv) != 2:
        sys.exit("usage: mdt-patient <patient-id>")
    try:
        print_patient_record(sys.argv[1])
    except httpx.HTTPStatusError as e:
        sys.exit(f"{sys.argv[1]}: HTTP {e.response.status_code} from {e.request.url}")
