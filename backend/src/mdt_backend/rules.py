"""Rule-based red flags (brief: "AI upozornění"), pravidla-v2. Machine-made, so origin "ai" — the
clinician confirms them. Rules are written against concepts (concepts.py), not against the
dataset's codes or wording, and every threshold, severity and guideline citation lives in the
declarative catalogue rules.toml (brief BONUS: configurable red-flag rules). Families:
A abnormal values (CTCAE grades) · B trends · C discordance between sources · D lab + symptom
corroboration · E drug monitoring · F alarm symptoms · G stale/missing data · H process/context.
Each flag cites the record resources it compares (both sides of a conflict) and the guideline
passage its threshold comes from."""

import datetime as dt
import re
import tomllib
from collections.abc import Callable
from functools import lru_cache
from itertools import pairwise
from pathlib import Path

from mdt_backend import concepts as C
from mdt_backend.briefing import RedFlag
from mdt_backend.bundles import Bundle, answers, short_label, src, title_of, value_of
from mdt_backend.config import settings
from mdt_backend.knowledge import guideline_source, guidelines
from mdt_backend.provenance import NOT_FOUND, Source, Statement

MODEL = "pravidla-v2"
CATALOGUE = Path(__file__).with_name("rules.toml")
RANK = {"high": 0, "medium": 1, "low": 2}


def _merge(a: dict, b: dict) -> dict:
    out = dict(a)
    for k, v in b.items():
        out[k] = _merge(a[k], v) if isinstance(v, dict) and isinstance(a.get(k), dict) else v
    return out


@lru_cache
def load_config(override: str | None = None) -> dict:
    """The catalogue, with an optional override file (argument or RULES_CONFIG) merged in."""
    cfg = tomllib.loads(CATALOGUE.read_text("utf-8"))
    path = override or settings.rules_config
    return _merge(cfg, tomllib.loads(Path(path).read_text("utf-8"))) if path else cfg


class Flags:
    """Collects flags; shared helpers for the rule functions below."""

    def __init__(self, f: C.Facts, cfg: dict):
        self.f, self.cfg = f, cfg
        self.out: list[RedFlag] = []
        self.used: set[str] = set()  # "lab:hb", "prom:unava", "sym:neuropathy" — said already

    def add(self, rule: str, severity: str, text: str, *sources: Source | None, guideline=None):
        refs = [s for s in sources if s] + self.guideline(guideline)
        refs = list({s.reference + (s.excerpt or ""): s for s in refs}.values())
        st = Statement(text=text, origin="ai", model=f"{MODEL}:{rule}", sources=refs)
        self.out.append(RedFlag(severity=severity, statement=st))

    def guideline(self, g) -> list[Source]:
        if isinstance(g, dict):
            primary = self.f.primary
            g = next((v for k, v in g.items() if k != "*" and primary.startswith(k)), g.get("*"))
        return [guideline_source(g)] if g and g in guidelines() else []

    def s(self, r: dict, excerpt: str | None = None, item: str | None = None) -> Source:
        return src(self.f.b, r, excerpt, item)

    def lab_src(self, lab: C.Lab) -> Source:
        return self.s(lab.r, value_of(lab.r))

    def prom_src(self, i: int, concept: str) -> Source | None:
        link_id, text, a = self.f.qa(i).get(concept, (None, None, None))
        return self.s(self.f.proms[i], f"{text}: {value_of(a)}", link_id) if link_id else None

    def severity_for_grade(self, g: int) -> str:
        sev = self.cfg["general"]["grade_severity"]
        return sev[min(g, len(sev) - 1)]

    def current(self, classes) -> list[C.Exposure]:
        return [e for cls in classes if (e := self.f.drugs.get(cls)) and e.current]

    def cause(self, concept: str) -> str:
        drugs = self.current(self.cfg.get("toxicity", {}).get(concept, []))
        names = sorted({n for e in drugs for n in e.names})
        return f" – možná souvislost s léčbou ({', '.join(names)})" if names else ""

    def score(self, concept: str, i: int = -1) -> int | None:
        a = self.f.qa(i).get(concept, (None, None, {}))[2]
        return a.get("valueInteger") if a else None

    def symptom(self, concepts: list[str], min_score: int) -> tuple[str, Source] | None:
        """Patient-side evidence: a 0–10 PROMs item ≥ min_score or a free-text symptom."""
        for c in concepts:
            score = self.score(c)
            if score is not None and score >= min_score:
                link_id, text, _ = self.f.qa()[c]
                label = f"{short_label(text).lower()} {score}/10"
                return label, self.s(self.f.proms[-1], f"{text}: {score}", link_id)
        for sym in self.f.symptoms:
            if sym.concept in concepts:
                return f"pacient uvádí „{_short(sym.excerpt)}“", self.s(
                    sym.r, sym.excerpt, sym.item
                )
        return None


