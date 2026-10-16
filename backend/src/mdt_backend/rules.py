"""Rule-based red flags (brief: "AI upozornění"). Machine-made, so origin "ai" — the clinician
confirms them. ponytail: a handful of fixed rules and thresholds; move thresholds to the board
template (brief BONUS: red-flag rules configuration) when someone needs to tune them."""

import datetime as dt

from mdt_backend.briefing import Trend
from mdt_backend.bundles import (
    LOINC_ECOG,
    LOINC_HB,
    Bundle,
    answers,
    code_of,
    date_of,
    short_label,
    src,
    title_of,
    value_of,
)
from mdt_backend.provenance import Source, Statement

MODEL = "pravidla-v1"
STALE_IMAGING_DAYS = 42  # brief: "staging starší než 6 týdnů"


def red_flags(
    b: Bundle,
    observations,
    proms,
    imaging,
    trends: list[Trend],
    markers: set[str],
    mdt: dt.date | None,
) -> list[dict]:
    flags: list[dict] = []

    def flag(severity: str, text: str, *sources: Source):
        flags.append(
            {
                "severity": severity,
                "statement": Statement(text=text, origin="ai", model=MODEL, sources=list(sources)),
            }
        )

    latest_qr = proms[-1] if proms else None
    qa = answers(latest_qr) if latest_qr else {}

    # 1. ECOG: doctor vs patient (brief: a marked difference is automatically a red flag)
    ecog = [o for o in observations if code_of(o) == LOINC_ECOG]
    if ecog and "samostatnost" in qa:
        doc, (text, a) = ecog[-1]["valueInteger"], qa["samostatnost"]
        pat = int(a["valueCoding"]["code"])
        if pat - doc >= 1:
            flag(
                "high" if pat - doc >= 2 else "medium",
                f"ECOG dle lékaře {doc}, pacient popisuje stav odpovídající ECOG {pat} – ověřit výkonnostní stav.",
                src(b, ecog[-1], f"ECOG {doc}"),
                src(b, latest_qr, f"{text} {value_of(a)}", "samostatnost"),
            )

    # 2. Anaemia + fatigue (brief's own example)
    hb = [o for o in observations if code_of(o) == LOINC_HB]
    if hb and "unava" in qa:
        o, (text, a) = hb[-1], qa["unava"]
        low = ((o.get("referenceRange") or [{}])[0].get("low") or {}).get("value")
        if low is not None and o["valueQuantity"]["value"] < low and a["valueInteger"] >= 6:
            flag(
                "high",
                f"Hemoglobin {value_of(o)} pod normou a únava {a['valueInteger']}/10 – zvážit příčinu a léčbu anémie.",
                src(b, o, value_of(o)),
                src(b, latest_qr, f"{text}: {a['valueInteger']}", "unava"),
            )

    # 3. Rising tumour marker above the reference range
    for t in trends:
        if t.id not in markers or len(t.points) < 2 or t.ref_high is None:
            continue
        prev, last = t.points[-2], t.points[-1]
        if last.value > t.ref_high and last.value > prev.value * 1.2:
            flag(
                "medium",
                f"{t.label} roste: {prev.value:g} → {last.value:g} {t.unit} (norma do {t.ref_high:g}).",
                prev.source,
                last.source,
            )

    # 4. PROMs getting worse between the last two questionnaires
    if len(proms) > 1:
        before = answers(proms[-2])
        worse = [
            (link_id, text, before[link_id][1]["valueInteger"], a["valueInteger"])
            for link_id, (text, a) in qa.items()
            if "valueInteger" in a
            and link_id in before
            and a["valueInteger"] - before[link_id][1]["valueInteger"] >= 3
        ]
        if worse:
            items = ", ".join(f"{short_label(t).lower()} {x}→{y}" for _, t, x, y in worse)
            flag(
                "medium",
                f"Zhoršení v dotazníku pacienta: {items} (škála 0–10).",
                src(b, proms[-2], "; ".join(f"{t}: {x}" for _, t, x, _ in worse)),
                src(b, latest_qr, "; ".join(f"{t}: {y}" for _, t, _, y in worse)),
            )

    # 5. New symptom reported by the patient
    if "nove-obtize" in qa:
        text, a = qa["nove-obtize"]
        answer = value_of(a).strip()
        if answer and not answer.lower().startswith("ne"):
            flag(
                "medium",
                f"Nová obtíž hlášená pacientem: „{answer.split('. ')[0].rstrip('.')}“ – ověřit, zda byla vyšetřena.",
                src(b, latest_qr, answer, "nove-obtize"),
            )

    # 6. Imaging older than 6 weeks before the planned meeting
    if imaging and mdt:
        last = imaging[-1]
        if (mdt - (date_of(last) or mdt)) > dt.timedelta(days=STALE_IMAGING_DAYS):
            flag(
                "low",
                f"Poslední zobrazení ({title_of(last)}) je starší než 6 týdnů před MDT.",
                src(b, last, last.get("conclusion")),
            )
    return flags
