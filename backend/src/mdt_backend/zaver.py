"""Závěr zasedání MDT: fill docs/template_zaver_zasedani/form.md for one patient and export a PDF.

Run: cd backend && uv run mdt-zaver P01 [-o out.pdf]   (needs the FHIR server + AZURE_API_KEY)

1. # HEADER — dummy team/patient contact data, filled programmatically (no LLM).
2. # BODY   — LLM call 1: patient history from the full FHIR record (get_patient_record), one
              structured field per template line, each with the FHIR resources it came from.
3. # RESPONSE — LLM call 2: the filled BODY only → concise recommendation, posing as the MDT.
4. Filled form saved as .md and rendered to PDF (pdf.py). Everything from steps 2–3 is labelled
   as an unconfirmed AI proposal (blue bar); unsourced or unverifiable claims are flagged.
"""

import argparse
import hashlib
import json
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

from mdt_backend import fhir, llm
from mdt_backend.config import settings
from mdt_backend.pdf import BLUE, GREY, PdfDoc, Run

TEMPLATE = Path(__file__).parents[3] / "docs" / "template_zaver_zasedani" / "form.md"
OUT_DIR = Path(__file__).parents[3] / "data" / "zavery"
NOT_FOUND = "V dostupné dokumentaci se nenachází."
NO_SOURCE = "bez ověřeného zdroje"


@dataclass
class Field:
    label: str
    depth: int
    value: str  # template default ("?", "0", "") until filled
    group: bool  # has indented children
    path: str  # "Historie > Staging > CT"
    sources: list[str] | None = None  # None = not AI-filled


def parse_template(text: str) -> dict[str, list[Field | None]]:
    """`# NAME` sections → lines; None = blank line (kept for layout)."""
    sections: dict[str, list[Field | None]] = {}
    current: list[Field | None] = []
    for line in text.splitlines():
        if line.startswith("# "):
            current = sections.setdefault(line[2:].strip(), [])
        elif not line.strip():
            current.append(None)
        else:
            label, _, value = line.strip().partition(":")
            current.append(
                Field(label.strip(), len(line) - len(line.lstrip("\t")), value.strip(), False, "")
            )
    for lines in sections.values():
        stack: list[Field] = []
        fields = [f for f in lines if f]
        for i, f in enumerate(fields):
            f.group = i + 1 < len(fields) and fields[i + 1].depth > f.depth
            stack = [s for s in stack if s.depth < f.depth]
            f.path = " > ".join([s.label for s in stack] + [f.label])
            stack.append(f)
    return sections


def leaves(lines: list[Field | None]) -> list[Field]:
    return [f for f in lines if f and not f.group]


# --- 1. HEADER: dummy data ------------------------------------------------------------------

_DUMMY_TEAM = {  # template label prefix → fictional names to pick from
    "Klinika zobrazovacích metod": ["MUDr. Petr Svoboda", "doc. MUDr. Eva Dvořáková, Ph.D."],
    "Onkologická klinika": ["MUDr. Tomáš Černý", "MUDr. Jana Nováková"],
    "III.chirurgická klinika": ["prof. MUDr. Martin Kučera, CSc.", "MUDr. Ondřej Malý"],
    "Ústav Patologie": ["MUDr. Hana Veselá", "MUDr. Jiří Horák, Ph.D."],
    "Koordinátorka onkologické péče": ["Mgr. Lucie Procházková", "Bc. Petra Králová"],
}


def fill_header(lines: list[Field | None], patient: dict) -> None:
    pid = patient["id"]
    seed = int(hashlib.sha256(pid.encode()).hexdigest(), 16)
    year = str(patient.get("birthDate", "1960"))[:4]
    month = 1 + seed % 12 + (50 if patient.get("gender") == "female" else 0)
    patient_values = {
        "Jméno, příjmení pacienta": (patient.get("name") or [{}])[0].get("text", pid),
        "Rodné číslo (pojišťovna) pacienta": f"{year[2:]}{month:02d}{1 + seed % 28:02d}/{seed % 10000:04d}"
        " (VZP 111) – fiktivní",
        "Adresa pacienta": f"Fiktivní {1 + seed % 90}, 100 00 Praha 10",
        "Telefonní kontakt na pacienta": f"+420 600 {seed % 1000:03d} {seed // 1000 % 1000:03d}",
    }
    for f in leaves(lines):
        if f.label in patient_values:
            f.value = patient_values[f.label]
        elif f.value == "?":
            names = _DUMMY_TEAM.get(f.label, ["MUDr. Jan Novák"])
            f.value = names[seed % len(names)]


# --- 2. BODY: patient history from the FHIR record ------------------------------------------