def _short(text: str, n: int = 140) -> str:
    first = re.split(r"(?<=[^\d\s])\.\s", text.strip())[0].rstrip(".")
    return first if len(first) <= n else first[: n - 1] + "…"


def _days(a: dt.date | None, b: dt.date | None) -> int | None:
    return (b - a).days if a and b else None


# --- A: abnormal values ------------------------------------------------------------------------
def grade(lab: C.Lab, spec: dict) -> tuple[int, str]:
    """CTCAE-style grade and direction ("below"/"above") of one value."""
    g, d = 0, ""
    if lab.low is not None and lab.value < lab.low:
        g, d = 1, "below"
    if lab.high is not None and lab.value > lab.high:
        g, d = 1, "above"
    for key in ("below", "above", "above_x_uln"):
        cuts = spec.get(key) or []
        if key == "above_x_uln":
            n = sum(lab.value > t * lab.high for t in cuts) if lab.high is not None else 0
        elif key == "below":
            n = sum(lab.value < t for t in cuts)
        else:
            n = sum(lab.value > t for t in cuts)
        if n and 1 + n > g:
            g, d = 1 + n, "below" if key == "below" else "above"
    return g, d


def abnormal_lab(F: Flags, c: dict):
    mild = []
    for concept, spec in c["grades"].items():
        labs = F.f.labs.get(concept)
        if not labs:
            continue
        last = labs[-1]
        g, _ = grade(last, spec)
        if g == 0 or f"lab:{concept}" in F.used:
            continue
        if g == 1 and c.get("aggregate_grade1", True):
            mild.append(last)
            continue
        prev = labs[-2] if len(labs) > 1 else None
        before = f" (předtím {value_of(prev.r)})" if prev else ""
        F.add(
            "abnormal_lab",
            F.severity_for_grade(g),
            f"{last.label} {value_of(last.r)} – CTCAE stupeň {g}{before}{F.cause(concept)}.",
            F.lab_src(last),
            F.lab_src(prev) if prev else None,
            guideline=c.get("guideline", {}).get(concept),
        )
    if mild:
        items = ", ".join(
            f"{x.label} {value_of(x.r)} {'↓' if x.low is not None and x.value < x.low else '↑'}"
            for x in mild
        )
        F.add(
            "abnormal_lab",
            F.severity_for_grade(1),
            f"Mírně mimo referenční rozmezí: {items}.",
            *[F.lab_src(x) for x in mild],
        )


def threshold(F: Flags, rules: list[dict]):
    for t in rules:
        labs = F.f.labs.get(t["concept"])
        if not labs or labs[-1].value >= t["below"]:
            continue
        last = labs[-1]
        high = last.value < t.get("high_below", float("-inf"))
        F.add(
            "threshold",
            t.get("high_severity", "high") if high else t.get("severity", "medium"),
            f"{last.label} {value_of(last.r)} (< {t['below']:g} %) – {t['advice']}.",
            F.lab_src(last),
            guideline=t.get("guideline"),
        )


# --- B: trends ---------------------------------------------------------------------------------
def marker_rise(F: Flags, c: dict):
    for concept in sorted(C.MARKERS & F.f.labs.keys()):
        labs = F.f.labs[concept]
        if len(labs) < 2:
            continue
        prev, last = labs[-2], labs[-1]
        high = last.high
        if high is None or last.value <= high:
            continue
        if last.value >= prev.value * (1 + c["rise_pct"] / 100):
            F.add(
                "marker_rise",
                c["severity"],
                f"{last.label} roste: {prev.value:g} → {last.value:g} {last.unit} (norma do {high:g}).",
                F.lab_src(prev),
                F.lab_src(last),
                guideline=c.get("guideline"),
            )


def lab_change(F: Flags, c: dict):
    skip = C.MARKERS | {"ecog", "weight", "lvef"}
    for concept, labs in F.f.labs.items():
        spec = F.cfg.get("abnormal_lab", {}).get("grades", {}).get(concept, {})
        if concept in skip or len(labs) < 2 or grade(labs[-1], spec)[0] >= 2:
            continue
        prev, last = labs[-2], labs[-1]
        gap = _days(prev.date, last.date)
        outside = (last.low is not None and last.value < last.low) or (
            last.high is not None and last.value > last.high
        )
        if not prev.value or not outside or gap is None or gap > c["max_days"]:
            continue
        rel = (last.value - prev.value) / prev.value * 100
        if abs(rel) >= c["rel_pct"]:
            F.used.add(f"lab:{concept}")
            F.add(
                "lab_change",
                c["severity"],
                f"{last.label}: výrazná změna {value_of(prev.r)} → {value_of(last.r)} "
                f"({rel:+.0f} % za {gap} dní){F.cause(concept)}.",
                F.lab_src(prev),
                F.lab_src(last),
            )


