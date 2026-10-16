"""MDT agent: guideline-grounded AI layer on top of the deterministic briefing (from_fhir.py).

Pipeline (a fixed chain of tool steps and strict-JSON LLM calls, decision #16):
  1. gather      – the patient's record from the IRIS FHIR server only (Patient/$everything;
                   ids mapped back to the dataset's via the loader's tag), or, for offline
                   tests, from the bundle on disk (`source="file"`)
  2. diagnosis   – primary ICD-10 code → the tumour's guideline (KRC/PLI/PRS) + general MDT rules (OBC)
  3. CACC        – LLM: completeness-and-consistency checklist (decision prerequisites the record
                   should contain, symptoms expected for the diagnosis), each item tied to passages
  4. findings    – LLM: record × CACC → missing data and inconsistencies, ranked RED / YELLOW
  5. specialists – per radiology / surgery / oncology: LLM picks the relevant records, the agent
                   fetches them (from IRIS), LLM writes the specialist's view citing passages
  6. recommend   – LLM: 1–2 treatment options strictly from the guidelines, mentioning (not
                   following) the patient's preference, plus open questions for the board

Every citation the model returns is checked before it reaches a Statement: passage ids must be in
the guidelines allowed for the diagnosis, record references must exist in the patient's record and
quoted excerpts must appear verbatim in that record. Anything else is dropped and logged in the
trace. Output is the app's own `Case` (AI statements appended), so the frontend needs no changes."""

import argparse
import datetime as dt
import json
import re
import sys
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from mdt_backend import bundles, fhir
from mdt_backend.briefing import Case, RedFlag, Section
from mdt_backend.bundles import Bundle, category_text, date_of, src, text_of, title_of
from mdt_backend.config import settings
from mdt_backend.from_fhir import TUMOURS, build_case
from mdt_backend.knowledge import guideline_source, guidelines
from mdt_backend.llm import chat_json
from mdt_backend.load_fhir import dataset_id
from mdt_backend.provenance import NOT_FOUND, Source, Statement

PROMPT_VERSION = "mdt-agent-v1"
OUT_DIR = Path(__file__).parents[3] / "data" / "ai_cases"
GUIDELINE_DOCS = {"breast": "PRS", "lung": "PLI", "colorectal": "KRC"}
GENERAL_DOC = "OBC"
AREAS = ["radiology", "surgery", "oncology", "pathology", "patient"]
SPECIALISTS = {
    "radiology": (
        "Radiologie",
        (
            "radiolog – rozumí zobrazovacím metodám (CT, MR, PET/CT, scintigrafie, RTG): rozsah "
            "onemocnění, staging, hodnocení odpovědi (RECIST), aktuálnost a úplnost zobrazení, "
            "nejasná ložiska a co dalšího zobrazit"
        ),
    ),
    "surgery": (
        "Chirurgie",
        (
            "chirurg – rozhoduje, zda je nález operabilní/resekabilní: technická resekabilita, "
            "funkční operabilita a komorbidity, rizika výkonu, načasování vůči systémové léčbě, "
            "potřeba biopsie"
        ),
    ),
    "oncology": (
        "Klinická onkologie",
        (
            "klinický onkolog – rozhoduje o medikamentózní léčbě: linie léčby, biomarkery, "
            "předchozí léčba a odpověď, toxicita a nežádoucí účinky, lékové interakce, "
            "výkonnostní stav"
        ),
    ),
}
SEVERITY = {"RED": "high", "YELLOW": "medium"}
_DROP_KEYS = {"meta", "subject", "patient", "identifier", "system", "for"}

# --- shared JSON schema pieces (strict mode: every property required, no extras) --------------
_REFS = {
    "type": "array",
    "items": {
        "type": "object",
        "properties": {
            "ref": {"type": "string", "description": "např. Observation/P01-lab03-hb"},
            "excerpt": {"type": "string", "description": "doslovná citace ze záznamu, ≤ 25 slov"},
        },
        "required": ["ref", "excerpt"],
        "additionalProperties": False,
    },
}
_GL = {"type": "array", "items": {"type": "string"}, "description": "id pasáží, např. KRC-2.3"}


def _obj(**props) -> dict:
    return {
        "type": "object",
        "properties": props,
        "required": list(props),
        "additionalProperties": False,
    }


