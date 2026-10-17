"""Intake: the coordinator adds a case from one FHIR bundle, loaded into the FHIR server (the only
store of patient data), so the case list, the briefing and `mdt-agent` see it. ponytail: resources
of an earlier upload that the new bundle lacks stay on the server; delete the patient first once
deletion exists. PDFs (one per record, as an external doctor sends them) are part of the API but
answer 501 until AI extraction exists."""

import base64
import binascii
import json
import re
from typing import Literal

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from mdt_backend import bundles, load_fhir
from mdt_backend.features import cases
from mdt_backend.from_fhir import build_case

router = APIRouter(prefix="/api/intake")

PATIENT_KEY = re.compile(r"[a-z0-9.-]{1,64}")  # a valid FHIR id, so the case id matches the server


class File(BaseModel):
    name: str
    data: str  # base64


class Upload(BaseModel):
    kind: Literal["fhir", "pdf"]
    files: list[File]


def _decode(f: File) -> bytes:
    try:
        return base64.b64decode(f.data, validate=True)
    except binascii.Error:
        raise HTTPException(422, f"{f.name}: poškozený soubor") from None


def _from_fhir(files: list[File]) -> dict:
    if len(files) != 1:
        raise HTTPException(422, "Nahrajte jeden FHIR Bundle (.json)")
    try:
        data = json.loads(_decode(files[0]))
    except ValueError:
        raise HTTPException(422, f"{files[0].name}: není platný JSON") from None
    if not isinstance(data, dict) or data.get("resourceType") != "Bundle":
        raise HTTPException(422, f"{files[0].name}: není FHIR Bundle")
    return data


@router.post("")
def upload(u: Upload) -> dict:
    if not u.files:
        raise HTTPException(422, "Nebyly vybrány žádné soubory")
    if u.kind == "pdf":
        raise HTTPException(501, "Zpracování PDF zatím není k dispozici")
    data = _from_fhir(u.files)
    b = bundles.Bundle(data)
    key = next(iter(b.all("Patient")), {}).get("id", "").lower()
    if not PATIENT_KEY.fullmatch(key):
        raise HTTPException(422, "Bundle neobsahuje pacienta")
    try:
        build_case(key, b)  # a bundle the briefing can't be built from is no case
    except Exception as e:  # untrusted input: any gap in it surfaces here
        raise HTTPException(422, f"Z dat nelze sestavit podklad ({type(e).__name__}: {e})") from e
    with cases.fhir_server():
        r = load_fhir.put(load_fhir.to_transaction(data))
    if r.is_error:
        raise HTTPException(
            422, f"FHIR server případ odmítl (HTTP {r.status_code}): {r.text[:300]}"
        )
    return {"case_id": cases.meeting_id(key, b)}
