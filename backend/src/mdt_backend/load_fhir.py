"""Load the organisers' FHIR bundles (Dataset/fhir/bundles.ndjson) into the FHIR server.

Run: cd backend && uv run mdt-load-fhir [path/to/bundles.ndjson]

The bundles are `collection` type, which FHIR servers don't accept via POST, so each one is
re-sent as a `transaction` of PUTs. PUT keeps the dataset's IDs (Patient/P01, …) and makes
reloading idempotent (shared resources such as Organization/ORG-FN are just overwritten).

Some dataset IDs contain "_", which FHIR R4 forbids ([A-Za-z0-9.-]{1,64}) and IRIS rejects; they
are stored with "_" replaced by "-" (e.g. Observation/P01-lab01-hb_f -> P01-lab01-hb-f), and
references to them are rewritten to match. The original id is kept on the resource as
meta.tag {system: DATASET_ID, code: <original id>}, so readers of the server can cite the dataset's
ids without the bundle files (`dataset_id`).

Two other R4 violations IRIS rejects are repaired without losing data:
- Observation.derivedFrom -> DiagnosticReport (type not allowed) is moved to the extension
  DERIVED_FROM_REPORT with the same valueReference, so the source link is preserved.
- Empty QuestionnaireResponse answers (valueString "") are dropped; the item stays, unanswered.
"""

import json
import re
import sys
from pathlib import Path

import httpx

from mdt_backend.config import settings

DEFAULT_PATH = settings.dataset_dir / "fhir" / "bundles.ndjson"
DERIVED_FROM_REPORT = "https://rakathon.example.org/fhir/StructureDefinition/derived-from-report"
DATASET_ID = "https://rakathon.example.org/fhir/sid/dataset-id"


def fhir_id(raw: str) -> str:
    return re.sub(r"[^A-Za-z0-9.-]", "-", raw)


def dataset_id(res: dict) -> str:
    """The resource's id as in the dataset (undoes the "_" rewrite using the DATASET_ID tag)."""
    tags = (res.get("meta") or {}).get("tag", [])
    return next((t["code"] for t in tags if t.get("system") == DATASET_ID), res["id"])


def _fix_refs(node):
    if isinstance(node, dict):
        return {
            k: (
                "/".join([*v.split("/")[:-1], fhir_id(v.split("/")[-1])])
                if k == "reference" and isinstance(v, str)
                else _fix_refs(v)
            )
            for k, v in node.items()
        }
    if isinstance(node, list):
        return [_fix_refs(v) for v in node]
    return node


def _drop_empty_answers(items: list) -> None:
    for item in items:
        if "answer" in item:
            item["answer"] = [a for a in item["answer"] if a.get("valueString", True) != ""]
            if not item["answer"]:
                del item["answer"]
        _drop_empty_answers(item.get("item", []))


def to_r4(res: dict) -> dict:
    """Return a copy of `res` repaired to pass strict R4 validation (see module docstring)."""
    res = _fix_refs(res)
    if (new := fhir_id(res["id"])) != res["id"]:
        meta = res.setdefault("meta", {})
        meta["tag"] = [*meta.get("tag", []), {"system": DATASET_ID, "code": res["id"]}]
        res["id"] = new
    if res["resourceType"] == "Observation" and "derivedFrom" in res:
        reports = [d for d in res["derivedFrom"] if d["reference"].startswith("DiagnosticReport/")]
        res["derivedFrom"] = [d for d in res["derivedFrom"] if d not in reports]
        if not res["derivedFrom"]:
            del res["derivedFrom"]
        if reports:
            res.setdefault("extension", []).extend(
                {"url": DERIVED_FROM_REPORT, "valueReference": d} for d in reports
            )
    if res["resourceType"] == "QuestionnaireResponse":
        _drop_empty_answers(res.get("item", []))
    return res


def to_transaction(bundle: dict) -> dict:
    entries = []
    for entry in bundle["entry"]:
        res = to_r4(entry["resource"])
        url = f"{res['resourceType']}/{res['id']}"
        entries.append({"resource": res, "request": {"method": "PUT", "url": url}})
    return {"resourceType": "Bundle", "type": "transaction", "entry": entries}


def put(tx: dict) -> httpx.Response:
    """Send one transaction bundle to the FHIR server."""
    auth = (settings.fhir_user, settings.fhir_password) if settings.fhir_user else None
    return httpx.post(
        settings.fhir_base_url,
        json=tx,
        auth=auth,
        headers={"Content-Type": "application/fhir+json", "Accept": "application/fhir+json"},
        timeout=300,
    )


def load(path: Path = DEFAULT_PATH) -> None:
    lines = [line for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]
    for i, line in enumerate(lines, 1):
        tx = to_transaction(json.loads(line))
        patient = next(
            e["resource"]["id"] for e in tx["entry"] if e["request"]["url"].startswith("Patient/")
        )
        r = put(tx)
        if r.is_error:
            sys.exit(f"[{i}/{len(lines)}] {patient}: HTTP {r.status_code}\n{r.text[:2000]}")
        print(f"[{i}/{len(lines)}] {patient}: {len(tx['entry'])} resources -> HTTP {r.status_code}")


def main() -> None:
    load(Path(sys.argv[1]) if len(sys.argv) > 1 else DEFAULT_PATH)


if __name__ == "__main__":
    main()