def _arr(item: dict) -> dict:
    return {"type": "array", "items": item}


_STR = {"type": "string"}

CACC_SCHEMA = _obj(
    prerequisites=_arr(
        _obj(
            id=_STR,
            item=_STR,
            why=_STR,
            area={"type": "string", "enum": AREAS},
            guideline_ids=_GL,
        )
    ),
    expected_symptoms=_arr(_obj(symptom=_STR, basis=_STR, guideline_ids=_GL)),
)
FINDINGS_SCHEMA = _obj(
    checklist=_arr(
        _obj(
            id=_STR,
            status={"type": "string", "enum": ["splneno", "chybi", "zastarale", "rozpor"]},
            note=_STR,
            refs=_REFS,
        )
    ),
    findings=_arr(
        _obj(
            severity={"type": "string", "enum": ["RED", "YELLOW"]},
            kind={
                "type": "string",
                "enum": ["chybejici_udaj", "rozpor", "neocekavany_symptom", "zastarale", "jine"],
            },
            area={"type": "string", "enum": AREAS},
            text=_STR,
            refs=_REFS,
            guideline_ids=_GL,
        )
    ),
)
CONTEXT_SCHEMA = _obj(refs=_arr(_STR), reason=_STR)
VERDICT_SCHEMA = _obj(
    points=_arr(_obj(text=_STR, refs=_REFS, guideline_ids=_GL)),
    verdict=_obj(text=_STR, refs=_REFS, guideline_ids=_GL),
    missing=_arr(_STR),
)
RECOMMEND_SCHEMA = _obj(
    options=_arr(_obj(rank={"type": "integer"}, text=_STR, refs=_REFS, guideline_ids=_GL)),
    preference=_obj(stated={"type": "boolean"}, text=_STR, refs=_REFS, matches_option=_STR),
    questions=_arr(_obj(text=_STR, refs=_REFS, guideline_ids=_GL)),
)

RULES = f"""Pravidla (závazná):
- Piš česky, velmi stručně, v bodech; čísla s jednotkami a daty (YYYY-MM-DD), kde existují.
- Používej VÝHRADNĚ dodaná data pacienta a dodané pasáže doporučených postupů. Žádné znalosti
  modelu o léčbě, které nejsou v pasážích; nic nedomýšlej.
- Každé tvrzení o pacientovi doložit `refs`: přesná reference záznamu ve tvaru, v jakém je uvedena
  v hranatých závorkách (např. Observation/P01-lab03-hb), a `excerpt` = DOSLOVNÁ krátká citace z
  daného záznamu (zkopírovat znak po znaku, ≤ 25 slov) – citovat čitelný text nebo hodnotu,
  nikdy syntaxi JSON (klíče, uvozovky, závorky).
- Každé doporučení nebo pravidlo doložit `guideline_ids` = id pasáží (např. KRC-2.3) ze seznamu.
- Údaj, který v datech není, nikdy neodhaduj; uveď, že chybí („{NOT_FOUND}“).
- Data obsahují záměrné chyby a mezery: rozpory uváděj, neopravuj je.
- Jsi podpůrný nástroj, ne rozhodovatel: rozhodnutí patří komisi MDT."""


# --- 1. gather ---------------------------------------------------------------------------------
class Record:
    """The patient's record as the agent sees it: a Bundle keyed by dataset ids, and a `fetch`
    tool that reads one resource from where the record came from (IRIS or the bundle file)."""

    def __init__(self, case_id: str, source: str = "iris"):
        self.case_id = case_id.lower()
        self.patient_id = case_id.upper()
        self.source = source
        if source == "file":
            path = bundles.bundle_paths().get(self.case_id)
            if not path:
                raise SystemExit(f"{case_id}: no bundle in {settings.dataset_dir / 'pacienti'}")
            self.bundle = bundles.load(path)
            self.iris_ids: dict[str, str] = {}
        else:
            # Only the FHIR server is read. IRIS rejects "_" in ids (decision #12); the loader
            # keeps the original id as a tag, so citations use the dataset's ids (the app's source
            # drawer and the frontend resolve those)
            by_ref, self.iris_ids = {}, {}
            for r in fhir.get_patient_record(self.patient_id):
                ref = f"{r['resourceType']}/{dataset_id(r)}"
                self.iris_ids[ref] = f"{r['resourceType']}/{r['id']}"
                by_ref[ref] = {**r, "id": ref.split("/", 1)[1]}
            self.bundle = Bundle({"entry": [{"resource": r} for r in by_ref.values()]})

    def fetch(self, ref: str) -> dict | None:
        """Tool: one resource by dataset reference (read from IRIS when that's the source)."""
        base = ref.split("#")[0]
        if base not in self.bundle.by_ref:
            return None
        if self.source == "file":
            return self.bundle.by_ref[base]
        rtype, rid = self.iris_ids.get(base, base).split("/", 1)
        r = fhir.get(f"{rtype}/{rid}")
        return {**r, "id": base.split("/", 1)[1]}

    def refs(self) -> list[str]:
        return [ref for ref in self.bundle.by_ref if not ref.startswith(("Practitioner/", "Org"))]