HISTORY_SYSTEM = f"""Jsi klinický dokumentarista onkologického multidisciplinárního týmu (MDT).
Z dodaného FHIR záznamu pacienta vyplň pole formuláře pro zasedání MDT. Pravidla:
- Jen fakta ze záznamu, nic nedomýšlej. Nejsou-li data, napiš přesně: "{NOT_FOUND}"
- Extrémně stručně: heslovité body oddělené "; ", žádné celé věty (epikríza max. 3 krátké body).
- Čísla vždy, kde to jde: data (MM/RRRR nebo DD.MM.RRRR), velikosti v mm, hodnoty s jednotkami,
  počty cyklů, délky v měsících, TNM, ECOG, procenta.
- Pole s výchozí hodnotou 0 jsou počty/přítomnost: "0" = nebylo; jinak počet nebo stručný popis
  (např. "1; 03/2025 jaterní meta"). "Délka" dispenzarizace v měsících.
- "zdroje": ID FHIR zdrojů (ResourceType/id přesně jak jsou v záznamu), ze kterých hodnota pochází.
  U "{NOT_FOUND}" prázdný seznam.
- Česky, standardní lékařské zkratky."""

RECOMMENDATION_SYSTEM = """Jsi multidisciplinární onkologická komise (MDT: klinický a radiační
onkolog, chirurg, radiolog, patolog). Na základě podkladů formuláře vydej závěr zasedání MDT.
Pravidla: velmi stručně a konkrétně (léčebný záměr, doporučená léčba/postup, další vyšetření,
termín kontroly); vycházej jen z podkladů; chybí-li klíčová data pro rozhodnutí, uveď co doplnit.
Česky, heslovitě."""

RECOMMENDATION_SCHEMA = {
    "type": "object",
    "properties": {
        "doporuceni": {
            "type": "array",
            "description": "2–5 velmi stručných bodů závěru MDT",
            "items": {"type": "string"},
        },
        "zduvodneni": {"type": "string", "description": "Zdůvodnění, max. 1–2 krátké věty"},
    },
    "required": ["doporuceni", "zduvodneni"],
    "additionalProperties": False,
}


def _history_schema(fields: list[Field]) -> dict:
    item = {
        "type": "object",
        "properties": {
            "hodnota": {"type": "string"},
            "zdroje": {"type": "array", "items": {"type": "string"}},
        },
        "required": ["hodnota", "zdroje"],
        "additionalProperties": False,
    }
    props = {f"f{i:02d}": {**item, "description": f.path} for i, f in enumerate(fields)}
    return {
        "type": "object",
        "properties": props,
        "required": list(props),
        "additionalProperties": False,
    }


def _compact(resources: list[dict]) -> str:
    return "\n".join(
        json.dumps(
            {k: v for k, v in r.items() if k != "meta"}, ensure_ascii=False, separators=(",", ":")
        )
        for r in resources
    )


def fill_body(lines: list[Field | None], resources: list[dict]) -> None:
    fields = leaves(lines)
    field_list = "\n".join(
        f"f{i:02d}: {f.path}" + (f" (výchozí: {f.value})" if f.value else "")
        for i, f in enumerate(fields)
    )
    user = f"Pole formuláře:\n{field_list}\n\nFHIR záznam pacienta (1 zdroj na řádek):\n{_compact(resources)}"
    answer = llm.chat_json(HISTORY_SYSTEM, user, _history_schema(fields), name="historie")
    known = {f"{r['resourceType']}/{r['id']}" for r in resources}
    for i, f in enumerate(fields):
        a = answer[f"f{i:02d}"]
        f.value = a["hodnota"].strip() or NOT_FOUND
        f.sources = [s for s in a["zdroje"] if s in known]  # drop hallucinated references


def render_section(lines: list[Field | None], with_sources: bool = False) -> str:
    out = []
    for f in lines:
        if f is None:
            out.append("")
            continue
        line = "\t" * f.depth + f"{f.label}: {f.value}".rstrip()
        if with_sources and f.sources:
            line += f"  [Zdroj: {', '.join(f.sources)}]"
        out.append(line)
    return "\n".join(out).strip("\n")


# --- 3. RESPONSE: MDT recommendation ---------------------------------------------------------


def recommend(body_text: str) -> dict:
    return llm.chat_json(
        RECOMMENDATION_SYSTEM,
        f"Podklady pro MDT:\n{body_text}",
        RECOMMENDATION_SCHEMA,
        name="zaver_mdt",
    )


# --- 4. Output ---------------------------------------------------------------------------------


def _unsourced(f: Field) -> bool:
    return f.sources is not None and not f.sources and f.value not in (NOT_FOUND, "0")