def weight_loss(F: Flags, c: dict):
    points = [(x.date, x.value, F.lab_src(x)) for x in F.f.labs.get("weight", []) if x.date]
    for i, qr in enumerate(F.f.proms):
        a = F.f.qa(i).get("weight")
        if a and (v := C.num(value_of(a[2]))) and (day := C.date_of(qr)):
            points.append((day, v, F.prom_src(i, "weight")))
    points.sort(key=lambda p: p[0])
    if points:
        last = points[-1]
        window = [p for p in points if 0 < (last[0] - p[0]).days <= c["window_days"]]
        if window:
            top = max(window, key=lambda p: p[1])
            pct = (top[1] - last[1]) / top[1] * 100
            if pct >= c["medium_pct"]:
                sev = "high" if pct >= c["high_pct"] else "medium"
                F.add(
                    "weight_loss",
                    sev,
                    f"Úbytek hmotnosti {pct:.0f} % ({top[1]:g} → {last[1]:g} kg za "
                    f"{(last[0] - top[0]).days} dní) – nutriční screening a intervence.",
                    top[2],
                    last[2],
                    guideline=c.get("guideline"),
                )
                F.used.add("sym:weight_loss")
                return
    # only the patient's own estimate of the change is available
    change, weight = F.f.qa().get("weight_change"), F.f.qa().get("weight")
    if change and weight:
        delta, w = C.num(value_of(change[2])), C.num(value_of(weight[2]))
        if delta and w and value_of(change[2]).strip().startswith("-"):
            pct = delta / (w + delta) * 100
            if pct >= c["medium_pct"]:
                F.add(
                    "weight_loss",
                    "high" if pct >= c["high_pct"] else "medium",
                    f"Pacient uvádí úbytek {delta:g} kg ({pct:.0f} %) – nutriční screening.",
                    F.prom_src(-1, "weight_change"),
                    F.prom_src(-1, "weight"),
                    guideline=c.get("guideline"),
                )
                F.used.add("sym:weight_loss")


def _integers(qr: dict) -> dict[str, tuple[str, int]]:
    return {k: (t, a["valueInteger"]) for k, (t, a) in answers(qr).items() if "valueInteger" in a}


def proms_worsening(F: Flags, c: dict):
    if len(F.f.proms) < 2:
        return
    before, now = _integers(F.f.proms[-2]), _integers(F.f.proms[-1])
    worse = [
        (k, t, before[k][1], v)
        for k, (t, v) in now.items()
        if k in before and v - before[k][1] >= c["points"]
    ]
    if worse:
        F.used |= {f"prom:{k}" for k, *_ in worse}
        items = ", ".join(f"{short_label(t).lower()} {x}→{y}" for _, t, x, y in worse)
        F.add(
            "proms_worsening",
            c["severity"],
            f"Zhoršení v dotazníku pacienta: {items} (škála 0–10).",
            F.s(F.f.proms[-2], "; ".join(f"{t}: {x}" for _, t, x, _ in worse)),
            F.s(F.f.proms[-1], "; ".join(f"{t}: {y}" for _, t, _, y in worse)),
        )


def symptom_burden(F: Flags, c: dict):
    if not F.f.proms:
        return
    qr = F.f.proms[-1]
    heavy = [
        (k, t, v)
        for k, (t, v) in _integers(qr).items()
        if v >= c["min_score"] and f"prom:{k}" not in F.used
    ]
    if not heavy:
        return
    advice = c.get("advice", {})
    tips = []
    for k, t, _ in heavy:
        tip = advice.get(C.prom_concept(k, t) or "")
        tips += [tip] if tip and tip not in tips else []
    items = ", ".join(f"{short_label(t).lower()} {v}/10" for _, t, v in heavy)
    F.add(
        "symptom_burden",
        c["severity"],
        f"Výrazná symptomová zátěž dle pacienta: {items}"
        + (f" – {'; '.join(tips)}." if tips else "."),
        F.s(qr, "; ".join(f"{t}: {v}" for _, t, v in heavy)),
        guideline=c.get("guideline"),
    )


def ecog_change(F: Flags, c: dict):
    ecog = F.f.labs.get("ecog", [])
    if len(ecog) < 2 or ecog[-1].value <= ecog[-2].value:
        return
    diff = ecog[-1].value - ecog[-2].value
    F.add(
        "ecog_change",
        c["high_severity"] if diff >= c["high_points"] else c["severity"],
        f"Zhoršení výkonnostního stavu dle lékaře: ECOG {ecog[-2].value:g} → {ecog[-1].value:g}.",
        F.lab_src(ecog[-2]),
        F.lab_src(ecog[-1]),
        guideline=c.get("guideline"),
    )