def _clean(node):
    """Resource JSON without noise (narrative, system URIs, subject) and with attachments decoded."""
    if isinstance(node, dict):
        if "data" in node and "contentType" in node:
            return {"text": bundles._decode(node)}
        return {
            k: _clean(v)
            for k, v in node.items()
            if k not in _DROP_KEYS and not (k == "text" and isinstance(v, dict))  # narrative
        }
    if isinstance(node, list):
        return [_clean(v) for v in node]
    return node


def digest(resources: dict[str, dict]) -> str:
    """One line per resource: `[Type/id] {compact JSON}` — what the model reads and cites."""
    return "\n".join(
        f"[{ref}] {json.dumps(_clean(r), ensure_ascii=False, separators=(',', ':'))}"
        for ref, r in resources.items()
    )


def index(b: Bundle, refs: list[str]) -> str:
    """One short line per resource (date, type, category, title) — for picking context."""
    lines = []
    for ref in refs:
        r = b.by_ref[ref]
        cat = category_text(r)
        lines.append(f"[{ref}] {date_of(r) or ''} {cat + ' · ' if cat else ''}{title_of(r)}")
    return "\n".join(lines)


def _norm(s: str) -> str:
    """Words only (case, punctuation and spacing ignored) — for checking quotes are verbatim."""
    return " ".join(re.findall(r"\w+", s.lower()))


# --- 2. diagnosis ------------------------------------------------------------------------------
def diagnosis(b: Bundle) -> dict:
    onco = [c for c in b.all("Condition") if category_text(c) == "onkologická diagnóza"]
    if not onco:
        raise SystemExit("record has no oncological diagnosis (Condition)")
    primary = onco[0]["code"]["coding"][0]["code"]
    tumour = TUMOURS.get(primary[:3], "unknown")
    docs = [d for d in (GUIDELINE_DOCS.get(tumour), GENERAL_DOC) if d]
    return {
        "primary": primary,
        "tumour": tumour,
        "conditions": [
            f"{c['code']['coding'][0]['code']} {c['code'].get('text', '')}"
            + (f" – {s}" if (s := c.get("stage", [{}])[0].get("summary", {}).get("text")) else "")
            for c in onco
        ],
        "docs": docs,
        "passages": {k: v for k, v in guidelines().items() if k.split("-")[0] in docs},
    }


def passages_text(passages: dict) -> str:
    return "\n".join(f"[{pid}] {p['title']}: {p['text']}" for pid, p in passages.items())


