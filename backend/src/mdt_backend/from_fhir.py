"""Builds the MDT briefing (`Case`) from a patient's FHIR bundle — deterministically, no LLM.

Everything here is taken from the record (origin "record", ground truth with sources), except red
flags (rules.py, origin "ai": machine-made proposals the clinician confirms). Parts that need an
LLM or documents not in the dataset (guideline options, trial screening) stay empty for now."""

import datetime as dt
import re

from mdt_backend.briefing import (
    BoardMember,
    Case,
    DecisionSupport,
    Section,
    TimelineEvent,
    Trend,
    TrendPoint,
)
from mdt_backend.bundles import (
    LOINC_ECOG,
    LOINC_HB,
    Bundle,
    answer_line,
    answers,
    by_date,
    category_text,
    code_of,
    date_of,
    observation_line,
    section_text,
    short_label,
    src,
    title_of,
    value_of,
)
from mdt_backend.concepts import Symptom
from mdt_backend.provenance import Source, Statement
from mdt_backend.rules import red_flags

TREATMENT_LINE = re.compile(
    r"^- \[(?P<cat>[^\]]+)\] (?P<what>.+) \((?P<start>\d{4}-\d{2}(?:-\d{2})?)"
)
LOINC_MARKERS = {"2039-6", "6875-3", "24108-3", "2857-1", "83112-3", "10334-1"}  # CEA, CA…, PSA
PATIENT_LABELS = {  # PROMs items for the patient's voice, in display order
    "priorita": "Priorita",
    "postoj": "Přání",
    "podpora": "Podpora doma",
    "nove-obtize": "Nové obtíže",
}
PROMS_ALWAYS = ("unava", "bolest")  # always charted; other 0–10 items only when notable
TUMOURS = {
    "C50": "breast",
    "C34": "lung",
    "C18": "colorectal",
    "C19": "colorectal",
    "C20": "colorectal",
}


def rec(text: str, *sources: Source) -> Statement:
    return Statement(text=text, origin="record", sources=list(sources))


def previous_board(b: Bundle) -> list[BoardMember]:
    """Members of the latest previous MDT (CareTeam); the chair is the practitioner whose
    qualification says "předseda"."""
    teams = sorted(b.all("CareTeam"), key=lambda t: t["id"])
    members = []
    for p in teams[-1]["participant"] if teams else []:
        ref = p.get("member", {}).get("reference")
        members.append(
            BoardMember(
                name=ref.split("/")[-1] if ref else "",
                role=p["role"][0]["text"],
                chair="předseda" in (b.name(ref) or ""),
            )
        )
    return members


def planned_date(b: Bundle) -> dt.date | None:
    """Planned meeting = the nomination Task's restriction (ServiceRequest.occurrence is another
    date)."""
    task = next(iter(b.all("Task")), {})
    return date_of({"date": task.get("restriction", {}).get("period", {}).get("start", "")})


def build_case(case_id: str, b: Bundle, symptoms: list[Symptom] | None = None) -> Case:
    """`symptoms`: free-text symptoms classified by the agent's LLM (None = keyword fallback)."""
    patient = b.all("Patient")[0]
    nomination = b.all("ServiceRequest")[0]
    conditions = b.all("Condition")
    onco = [c for c in conditions if category_text(c) == "onkologická diagnóza"]
    observations = by_date(b.all("Observation"))
    proms = by_date(b.all("QuestionnaireResponse"))
    reports = by_date([r for r in b.all("DiagnosticReport") if r.get("conclusion")])
    pathology = [r for r in reports if category_text(r).startswith("Patologie")]
    imaging = [r for r in reports if category_text(r).startswith("Zobrazovací")]
    notes = {n["text"].split(":")[0]: n["text"] for n in nomination.get("note", [])}
    mdt_date = planned_date(b)

    age = next((e["valueInteger"] for e in patient.get("extension", []) if "vek" in e["url"]), None)
    label = patient["name"][0]["text"] + (f", {age} let" if age else "")
    primary = (onco[0]["code"]["coding"][0]["code"] if onco else "")[:3]

    def note(key: str) -> Statement | None:
        text = next((v for k, v in notes.items() if k.startswith(key)), None)
        return rec(text, src(b, nomination, text)) if text else None

    # --- question: written by the referring doctor in the nomination ---
    q_text = nomination["reasonCode"][0]["text"]
    question = Statement(
        text=q_text,
        origin="human",
        sources=[src(b, nomination, q_text)],
        confirmed_by=b.name(nomination["requester"]["reference"]),
        confirmed_at=nomination.get("authoredOn"),
    )

    # --- summary: diagnoses, nomination notes, ECOG from doctor and patient ---
    summary = [
        rec(f"{c['code']['coding'][0]['code']} {c['code']['text']}" + stage(c), src(b, c))
        for c in onco
    ]
    # ECOG side by side: doctor's assessment and the patient's own description (brief, section A)
    ecog = [o for o in observations if code_of(o) == LOINC_ECOG]
    patient_ecog = answers(proms[-1]).get("samostatnost") if proms else None
    parts, ecog_sources = [], []
    if ecog:
        parts.append(f"lékař {ecog[-1]['valueInteger']}")
        ecog_sources.append(src(b, ecog[-1], observation_line(ecog[-1])))
    if patient_ecog:
        text, a = patient_ecog
        parts.append(f"pacient ≈ {a['valueCoding']['code']}")
        ecog_sources.append(src(b, proms[-1], answer_line(text, a), "samostatnost"))
    if parts:
        summary.append(rec("ECOG: " + " · ".join(parts), *ecog_sources))

    trends = build_trends(b, observations, proms)
    return Case(
        id=case_id,
        patient=f"Patient/{patient['id']}",
        label=label,
        tumour=TUMOURS.get(primary, primary or "unknown"),
        board=nomination["category"][0]["text"].removeprefix("Požadované zaměření MDT: "),
        mdt_date=mdt_date,
        question=question,
        summary=summary,
        timeline=build_timeline(b, onco, pathology, imaging, note("Předchozí onkologická léčba")),
        red_flags=red_flags(b, mdt_date, symptoms),
        sections=build_sections(b, conditions, observations, proms, pathology, imaging, note),
        decision_support=DecisionSupport(options=[], trials=[], questions=[]),
        trends=trends,
        previous_board=previous_board(b),
    )