# --- C: discordance ------------------------------------------------------------------------------
def ecog_discordance(F: Flags, c: dict):
    ecog = F.f.labs.get("ecog")
    own = F.f.qa().get("self_care")
    if not ecog or not own or not F.f.proms:
        return
    code = (own[2].get("valueCoding") or {}).get("code", "")
    if not code.isdigit():
        return
    gap = abs(_days(ecog[-1].date, C.date_of(F.f.proms[-1])) or 0)
    doc, pat = int(ecog[-1].value), int(code)
    if gap > c["max_gap_days"] or pat - doc < c["medium_diff"]:
        return
    F.add(
        "ecog_discordance",
        "high" if pat - doc >= c["high_diff"] else "medium",
        f"ECOG dle lékaře {doc}, pacient popisuje stav odpovídající ECOG {pat} – ověřit výkonnostní stav.",
        F.s(ecog[-1].r, f"ECOG {doc}"),
        F.s(F.f.proms[-1], f"{own[1]} {value_of(own[2])}", own[0]),
        guideline=c.get("guideline"),
    )


TNM_PART = {
    "T": re.compile(r"(?<![A-Za-z])([cpy]{0,2})T([0-4][a-d]?|is|x)(?![a-z])"),
    "N": re.compile(r"(?<![A-Za-z])[cpy]{0,2}N([0-3][a-c]?|x)(?![a-z])"),
    "M": re.compile(r"(?<![A-Za-z])[cpy]{0,2}M([01][a-c]?)(?![a-z])"),
    "stage": re.compile(r"stadium\s+([IV]+[ABC]?)"),
}


def tnm(text: str) -> dict[str, str]:
    out = {k: m.group(m.lastindex) for k, rx in TNM_PART.items() if (m := rx.search(text))}
    t = TNM_PART["T"].search(text)
    out["kind"] = "p" if (t and "p" in t.group(1)) or "patolog" in text else "c"
    return out


def tnm_discordance(F: Flags, c: dict):
    obs = F.f.texts.get("tnm", [])
    for a, b in pairwise(obs):
        ta, tb = tnm(title_of(a) + " " + value_of(a)), tnm(title_of(b) + " " + value_of(b))
        gap = _days(C.date_of(a), C.date_of(b))
        if ta["kind"] != tb["kind"] or gap is None or gap > c["window_days"]:
            continue
        differ = [k for k in ("T", "N") if k in ta and k in tb and ta[k] != tb[k]]
        if ta.get("M") == tb.get("M") and "stage" in ta and "stage" in tb:
            differ += ["stadium"] if ta["stage"] != tb["stage"] else []
        if differ:
            F.add(
                "tnm_discordance",
                c["severity"],
                f"Nesoulad stagingu ({', '.join(differ)}): „{value_of(a)}“ ({C.date_of(a)}) vs. "
                f"„{value_of(b)}“ ({C.date_of(b)}) – ověřit platné TNM.",
                F.s(a, value_of(a)),
                F.s(b, value_of(b)),
                guideline=c.get("guideline"),
            )


RECEPTORS = {"ER": r"^ER\b|estrogen", "PR": r"^PR\b|progesteron", "HER2": r"HER2"}


def receptor_status(name: str, value: str) -> str | None:
    v = value.lower()
    if C.NOT_DONE.search(v):
        return None
    if name == "HER2":
        if re.search(r"3\+|amplif", v) or (re.search(r"pozitiv", v) and "low" not in v):
            return "HER2 pozitivní"
        if re.search(r"[12]\+|low", v):
            return "HER2-low"
        return "HER2 0" if re.search(r"\b0\b|negativ", v) else None
    if "negativ" in v or re.match(r"^\D*0\s*%", v):
        return "negativní"
    return "pozitivní" if "pozitiv" in v or re.search(r"[1-9]\d*\s*%", v) else None


def receptors(F: Flags) -> dict[str, list[tuple[dict, str]]]:
    out: dict[str, list[tuple[dict, str]]] = {}
    for name, rx in RECEPTORS.items():  # fixed order, whatever order the server returns
        for o in F.f.biomarkers:
            if re.search(rx, title_of(o), re.IGNORECASE) and (
                st := receptor_status(name, value_of(o))
            ):
                out.setdefault(name, []).append((o, st))
    return out


def receptor_discordance(F: Flags, c: dict):
    changed = {n: v for n, v in receptors(F).items() if len({st for _, st in v}) > 1}
    if not changed:
        return
    parts, sources = [], []
    for name, values in changed.items():
        parts.append(
            f"{name}: "
            + " → ".join(f"{value_of(o)} ({title_of(o)}, {C.date_of(o)})" for o, _ in values)
        )
        sources += [F.s(o, value_of(o)) for o, _ in values]
    F.add(
        "receptor_discordance",
        c["severity"],
        "Receptorový stav se mezi vzorky liší – "
        + "; ".join(parts)
        + ". Pro léčbu rozhoduje nejaktuálnější relevantní vzorek.",
        *sources,
        guideline=c.get("guideline"),
    )