# --- citation checking -------------------------------------------------------------------------
class Citations:
    """Turns the model's citations into Sources, dropping anything not in the record/guidelines."""

    def __init__(self, record: Record, passages: dict):
        self.b = record.bundle
        self.passages = passages
        self.rejected: list[dict] = []
        self._hay = {
            ref: _norm(text_of(r) + " " + json.dumps(_clean(r), ensure_ascii=False))
            for ref, r in self.b.by_ref.items()
        }

    def record(self, refs: list[dict], where: str) -> list[Source]:
        out = []
        for c in refs:
            ref = c["ref"].strip().strip("[]")
            base, _, item = ref.partition("#")
            r = self.b.get(base)
            if not r:
                self.rejected.append({"where": where, "ref": ref, "reason": "not in record"})
                continue
            excerpt = c["excerpt"].strip()
            if excerpt and _norm(excerpt) not in self._hay[base]:
                self.rejected.append(
                    {"where": where, "ref": ref, "excerpt": excerpt, "reason": "not verbatim"}
                )
                excerpt = ""  # keep the pointer, never show a quote the record doesn't contain
            elif re.search(r'[{}"]', excerpt):  # a JSON fragment: show the readable value instead
                excerpt = text_of(r) if len(text_of(r)) <= 200 else ""
            out.append(src(self.b, r, excerpt or None, item or None))
        return list({s.reference + (s.excerpt or ""): s for s in out}.values())

    def guideline(self, ids: list[str], where: str) -> list[Source]:
        out = []
        for pid in dict.fromkeys(i.strip().strip("[]") for i in ids):
            if pid in self.passages:
                out.append(guideline_source(pid))
            else:
                self.rejected.append({"where": where, "guideline": pid, "reason": "not allowed"})
        return out

    def statement(self, text: str, refs: list[dict], gl: list[str], where: str):
        sources = self.record(refs, where) + self.guideline(gl, where)
        text = text.strip()
        if not sources and not text.endswith(NOT_FOUND):
            self.rejected.append({"where": where, "text": text, "reason": "no valid source"})
            return None
        return Statement(text=text, origin="ai", sources=sources, model=model_tag())


def model_tag() -> str:
    return f"{settings.llm_model}/{PROMPT_VERSION}"


def missing(text: str) -> Statement:
    text = text.strip().rstrip(".").removesuffix(NOT_FOUND.rstrip(".")).rstrip(" :–-")
    return Statement(text=f"{text}: {NOT_FOUND}", origin="ai", model=model_tag())


# --- 3–6. LLM steps ----------------------------------------------------------------------------
def _call(trace: dict, step: str, system: str, user: str, schema: dict) -> dict:
    t0 = time.monotonic()
    out = chat_json(system, user, schema, name=step.split(":")[0])
    trace["steps"][step] = {"seconds": round(time.monotonic() - t0, 1), "output": out}
    return out


def build_cacc(dx: dict, question: str, trace: dict) -> dict:
    system = f"""Jsi metodik onkologické multidisciplinární komise (MDT). Z doporučených postupů
sestav kontrolní seznam úplnosti a konzistence (CACC) pro danou diagnózu a otázku komise:
1) prerequisites – každý údaj, který musí být v dokumentaci, aby komise mohla rozhodnout
   (histologie, staging a jeho stáří, biomarkery, výkonnostní stav, funkční vyšetření, předchozí
   léčba, preference pacienta…), u každého proč (krátce) a id pasáží; area = odbornost, které
   údaj patří. id ve tvaru C1, C2…
2) expected_symptoms – příznaky očekávatelné u této diagnózy a jejího rozsahu (basis = odkud
   plyne, např. „metastázy jater“); id pasáží, pokud je pasáž uvádí, jinak prázdné pole.
Seznam je obecný pro diagnózu, ne pro konkrétní nálezy pacienta.
{RULES}"""
    user = f"""Diagnózy: {"; ".join(dx["conditions"])}
Otázka pro komisi: {question}

Pasáže doporučených postupů:
{passages_text(dx["passages"])}"""
    return _call(trace, "cacc", system, user, CACC_SCHEMA)


def find_issues(dx: dict, cacc: dict, record_text: str, mdt_date, trace: dict) -> dict:
    system = f"""Jsi kontrolor kvality podkladů pro onkologickou komisi (MDT), datum komise
{mdt_date}. Projdi záznam pacienta proti kontrolnímu seznamu CACC:
1) checklist – pro KAŽDOU položku prerequisites: splneno / chybi / zastarale / rozpor, krátká
   poznámka a doklad (refs; u „chybi“ prázdné refs).
2) findings – všechny problémy: chybějící údaje nutné pro rozhodnutí, rozpory mezi zdroji (např.
   ECOG lékař vs. pacient, různé TNM, text vs. hodnota), zastaralé podklady, a NOVÉ příznaky či
   obtíže, které nepatří mezi očekávané příznaky diagnózy (expected_symptoms) – u nich zvaž
   nežádoucí účinek léčby, lékovou interakci nebo nové onemocnění a uveď příslušný lék/záznam.
   severity: RED = brání rozhodnutí nebo ohrožuje pacienta; YELLOW = nutno ověřit/doplnit.
   U rozporu cituj OBA zdroje. Text ≤ 2 věty.
{RULES}"""
    user = f"""Diagnózy: {"; ".join(dx["conditions"])}

CACC:
{json.dumps(cacc, ensure_ascii=False)}

Pasáže doporučených postupů:
{passages_text(dx["passages"])}

Záznam pacienta (jeden záznam na řádek, reference v hranatých závorkách):
{record_text}"""
    return _call(trace, "findings", system, user, FINDINGS_SCHEMA)