def stage(c: dict) -> str:
    s = (c.get("stage") or [{}])[0].get("summary", {}).get("text")
    return f" · {s}" if s else ""


def build_timeline(b: Bundle, onco, pathology, imaging, history: Statement | None):
    ev: list[TimelineEvent] = []

    def add(kind: str, text: str, r: dict, excerpt: str | None = None):
        if d := date_of(r):
            ev.append(TimelineEvent(date=d, kind=kind, statement=rec(text, src(b, r, excerpt))))

    for c in onco:  # primary = diagnosis, secondary (C77–C79) = progression
        secondary = c["code"]["coding"][0]["code"][:3] in {"C77", "C78", "C79"}
        add("progression" if secondary else "diagnosis", c["code"]["text"], c, c["code"]["text"])
    for r in pathology:
        add("pathology", title_of(r), r, r["conclusion"])
    for r in imaging:
        add("imaging", title_of(r), r, r["conclusion"])
    for p in b.all("Procedure"):
        if category_text(p) == "chirurgický výkon":
            add("surgery", title_of(p), p, title_of(p))
    # Systemic lines and RT come from the nomination's treatment history: it has the real start
    # dates (the bundle's MedicationAdministrations only cover the latest doses).
    for line in history.text.splitlines() if history else []:
        m = TREATMENT_LINE.match(line.strip())
        if m and m["cat"] != "Chirurgie":
            kind = "radiotherapy" if m["cat"] == "Radioterapie" else "systemic"
            start = dt.date.fromisoformat(m["start"] + "-01"[: 10 - len(m["start"])])
            source = history.sources[0].model_copy(update={"excerpt": line.strip("- ")})
            ev.append(TimelineEvent(date=start, kind=kind, statement=rec(m["what"], source)))
    for comp in b.all("Composition"):
        if comp["type"]["coding"][0]["code"] == "mdt-zaznam":
            conclusion = section_text(comp, "Závěr MDT")
            add("mdt", f"MDT: {conclusion}", comp, conclusion)
    return sorted(ev, key=lambda e: e.date)


