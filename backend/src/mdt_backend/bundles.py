"""A patient's FHIR resources as one in-memory `Bundle` (built from the server's answer in
agent.Record), plus small accessors shared by from_fhir.py, the agent and the source endpoint."""

import base64
import datetime as dt
import re

from mdt_backend.provenance import Source

LOINC_HB, LOINC_ECOG = "718-7", "89247-1"


class Bundle:
    def __init__(self, data: dict):
        resources = (e["resource"] for e in data.get("entry", []))
        self.by_ref = {f"{r['resourceType']}/{r['id']}": r for r in resources}

    def all(self, resource_type: str) -> list[dict]:
        return [r for ref, r in self.by_ref.items() if ref.startswith(resource_type + "/")]

    def get(self, ref: str) -> dict | None:
        return self.by_ref.get(ref.split("#")[0])

    def name(self, ref: str | None) -> str | None:
        """Display name of a Practitioner/Organization reference."""
        r = self.get(ref) if ref else None
        if not r:
            return None
        name = r.get("name")
        text = name[0].get("text") if isinstance(name, list) else name
        return text.replace(" (fiktivní lékař)", "") if text else r["id"]


# --- small accessors shared by from_fhir.py and the source endpoint ---------------------------

_DATE_FIELDS = (
    "effectiveDateTime",
    "issued",
    "date",
    "authored",
    "authoredOn",
    "performedDateTime",
    "onsetDateTime",
    "occurrenceDateTime",
    "started",
    "created",
)


def date_of(r: dict) -> dt.date | None:
    for f in _DATE_FIELDS:
        v = r.get(f)
        if isinstance(v, str) and len(v) >= 10:
            return dt.date.fromisoformat(v[:10])
    return None


def title_of(r: dict) -> str:
    code = r.get("code") or r.get("type") or {}
    if isinstance(code, dict) and code.get("text"):
        return code["text"]
    return (
        r.get("title")
        or r.get("description")
        or (code.get("coding") or [{}])[0].get("display")
        or r["resourceType"]
    )


def author_of(b: Bundle, r: dict) -> str | None:
    for f in ("performer", "author", "requester", "recorder"):
        v = r.get(f)
        v = v[0] if isinstance(v, list) and v else v
        if isinstance(v, dict):
            return b.name(v.get("reference")) or v.get("display")
    return None


def code_of(r: dict) -> str | None:
    return ((r.get("code") or {}).get("coding") or [{}])[0].get("code")


def category_text(r: dict) -> str:
    cats = r.get("category") or []
    cats = cats if isinstance(cats, list) else [cats]
    return " | ".join(c.get("text") or (c.get("coding") or [{}])[0].get("code", "") for c in cats)


def answers(qr: dict) -> dict[str, tuple[str, dict]]:
    """QuestionnaireResponse: linkId → (question text, first answer)."""
    return {i["linkId"]: (i["text"], i["answer"][0]) for i in qr.get("item", []) if i.get("answer")}


def short_label(question: str) -> str:
    """'Únava za poslední týden (0–10)' → 'Únava'; for compact PROMs labels."""
    return question.split(" (")[0].split(" za ")[0].split(",")[0].split(" –")[0]


def by_date(rs: list[dict]) -> list[dict]:
    return sorted(rs, key=lambda r: date_of(r) or dt.date.min)


def section_text(comp: dict, title: str) -> str:
    s = next((s for s in comp.get("section", []) if s["title"] == title), None)
    return re.sub("<[^>]+>", "", s["text"]["div"]).strip() if s else ""


def src(b: Bundle, r: dict, excerpt: str | None = None, item: str | None = None) -> Source:
    """Source pointing at a resource (and optionally one questionnaire item via #linkId)."""
    ref = f"{r['resourceType']}/{r['id']}" + (f"#{item}" if item else "")
    return Source(
        reference=ref, title=title_of(r), excerpt=excerpt, date=date_of(r), author=author_of(b, r)
    )


def _decode(attachment: dict) -> str:
    return base64.b64decode(attachment["data"]).decode("utf-8") if "data" in attachment else ""


def value_of(r: dict) -> str:
    """Observation / answer value as text, e.g. "95 g/l"."""
    for k, v in r.items():
        if k == "valueQuantity":
            return f"{v['value']:g} {v.get('unit', '')}".strip()
        if k == "valueCoding":
            return v.get("display") or v.get("code", "")
        if k == "valueCodeableConcept":
            return v.get("text") or v["coding"][0].get("display", "")
        if k.startswith("value"):
            return str(v)
    return ""


def text_of(r: dict) -> str:
    """Full human-readable text of a resource, for the 'whole record' view."""
    t = r["resourceType"]
    if t == "DiagnosticReport":
        body = "\n\n".join(_decode(a) for a in r.get("presentedForm", []))
        return "\n\n".join(
            x for x in (body, r.get("conclusion") and f"Závěr: {r['conclusion']}") if x
        )
    if t == "DocumentReference":
        return "\n\n".join(_decode(c["attachment"]) for c in r.get("content", []))
    if t == "Composition":
        return "\n\n".join(
            f"{s['title']}:\n{re.sub('<[^>]+>', '', s['text']['div']).strip()}"
            for s in r.get("section", [])
        )
    if t == "QuestionnaireResponse":
        return "\n".join(
            f"{i['text']}: {value_of(i['answer'][0])}" for i in r["item"] if i.get("answer")
        )
    if t == "Observation":
        rng = (r.get("referenceRange") or [{}])[0]
        lo, hi = rng.get("low", {}).get("value"), rng.get("high", {}).get("value")
        ref = f" (norma {lo:g}–{hi:g})" if lo is not None and hi is not None else ""
        return f"{title_of(r)}: {value_of(r)}{ref}"
    notes = [n["text"] for n in r.get("note", [])]
    return "\n\n".join([title_of(r), *notes])
