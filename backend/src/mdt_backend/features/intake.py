"""Intake: the coordinator adds a case from one FHIR bundle. Stored as
data/intake/<patient>/bundle.json, where it replaces that patient's record (cases.uploads), and
loaded into the FHIR server too when it's reachable, so `mdt-agent` can brief the patient. PDFs (one per record, as an external doctor sends them) are part of
the API but answer 501 until AI extraction exists."""

import base64
import binascii
import json
import re
from typing import Literal

import httpx
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from mdt_backend import bundles, load_fhir
from mdt_backend.features import cases
from mdt_backend.from_fhir import build_case

router = APIRouter(prefix="/api/intake")

PATIENT_KEY = re.compile(r"[a-z0-9-]{1,64}")  # becomes a folder name


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
    folder = cases.INTAKE / key
    folder.mkdir(parents=True, exist_ok=True)
    (folder / "bundle.json").write_text(json.dumps(data, ensure_ascii=False), "utf-8")
    try:
        load_fhir.put(load_fhir.to_transaction(data)).raise_for_status()
    except httpx.HTTPError:
        pass  # ponytail: no server (e.g. on Fly) = the disk copy alone; the agent can't brief it
    return {"case_id": cases.meeting_id(key, b)}