def build_sections(b: Bundle, conditions, observations, proms, pathology, imaging, note):
    def obs_items(pred) -> list[Statement]:
        latest: dict[str, dict] = {}
        for o in observations:  # sorted by date: last one wins per test
            if pred(o):
                latest[title_of(o)] = o
        return [rec(f"{t}: {value_of(o)}", src(b, o, value_of(o))) for t, o in latest.items()]

    def report_items(rs: list[dict]) -> list[Statement]:
        return [rec(f"{title_of(r)}: {r['conclusion']}", src(b, r, r["conclusion"])) for r in rs]

    treatment = note("Předchozí onkologická léčba")
    history = []
    if treatment:
        for line in treatment.text.splitlines()[1:]:
            line = line.removeprefix("- ").strip()
            if line:
                history.append(rec(line, treatment.sources[0].model_copy(update={"excerpt": line})))

    surgery = [s for s in (note("Relevantní komorbidity"),) if s]
    surgery += [
        rec(f"Komorbidita: {c['code']['text']}", src(b, c))
        for c in conditions
        if category_text(c) == "komorbidita"
    ]
    surgery += obs_items(
        lambda o: (
            category_text(o).split(" | ")[0]
            in {
                "Staging",
                "Funkční vyšetření plic",
                "Kardiologie",
                "Rizikové faktory",
                "vital-signs",
            }
        )
    )
    surgery += [
        rec(f"{t['title']}: {t['text']}", t["source"])
        for t in proms_items(b, proms, ("chuze", "hmotnost-zmena"))
    ]
    surgery += [
        rec(f"Výkon: {title_of(p)}", src(b, p))
        for p in b.all("Procedure")
        if category_text(p) == "chirurgický výkon"
    ]

    oncology = obs_items(lambda o: "Biomarker" in category_text(o))
    oncology += obs_items(lambda o: category_text(o).startswith("Toxicita"))
    oncology += [
        rec(f"Nežádoucí účinek: {c['code']['text']}", src(b, c))
        for c in conditions
        if category_text(c) == "nežádoucí účinek léčby"
    ]
    oncology += history

    patient = [
        rec(f"{PATIENT_LABELS[t['id']]}: {t['text']}", t["source"])
        for t in proms_items(b, proms, tuple(PATIENT_LABELS))
    ]
    if pref := note("Preference"):
        patient.append(pref)

    return [
        s
        for s in (
            Section(id="surgery", title="Chirurgie", items=surgery),
            Section(id="oncology", title="Klinická onkologie", items=oncology),
            Section(id="radiology", title="Radiologie", items=report_items(imaging[::-1])),
            Section(
                id="pathology",
                title="Patologie",
                items=[s for s in (note("Histologie"),) if s] + report_items(pathology[::-1]),
            ),
            Section(id="patient", title="Pacient", items=patient),
        )
        if s.items
    ]


def proms_items(b: Bundle, proms: list[dict], link_ids: tuple[str, ...]) -> list[dict]:
    if not proms:
        return []
    qr, out = proms[-1], []
    for link_id in link_ids:
        if link_id in (a := answers(qr)):
            text, ans = a[link_id]
            value = value_of(ans)
            out.append(
                {
                    "id": link_id,
                    "title": text,
                    "text": value,
                    "source": src(b, qr, answer_line(text, ans), link_id),
                }
            )
    return out


def build_trends(b: Bundle, observations, proms) -> list[Trend]:
    labs: dict[str, list[dict]] = {}
    for o in observations:
        if "valueQuantity" in o and code_of(o):
            labs.setdefault(code_of(o), []).append(o)

    def lab_trend(series: list[dict]) -> Trend:
        last = series[-1]
        rng = (last.get("referenceRange") or [{}])[0]
        return Trend(
            id=code_of(last),
            label=title_of(last),
            unit=last["valueQuantity"].get("unit", ""),
            ref_low=rng.get("low", {}).get("value"),
            ref_high=rng.get("high", {}).get("value"),
            points=[
                TrendPoint(
                    date=date_of(o),
                    value=o["valueQuantity"]["value"],
                    source=src(b, o, value_of(o)),
                )
                for o in series
            ],
        )

    def abnormal(t: Trend) -> bool:
        v = t.points[-1].value
        return (t.ref_low is not None and v < t.ref_low) or (
            t.ref_high is not None and v > t.ref_high
        )

    multi = {c: s for c, s in labs.items() if len(s) > 1}
    markers = [lab_trend(s) for c, s in multi.items() if c in LOINC_MARKERS]
    hb = [lab_trend(multi[LOINC_HB])] if LOINC_HB in multi else []
    others = [
        t
        for t in (lab_trend(s) for c, s in multi.items() if c not in LOINC_MARKERS | {LOINC_HB})
        if abnormal(t)
    ]
    proms_trends: list[Trend] = []
    if len(proms) > 1:
        series: dict[str, list[tuple[dict, str, int]]] = {}
        for qr in proms:
            for link_id, (text, a) in answers(qr).items():
                if "valueInteger" in a:
                    series.setdefault(link_id, []).append((qr, text, a["valueInteger"]))
        for link_id, pts in series.items():
            if link_id in PROMS_ALWAYS or max(v for _, _, v in pts) >= 5:
                label = short_label(pts[0][1])
                proms_trends.append(
                    Trend(
                        id=f"proms-{link_id}",
                        label=f"{label} (PROMs)",
                        unit="/10",
                        axis=(0, 10),
                        points=[
                            TrendPoint(
                                date=date_of(qr), value=v, source=src(b, qr, f"{t}: {v}", link_id)
                            )
                            for qr, t, v in pts
                        ],
                    )
                )
    # priority: tumour markers, Hb, the patient's fatigue/pain, then other abnormal labs and PROMs
    core = [t for t in proms_trends if t.id.removeprefix("proms-") in PROMS_ALWAYS]
    rest = [t for t in proms_trends if t not in core]
    trends = markers[:2] + hb + core + others + rest
    return trends[
        :6
    ]  # ponytail: fixed cap keeps the meeting slide calm; make it a board setting if needed