def toxicity_discordance(F: Flags, c: dict):
    grades = load_config_grades(F)
    for key, obs in F.f.texts.items():
        if not key.startswith("ctcae_") or not obs:
            continue
        concept, o = key.removeprefix("ctcae_"), obs[-1]
        doc = C.grade_of(value_of(o))
        if doc is None or f"sym:{concept}" in F.used:
            continue
        if concept == "neuropathy":
            ev = F.symptom(["neuropathy_functional"], 99) or F.symptom(
                ["neuropathy"], c["patient_score"]
            )
            if doc <= 1 and ev:
                F.add(
                    "toxicity_discordance",
                    c["severity"],
                    f"Neuropatie: lékař CTCAE stupeň {doc}, {ev[0]} – ověřit stupeň toxicity.",
                    F.s(o, value_of(o)),
                    ev[1],
                    guideline=c.get("guideline"),
                )
            continue
        labs = [
            x
            for x in F.f.labs.get(concept, [])
            if abs(_days(x.date, C.date_of(o)) or 999) <= c["lab_window_days"]
        ]
        if labs and concept in grades:
            lab_grade, _ = grade(labs[-1], grades[concept])
            if lab_grade != doc:
                F.add(
                    "toxicity_discordance",
                    c["severity"],
                    f"{title_of(o)}: lékař stupeň {doc}, laboratorně {labs[-1].label} "
                    f"{value_of(labs[-1].r)} odpovídá stupni {lab_grade}.",
                    F.s(o, value_of(o)),
                    F.lab_src(labs[-1]),
                )


def load_config_grades(F: Flags) -> dict:
    return F.cfg.get("abnormal_lab", {}).get("grades", {})


def weight_discordance(F: Flags, c: dict):
    measured = F.f.labs.get("weight", [])
    reported = F.f.qa().get("weight")
    if not measured or not reported:
        return
    w = C.num(value_of(reported[2]))
    day = C.date_of(F.f.proms[-1])
    near = [x for x in measured if abs(_days(x.date, day) or 999) <= c["max_gap_days"]]
    if w and near and abs(near[-1].value - w) > c["max_diff_kg"]:
        F.add(
            "weight_discordance",
            c["severity"],
            f"Hmotnost dle pacienta {w:g} kg, změřeno {value_of(near[-1].r)} – ověřit.",
            F.prom_src(-1, "weight"),
            F.lab_src(near[-1]),
        )


def allergy_record(F: Flags, c: dict):
    own = F.f.qa().get("allergy")
    if not own or F.f.b.all("AllergyIntolerance"):
        return
    answer = value_of(own[2]).strip()
    if answer and not C.NEGATIVE.match(answer):
        F.add(
            "allergy_record",
            c["severity"],
            f"Pacient uvádí nesnášenlivost „{_short(answer)}“; záznam o alergii: {NOT_FOUND}",
            F.prom_src(-1, "allergy"),
        )


def otc_interaction(F: Flags, c: dict):
    own = F.f.qa().get("otc")
    drugs = F.current(C.SYSTEMIC)
    if not own or not drugs:
        return
    answer = value_of(own[2]).strip()
    if not answer or C.NEGATIVE.match(answer):
        return
    risky = re.search(c["high_risk"], answer, re.IGNORECASE)
    names = ", ".join(sorted({n for e in drugs for n in e.names}))
    F.add(
        "otc_interaction",
        c["high_severity"] if risky else c["severity"],
        f"Pacient užívá mimo předpis „{_short(answer)}“ při léčbě {names} – ověřit lékové interakce.",
        F.prom_src(-1, "otc"),
        F.s(drugs[0].r),
    )


# --- D: corroboration ----------------------------------------------------------------------------
def corroborated(F: Flags, rules: list[dict]):
    for r in rules:
        labs = F.f.labs.get(r["lab"])
        if not labs:
            continue
        last = labs[-1]
        below = r["direction"] == "below"
        if below and not (last.low is not None and last.value < last.low):
            continue
        if not below and not (last.high is not None and last.value > last.high):
            continue
        ev = F.symptom(r["symptoms"], r.get("min_score", 1))
        if not ev:
            continue
        F.used.add(f"lab:{r['lab']}")
        g, _ = grade(last, F.cfg.get("abnormal_lab", {}).get("grades", {}).get(r["lab"], {}))
        F.add(
            "corroborated",
            r["severity"],
            f"{last.label} {value_of(last.r)} {'pod' if below else 'nad'} normou"
            + (f" (CTCAE stupeň {g})" if g >= 2 else "")
            + f" a {ev[0]} – "
            f"{r['advice']}{F.cause(r['lab'])}.",
            F.lab_src(last),
            ev[1],
            guideline=r.get("guideline"),
        )