def to_pdf(pid: str, sections: dict, rec: dict, path: Path, created: str) -> None:
    doc = PdfDoc(
        f"Závěr zasedání MDT – {pid}", footer=f"Závěr zasedání MDT · {pid} · vygenerováno {created}"
    )
    doc.paragraph([Run("Závěr zasedání MDT", bold=True)], size=16)
    doc.paragraph(
        [Run(f"Pacient {pid} · vygenerováno {created} · model {settings.llm_model}", color=GREY)],
        size=8,
    )
    doc.space(4)
    doc.paragraph(
        [
            Run("AI návrh – nepotvrzeno. ", bold=True, color=BLUE),
            Run(
                "Části s modrým pruhem vytvořil AI model z FHIR záznamu a musí je zkontrolovat a potvrdit "
                "lékař. Zdroje jsou uvedeny pod každou položkou. Hlavička obsahuje fiktivní údaje.",
                color=BLUE,
            ),
        ],
        size=8,
        bar=BLUE,
    )
    doc.rule()

    def section(title: str, lines: list[Field | None], ai: bool) -> None:
        doc.space(4)
        doc.paragraph([Run(title, bold=True)], size=12)
        doc.space(2)
        bar = BLUE if ai else None
        for f in lines:
            if f is None:
                doc.space(4)
                continue
            indent = 14 * f.depth
            if f.group or not f.value:
                doc.keep(50)
                doc.paragraph([Run(f.label, bold=True)], indent=indent, bar=bar)
                continue
            muted = f.value == NOT_FOUND
            doc.paragraph(
                [Run(f"{f.label}: ", bold=True), Run(f.value, color=GREY if muted else (0, 0, 0))],
                indent=indent,
                bar=bar,
            )
            if f.sources:
                doc.paragraph(
                    [Run("Zdroj: " + ", ".join(f.sources), color=GREY)],
                    size=6.5,
                    indent=indent,
                    text_offset=10,
                    bar=bar,
                )
            elif _unsourced(f):
                doc.paragraph(
                    [Run(f"⚠ {NO_SOURCE}", color=(0.75, 0.3, 0))],
                    size=6.5,
                    indent=indent,
                    text_offset=10,
                    bar=bar,
                )

    section("Multidisciplinární tým a pacient", sections["HEADER"], ai=False)
    doc.rule()
    section("Podklady pro MDT", sections["BODY"], ai=True)
    doc.rule()
    doc.space(4)
    doc.paragraph([Run("Závěr MDT", bold=True)], size=12)
    doc.paragraph(
        [Run("Návrh AI v roli komise – rozhodnutí přijímá MDT.", color=BLUE)], size=8, bar=BLUE
    )
    doc.space(2)
    for point in rec["doporuceni"]:
        doc.paragraph([Run("•  "), Run(point)], bar=BLUE)
    doc.space(2)
    doc.paragraph([Run("Zdůvodnění: ", bold=True), Run(rec["zduvodneni"])], size=9, bar=BLUE)
    doc.space(16)
    doc.paragraph(
        [Run("Potvrdil (jméno, podpis, datum): ______________________________", color=GREY)], size=9
    )
    doc.save(path)


def create_zaver(patient_id: str, out: Path | None = None) -> Path:
    """Fill the form for one patient from the FHIR server and write <out>.pdf + <out>.md."""
    out = out or OUT_DIR / f"{patient_id}_zaver.pdf"
    sections = parse_template(TEMPLATE.read_text(encoding="utf-8"))
    resources = fhir.get_patient_record(patient_id)
    patient = next(r for r in resources if r["resourceType"] == "Patient")

    fill_header(sections["HEADER"], patient)
    print(f"{patient_id}: {len(resources)} FHIR resources → LLM call 1 (history)…", flush=True)
    fill_body(sections["BODY"], resources)
    print(f"{patient_id}: LLM call 2 (MDT recommendation)…", flush=True)
    rec = recommend(render_section(sections["BODY"]))

    created = datetime.now().strftime("%d.%m.%Y %H:%M")
    zaver = "\n".join(f"- {p}" for p in rec["doporuceni"]) + f"\nZdůvodnění: {rec['zduvodneni']}"
    md = (
        f"<!-- AI návrh ({settings.llm_model}, {created}) – nepotvrzeno lékařem; hlavička fiktivní -->\n"
        f"# HEADER\n{render_section(sections['HEADER'])}\n\n"
        f"# BODY\n{render_section(sections['BODY'], with_sources=True)}\n\n"
        f"# RESPONSE\nZávěr MDT:\n{zaver}\n"
    )
    out.parent.mkdir(parents=True, exist_ok=True)
    out.with_suffix(".md").write_text(md, encoding="utf-8")
    to_pdf(patient_id, sections, rec, out, created)
    unsourced = [f.path for f in leaves(sections["BODY"]) if _unsourced(f)]
    if unsourced:
        print(f"{patient_id}: ⚠ {len(unsourced)} field(s) {NO_SOURCE}: {'; '.join(unsourced)}")
    return out


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("patient_id")
    ap.add_argument("-o", "--out", type=Path, help="PDF path (default data/zavery/<id>_zaver.pdf)")
    args = ap.parse_args()
    print(create_zaver(args.patient_id, args.out))


if __name__ == "__main__":
    main()