def specialist(
    key: str, rec: Record, dx: dict, cacc: dict, issues: dict, question: str, trace: dict
) -> dict:
    title, role = SPECIALISTS[key]
    focus = {
        "cacc": [p for p in cacc["prerequisites"] if p["area"] == key],
        "findings": [f for f in issues["findings"] if f["area"] in (key, "patient")],
    }
    # 5a: pick the records this specialist needs (a separate call), then fetch them
    pick = _call(
        trace,
        f"context:{key}",
        f"""Jsi {role}. Připravuješ se na onkologickou komisi (MDT). Ze seznamu záznamů
pacienta vyber VŠECHNY záznamy, které potřebuješ pro své stanovisko k otázce komise (včetně
nominace/žádanky, relevantních nálezů, laboratoře, dotazníku pacienta a předchozích závěrů MDT).
Vrať jejich reference přesně tak, jak jsou v hranatých závorkách.""",
        f"""Otázka pro komisi: {question}
Diagnózy: {"; ".join(dx["conditions"])}
Tvoje položky kontrolního seznamu a nálezy: {json.dumps(focus, ensure_ascii=False)}

Seznam záznamů:
{index(rec.bundle, rec.refs())}""",
        CONTEXT_SCHEMA,
    )
    context = {}
    for ref in dict.fromkeys(r.strip().strip("[]").split("#")[0] for r in pick["refs"]):
        if r := rec.fetch(ref):
            context[ref] = r
    trace["steps"][f"context:{key}"]["fetched"] = list(context)
    # 5b: the specialist's view, citing guideline passages
    verdict = _call(
        trace,
        f"verdict:{key}",
        f"""Jsi {role}, člen onkologické komise (MDT). Napiš své odborné stanovisko k otázce
komise POUZE ze své odbornosti:
- points: 3–6 klíčových bodů (nálezy, jejich význam, co z pasáží plyne), každý s refs a
  guideline_ids, kde pravidlo plyne z pasáže,
- verdict: tvůj závěr k otázce komise v 1–2 větách, opřený o konkrétní pasáže (guideline_ids)
  a záznamy (refs),
- missing: údaje z tvé odbornosti, které pro rozhodnutí chybějí (krátké názvy, bez věty o chybění).
{RULES}""",
        f"""Otázka pro komisi: {question}
Diagnózy: {"; ".join(dx["conditions"])}
Kontrolní seznam a nálezy pro tvou odbornost: {json.dumps(focus, ensure_ascii=False)}

Pasáže doporučených postupů:
{passages_text(dx["passages"])}

Vybrané záznamy pacienta:
{digest(context)}""",
        VERDICT_SCHEMA,
    )
    return {"key": key, "title": title, "context": list(context), **verdict}


def recommend(
    dx: dict, issues: dict, views: list[dict], preference: str, question: str, trace: dict
) -> dict:
    system = f"""Jsi koordinátor onkologické komise (MDT). Na základě nálezů a stanovisek
radiologa, chirurga a klinického onkologa navrhni 1 až 2 možnosti léčby (options, rank 1 = první
volba) PŘÍSNĚ podle dodaných pasáží doporučených postupů:
- každá možnost musí odpovídat konkrétní pasáži (guideline_ids, alespoň jedna) a stavu pacienta
  (refs); text ≤ 2 věty, uveď podmínky (např. co je třeba nejprve doplnit),
- pokud podle pasáží nelze rozhodnout bez chybějících údajů, uveď to jako podmínku možnosti,
- preference: stated = zda pacient uvedl preferenci léčby; text = preference stručně a zda ji
  možnosti respektují; matches_option = rank možnosti, která jí odpovídá, nebo „žádná“.
  Preference pacienta se zmíní, ale přednost mají doporučené postupy,
- questions: 2–3 otázky, které musí komise vyřešit (refs a/nebo guideline_ids).
{RULES}"""
    user = f"""Otázka pro komisi: {question}
Diagnózy: {"; ".join(dx["conditions"])}
Preference pacienta (ze záznamu): {preference}

Nálezy (RED/YELLOW):
{json.dumps(issues["findings"], ensure_ascii=False)}

Stanoviska odborností:
{json.dumps([{k: v[k] for k in ("title", "points", "verdict")} for v in views], ensure_ascii=False)}

Pasáže doporučených postupů:
{passages_text(dx["passages"])}"""
    return _call(trace, "recommend", system, user, RECOMMEND_SCHEMA)