# --- E: drug monitoring --------------------------------------------------------------------------
def monitoring(F: Flags, rules: list[dict]):
    for r in rules:
        e = F.f.drugs.get(r["drug"])
        if not e or not e.current:
            continue
        missing = []
        for concept in r.get("concepts", []):
            labs = F.f.labs.get(concept, [])
            if not labs or (_days(labs[-1].date, F.f.mdt) or 0) > r["within_days"]:
                missing.append(C.LABELS.get(concept, concept))
        if "biomarker" in r:
            hits = [
                o
                for o in F.f.biomarkers + F.f.texts.get("other", [])
                if re.search(r["biomarker"], title_of(o))
            ]
            if not hits or C.NOT_DONE.search(value_of(hits[-1])):
                missing.append(r["biomarker"].split("|")[-1])
        if missing:
            window = f" (za posledních {r['within_days']} dní)" if "within_days" in r else ""
            F.add(
                "monitoring",
                r["severity"],
                f"Monitorace při léčbě {', '.join(e.names)}: {', '.join(missing)}{window} – {NOT_FOUND}",
                F.s(e.r),
                guideline=r.get("guideline"),
            )


def lvef_drop(F: Flags, c: dict):
    lvef = F.f.labs.get("lvef", [])
    if not lvef:
        return
    base, last = lvef[0], lvef[-1]
    drop = base.value - last.value
    if drop < c["drop_points"] and last.value >= c["floor"]:
        return
    ev = F.symptom(c["symptoms"], c["min_score"])
    severe = last.value < c["floor"] or ev is not None
    text = (
        f"LVEF {base.value:g} → {last.value:g} % (pokles o {drop:g} b.)"
        if drop > 0
        else (f"LVEF {last.value:g} %")
    )
    F.add(
        "lvef_drop",
        c["high_severity"] if severe else c["severity"],
        text + (f", {ev[0]}" if ev else "") + F.cause("lvef") + " – kardiologické zhodnocení.",
        F.lab_src(base) if drop > 0 else None,
        F.lab_src(last),
        ev[1] if ev else None,
        guideline=c.get("guideline"),
    )


def neurotoxicity(F: Flags, c: dict):
    exposures = [e for cls in c["drugs"] if (e := F.f.drugs.get(cls))]
    if not exposures:
        return
    obs = F.f.texts.get("ctcae_neuropathy", [])
    doc = C.grade_of(value_of(obs[-1])) if obs else None
    ev = F.symptom(["neuropathy_functional"], 99) or F.symptom(["neuropathy"], c["patient_score"])
    if not ((doc or 0) >= c["min_grade"] or ev):
        return
    names = sorted({n for e in exposures for n in e.names})
    parts = ([f"lékař CTCAE stupeň {doc}"] if doc is not None else []) + ([ev[0]] if ev else [])
    differs = doc is not None and doc < c["min_grade"] and ev is not None
    F.used |= {"sym:neuropathy", "sym:neuropathy_functional"}
    F.add(
        "neurotoxicity",
        c["current_severity"] if any(e.current for e in exposures) else c["severity"],
        f"Neurotoxicita při léčbě {', '.join(names)}: {', '.join(parts)}"
        + (" – hodnocení lékaře a pacienta se liší" if differs else "")
        + " – zvážit přerušení nebo úpravu neurotoxické léčby.",
        F.s(obs[-1], value_of(obs[-1])) if obs else None,
        ev[1] if ev else None,
        F.s(exposures[0].r),
        guideline=c.get("guideline"),
    )


def surgery_washout(F: Flags, c: dict):
    e = F.f.drugs.get(c["drug"])
    if not e or not e.last:
        return
    asked = " ".join(
        [
            rc.get("text", "")
            for sr in F.f.b.all("ServiceRequest")
            for rc in sr.get("reasonCode", [])
        ]
        + [cp.get("description", "") for cp in F.f.b.all("CarePlan")]
    )
    gap = _days(e.last, F.f.mdt)
    if gap is None or gap >= c["days"] or not re.search(c["surgery"], asked, re.IGNORECASE):
        return
    earliest = e.last + dt.timedelta(days=c["days"])
    F.add(
        "surgery_washout",
        c["severity"],
        f"{', '.join(e.names)} naposledy {e.last} ({gap} dní před MDT) a zvažuje se operace – "
        f"operace nejdříve {earliest}.",
        F.s(e.r),
        guideline=c.get("guideline"),
    )


