"""Thin read client for the FHIR server. Returns raw FHIR JSON; map to domain models elsewhere."""

import httpx

from mdt_backend.config import settings


def get(path: str, **params) -> dict:
    """GET a FHIR resource or search, e.g. get("Patient", name="Novak") or get("Patient/123")."""
    auth = (settings.fhir_user, settings.fhir_password) if settings.fhir_user else None
    r = httpx.get(f"{settings.fhir_base_url}/{path}", params=params, auth=auth, timeout=10)
    r.raise_for_status()
    return r.json()