def patient_preference(b: Bundle) -> str:
    """Preference as recorded: nomination note + the patient's own PROMs answers, with references."""
    out = []
    for sr in b.all("ServiceRequest"):
        for n in sr.get("note", []):
            if n["text"].startswith("Preference"):
                out.append(f"[ServiceRequest/{sr['id']}] {n['text']}")
    for qr in bundles.by_date(b.all("QuestionnaireResponse"))[-1:]:
        for link, (q, a) in bundles.answers(qr).items():
            if link in ("priorita", "postoj"):
                out.append(f"[QuestionnaireResponse/{qr['id']}#{link}] {q}: {bundles.value_of(a)}")
    return "\n".join(out) or NOT_FOUND


# --- assemble ----------------------------------------------------------------------------------
def run(case_id: str, source: str = "iris") -> tuple[Case, dict]:
    """The whole pipeline for one patient: returns the AI-augmented Case and a trace."""
    t0 = time.monotonic()
    rec = Record(case_id, source)
    b = rec.bundle
    case = build_case(rec.case_id, b)
    dx = diagnosis(b)
    question = case.question.text if case.question else NOT_FOUND
    trace: dict = {
        "case": rec.case_id,
        "source": source,
        "model": model_tag(),
        "created": dt.datetime.now().isoformat(timespec="seconds"),
        "diagnosis": {k: v for k, v in dx.items() if k != "passages"},
        "steps": {},
    }
    cite = Citations(rec, dx["passages"])
    record_text = digest({ref: b.by_ref[ref] for ref in rec.refs()})

    cacc = build_cacc(dx, question, trace)
    issues = find_issues(dx, cacc, record_text, case.mdt_date, trace)
    with ThreadPoolExecutor(len(SPECIALISTS)) as pool:
        views = list(
            pool.map(lambda k: specialist(k, rec, dx, cacc, issues, question, trace), SPECIALISTS)
        )
    rec_out = recommend(dx, issues, views, patient_preference(b), question, trace)

    # missing checklist items and specialist views → the specialist's section
    sections = {s.id: s for s in case.sections}
    gaps: dict[str, set[str]] = {}

    # findings → red flags (RED = high, YELLOW = medium); an unsourced missing-data finding is
    # still a gap, so it is kept as a NOT_FOUND statement instead of being lost
    for i, f in enumerate(issues["findings"]):
        s = cite.statement(f["text"], f["refs"], f["guideline_ids"], f"findings.{i}")
        if s:
            case.red_flags.append(RedFlag(severity=SEVERITY[f["severity"]], statement=s))
        elif f["kind"] == "chybejici_udaj":
            gaps.setdefault(f["area"], set()).add(f["text"])

    def section(area: str) -> Section:
        if area not in sections:
            title = SPECIALISTS.get(area, (area.capitalize(),))[0]
            sections[area] = Section(id=area, title=title, items=[])
            case.sections.append(sections[area])
        return sections[area]

    prereq = {p["id"]: p for p in cacc["prerequisites"]}
    for c in issues["checklist"]:
        if c["status"] == "chybi" and (p := prereq.get(c["id"])):
            gaps.setdefault(p["area"], set()).add(p["item"])
    for v in views:
        sec = section(v["key"])
        for i, p in enumerate(v["points"]):
            if s := cite.statement(p["text"], p["refs"], p["guideline_ids"], f"{v['key']}.{i}"):
                sec.items.append(s)
        vd = v["verdict"]
        s = cite.statement(
            f"Stanovisko ({v['title']}): {vd['text']}",
            vd["refs"],
            vd["guideline_ids"],
            f"{v['key']}.verdict",
        )
        if s:
            sec.items.append(s)
        gaps.setdefault(v["key"], set()).update(v["missing"])
    for area, items in gaps.items():
        known: set[str] = set()
        for item in sorted(items):
            if _norm(item) not in known:
                known.add(_norm(item))
                section(area).items.append(missing(item))

    # options (max 2, each must keep a guideline citation) + preference + questions
    pref = rec_out["preference"]
    pref_sources = cite.record(pref["refs"], "preference") if pref["stated"] else []
    options = sorted(rec_out["options"], key=lambda o: o["rank"])
    for i, o in enumerate(options[:2]):
        gl = cite.guideline(o["guideline_ids"], f"options.{i}")
        if not gl:
            cite.rejected.append({"where": f"options.{i}", "reason": "option without guideline"})
            continue
        text = o["text"].strip()
        sources = gl + cite.record(o["refs"], f"options.{i}")
        if pref["stated"]:
            match = str(o["rank"]) == pref["matches_option"].strip()
            text += f" Preference pacienta: {pref['text'].strip()}" if i == 0 or match else ""
            sources += pref_sources if (i == 0 or match) else []
        case.decision_support.options.append(
            Statement(text=text, origin="ai", sources=sources, model=model_tag())
        )
    for i, q in enumerate(rec_out["questions"][:3]):
        if s := cite.statement(q["text"], q["refs"], q["guideline_ids"], f"questions.{i}"):
            case.decision_support.questions.append(s)

    trace["rejected_citations"] = cite.rejected
    trace["seconds"] = round(time.monotonic() - t0, 1)
    return Case.model_validate(case.model_dump()), trace