# --- F: alarm symptoms ---------------------------------------------------------------------------
def alarms(F: Flags, rules: list[dict]):
    c = F.cfg.get("new_symptom", {})
    groups: dict[tuple[str, str | None], list[C.Symptom]] = {}
    for s in F.f.symptoms:
        if s.new:
            groups.setdefault((f"{s.r['resourceType']}/{s.r['id']}", s.item), []).append(s)
    said: set[str] = set()
    # the dedicated "new symptoms" answer first; a pain site repeating it adds nothing
    for key in sorted(groups, key=lambda k: 0 if k[1] and "obtiz" in k[1] else 1):
        syms = groups[key]
        found = {s.concept for s in syms} - {u[4:] for u in F.used if u.startswith("sym:")}
        if not found or found <= said:
            continue
        said |= found
        sev, tips, gl = "low", [], None
        for r in rules:
            hit = found & set(r["symptoms"])
            if not hit or not set(r.get("with", [])) <= found:
                continue
            if r.get("drugs") and not F.current(r["drugs"]):
                continue
            s = r["severity"]
            if r.get("escalate_icd") and any(F.f.icd(r["escalate_icd"])):
                s = "high"
            sev = min(sev, s, key=RANK.get)
            tips += [r["advice"]] if r["advice"] not in tips else []
            gl = gl or r.get("guideline")
        if not tips:
            if not c.get("enabled", True):
                continue
            sev, tips = c["severity"], [c["advice"]]
        F.add(
            "alarm",
            sev,
            f"Nová obtíž hlášená pacientem: „{_short(syms[0].excerpt)}“ – {'; '.join(tips)}.",
            F.s(syms[0].r, syms[0].excerpt, syms[0].item),
            guideline=gl,
        )
    # a "new symptoms" answer that nothing could classify still deserves a look
    own = F.f.qa().get("new_symptoms")
    if own and c.get("enabled", True) and not any(k[1] == own[0] for k in groups):
        answer = value_of(own[2]).strip()
        if answer and not C.NEGATIVE.match(answer):
            F.add(
                "alarm",
                c["severity"],
                f"Nová obtíž hlášená pacientem: „{_short(answer)}“ – {c['advice']}.",
                F.s(F.f.proms[-1], answer, own[0]),
            )


# --- G: stale or missing data --------------------------------------------------------------------
def stale(F: Flags, c: dict):
    f = F.f
    if f.imaging:
        last = f.imaging[-1]
        days = _days(C.date_of(last), f.mdt)
        if days is not None and days > c["imaging_days"]:
            F.add(
                "stale",
                c["severity"],
                f"Poslední zobrazení ({title_of(last)}, {C.date_of(last)}) je starší než "
                f"{c['imaging_days'] // 7} týdnů před MDT ({days} dní).",
                F.s(last, last.get("conclusion")),
                guideline=c.get("guideline"),
            )
    old, sources = [], []
    blood = [x for k, v in f.labs.items() if k in C.LABS and k not in ("ecog", "weight") for x in v]
    for label, items, limit in (
        ("laboratoř", [x for x in blood if x.date], c["labs_days"]),
        ("ECOG", f.labs.get("ecog", []), c["ecog_days"]),
    ):
        if items:
            last = max(items, key=lambda x: x.date or dt.date.min)
            if (days := _days(last.date, f.mdt)) is not None and days > limit:
                old.append(f"{label} {last.date} ({days} dní)")
                sources.append(F.lab_src(last))
    if f.proms and (days := _days(C.date_of(f.proms[-1]), f.mdt)) and days > c["proms_days"]:
        old.append(f"dotazník pacienta {C.date_of(f.proms[-1])} ({days} dní)")
        sources.append(F.s(f.proms[-1]))
    if old:
        F.add("stale", c["severity"], f"Starší podklady k datu MDT: {', '.join(old)}.", *sources)


def _hr_her2(F: Flags) -> tuple[bool, bool]:
    r = receptors(F)
    er = r.get("ER", [])
    her2 = r.get("HER2", [])
    hr_pos = bool(er) and er[-1][1] == "pozitivní"
    her2_neg = bool(her2) and her2[-1][1] != "HER2 pozitivní"
    return hr_pos, her2_neg


def required(F: Flags, rules: list[dict]):
    hr_pos, her2_neg = _hr_her2(F)
    state = {"metastatic": F.f.metastatic, "hr_positive": hr_pos, "her2_negative": her2_neg}
    pool = F.f.biomarkers + F.f.texts.get("other", [])
    for r in rules:
        if not re.match(r["tumour"], F.f.primary) or not all(state[w] for w in r["when"]):
            continue
        gaps, absent, sources = [], [], []
        for name, rx in r["markers"].items():
            hits = [o for o in pool if re.search(rx, title_of(o), re.IGNORECASE)]
            if not hits:
                absent.append(name)
            elif C.NOT_DONE.search(value_of(hits[-1])):
                gaps.append(f"{name}: {_short(value_of(hits[-1]), 80)}")
                sources.append(F.s(hits[-1], value_of(hits[-1])))
        if absent:  # last, so a flag without record sources still ends with NOT_FOUND
            gaps.append(f"{', '.join(absent)}: {NOT_FOUND}")
        if gaps:
            text = f"Neúplné podklady – {r['name']}: " + "; ".join(gaps)
            F.add("required", r["severity"], text, *sources, guideline=r.get("guideline"))


# --- H: process and context ----------------------------------------------------------------------
def unfulfilled(F: Flags, c: dict):
    for o in [o for v in F.f.texts.values() for o in v] + F.f.biomarkers:
        if re.search(c["pattern"], value_of(o), re.IGNORECASE):
            F.add(
                "unfulfilled",
                c["severity"],
                f"Doporučený krok neproběhl: {title_of(o)} – „{_short(value_of(o))}“.",
                F.s(o, value_of(o)),
            )