def summary(case: Case) -> dict:
    """What a run recommends, for comparing runs: option texts and the passages they cite."""
    return {
        "options": [
            {
                "text": o.text,
                "guidelines": sorted(
                    s.reference.removeprefix("guideline:")
                    for s in o.sources
                    if s.reference.startswith("guideline:")
                ),
            }
            for o in case.decision_support.options
        ],
        "red": sum(
            f.severity == "high" and f.statement.model == model_tag() for f in case.red_flags
        ),
    }


def compare(a: Case, b: Case) -> dict:
    """Similarity of two runs' recommendations: first option's passages and all passages (Jaccard)."""
    sa, sb = summary(a), summary(b)

    def jac(x: set, y: set) -> float:
        return round(len(x & y) / len(x | y), 2) if x | y else 1.0

    first = [set(s["options"][0]["guidelines"]) if s["options"] else set() for s in (sa, sb)]
    every = [{g for o in s["options"] for g in o["guidelines"]} for s in (sa, sb)]
    return {
        "first_option_passages_jaccard": jac(*first),
        "all_option_passages_jaccard": jac(*every),
        "option_counts": [len(sa["options"]), len(sb["options"])],
        "runs": [sa, sb],
    }


def save(case: Case, trace: dict, out_dir: Path = OUT_DIR, suffix: str = "") -> Path:
    out_dir.mkdir(parents=True, exist_ok=True)
    path = out_dir / f"{case.id}{suffix}.json"
    path.write_text(case.model_dump_json(indent=2), "utf-8")
    trace_path = out_dir / f"{case.id}{suffix}.trace.json"
    trace_path.write_text(json.dumps(trace, ensure_ascii=False, indent=2, default=str), "utf-8")
    return path


def main() -> None:
    """CLI: uv run mdt-agent P01 [--runs 2] [--source iris|file]"""
    ap = argparse.ArgumentParser(prog="mdt-agent", description=__doc__.splitlines()[0])
    ap.add_argument("patient", help="patient id, e.g. P01")
    ap.add_argument("--source", choices=["iris", "file"], default="iris")
    ap.add_argument("--runs", type=int, default=1, help="run N times and compare recommendations")
    args = ap.parse_args()
    cases = []
    for n in range(1, args.runs + 1):
        case, trace = run(args.patient, args.source)
        suffix = f".run{n}" if args.runs > 1 else ""
        path = save(case, trace, suffix=suffix)
        print(
            f"run {n}: {path} ({trace['seconds']} s, "
            f"{len(trace['rejected_citations'])} citations rejected)",
            file=sys.stderr,
        )
        cases.append(case)
    save(cases[-1], trace)  # the latest run is what the app serves
    if len(cases) > 1:
        print(json.dumps(compare(cases[0], cases[1]), ensure_ascii=False, indent=2))
    else:
        print(json.dumps(summary(cases[0]), ensure_ascii=False, indent=2))