def preference_missing(F: Flags, c: dict):
    notes = [n["text"] for sr in F.f.b.all("ServiceRequest") for n in sr.get("note", [])]
    stated = any(n.startswith("Preference") for n in notes) or any(
        value_of(F.f.qa().get(k, ("", "", {}))[2]).strip() for k in ("priority", "wishes")
    )
    if not stated:
        sr = F.f.b.all("ServiceRequest")
        F.add(
            "preference_missing",
            c["severity"],
            f"Preference pacienta: {NOT_FOUND}",
            F.s(sr[0]) if sr else None,
        )


def geriatric(F: Flags, c: dict):
    if F.f.age is None or F.f.age < c["min_age"] or F.f.texts.get("geriatric"):
        return
    patient = F.f.b.all("Patient")[0]
    F.add(
        "geriatric",
        c["severity"],
        f"Věk {F.f.age} let – screening křehkosti (G8): {NOT_FOUND}",
        F.s(patient, f"věk {F.f.age}"),
        guideline=c.get("guideline"),
    )


def second_tumour(F: Flags, c: dict):
    primaries = {}
    for cond in F.f.conditions:
        code = C.icd_of(cond)
        if re.match(r"^(C(?!7[7-9])|D(3[7-9]|4[0-8]))", code):
            primaries.setdefault(code[:3], cond)
    if len(primaries) > 1:
        F.add(
            "second_tumour",
            c["severity"],
            "Více primárních nebo nejasných novotvarů: "
            + ", ".join(f"{C.icd_of(x)} {title_of(x)}" for x in primaries.values())
            + " – ověřit histologicky a stanovit prioritu léčby.",
            *[F.s(x) for x in primaries.values()],
            guideline=c.get("guideline"),
        )


def smoking(F: Flags, c: dict):
    obs = F.f.texts.get("smoking", [])
    if obs and re.search(c["pattern"], value_of(obs[-1]), re.IGNORECASE):
        F.add(
            "smoking",
            c["severity"],
            f"{title_of(obs[-1])}: {value_of(obs[-1])} – intervence k odvykání kouření.",
            F.s(obs[-1], value_of(obs[-1])),
            guideline=c.get("guideline"),
        )


def comorbidity_drug(F: Flags, rules: list[dict]):
    for r in rules:
        conds, drugs = F.f.icd(r["icd"]), F.current(r["drugs"])
        if not conds or not drugs:
            continue
        names = sorted({n for e in drugs for n in e.names})
        F.add(
            "comorbidity_drug",
            r["severity"],
            f"{', '.join(title_of(x) for x in conds)} + {', '.join(names)}: {r['advice']}.",
            *[F.s(x) for x in conds],
            F.s(drugs[0].r),
            guideline=r.get("guideline"),
        )


# Order matters where a rule claims evidence another would repeat (F.used).
RULES: list[tuple[str, Callable]] = [
    ("corroborated", corroborated),
    ("neurotoxicity", neurotoxicity),
    ("lvef_drop", lvef_drop),
    ("lab_change", lab_change),
    ("abnormal_lab", abnormal_lab),
    ("threshold", threshold),
    ("marker_rise", marker_rise),
    ("weight_loss", weight_loss),
    ("proms_worsening", proms_worsening),
    ("symptom_burden", symptom_burden),
    ("ecog_change", ecog_change),
    ("ecog_discordance", ecog_discordance),
    ("tnm_discordance", tnm_discordance),
    ("receptor_discordance", receptor_discordance),
    ("toxicity_discordance", toxicity_discordance),
    ("weight_discordance", weight_discordance),
    ("allergy_record", allergy_record),
    ("otc_interaction", otc_interaction),
    ("monitoring", monitoring),
    ("surgery_washout", surgery_washout),
    ("alarm", alarms),
    ("stale", stale),
    ("required", required),
    ("unfulfilled", unfulfilled),
    ("preference_missing", preference_missing),
    ("geriatric", geriatric),
    ("second_tumour", second_tumour),
    ("smoking", smoking),
    ("comorbidity_drug", comorbidity_drug),
]


def red_flags(
    b: Bundle,
    mdt: dt.date | None,
    symptoms: list[C.Symptom] | None = None,
    config: dict | None = None,
) -> list[RedFlag]:
    """All enabled rules over one bundle. `symptoms` = free-text symptoms already classified
    (the agent's LLM classifier); None = the offline keyword classifier."""
    cfg = config or load_config()
    F = Flags(C.facts(b, mdt, symptoms), cfg)
    for name, rule in RULES:
        c = cfg.get(name)
        if c is None or (isinstance(c, dict) and not c.get("enabled", True)):
            continue
        rule(F, c)
    seen, out = set(), []
    for flag in sorted(F.out, key=lambda x: RANK[x.severity]):
        if flag.statement.text not in seen:
            seen.add(flag.statement.text)
            out.append(flag)
    return out
