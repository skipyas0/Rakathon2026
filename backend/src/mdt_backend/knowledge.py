"""The dataset's decision-support documents: guideline passages (guidelines/*.md) and fictional
trials with their criteria (studie/studie.json). Gives verbatim text as `Source`s, so whatever
proposes options or screens trials cites the exact passage / criterion.
Reference formats: `guideline:KRC-2.3` (passage id as the dataset says to cite it) and
`trial:RKT-01#Z2` (trial id + criterion id; Z = inclusion, V = exclusion)."""

import json
import re
from functools import cache

from mdt_backend.config import settings
from mdt_backend.provenance import Source

# "**KRC-2.3 – Title.** text…" up to the next passage or section heading
PASSAGE = re.compile(
    r"^\*\*(?P<id>[A-Z]{3}-\d+\.\d+) – (?P<title>.+?)\.\*\* (?P<text>.+?)(?=^\*\*[A-Z]{3}-|^#|\Z)",
    re.MULTILINE | re.DOTALL,
)


@cache  # ponytail: read once per process; restart the backend after editing the dataset
def guidelines() -> dict[str, dict]:
    """Passage id → {doc, title, text}."""
    out = {}
    for path in sorted((settings.dataset_dir / "guidelines").glob("*.md")):
        md = path.read_text("utf-8")
        doc = md.splitlines()[0].removeprefix("# ")
        for m in PASSAGE.finditer(md):
            out[m["id"]] = {"doc": doc, "title": m["title"], "text": " ".join(m["text"].split())}
    return out


@cache
def trials() -> dict[str, dict]:
    """Trial id → the trial as in studie.json (zarazeni / vyrazeni = inclusion / exclusion)."""
    path = settings.dataset_dir / "studie" / "studie.json"
    data = json.loads(path.read_text("utf-8")) if path.exists() else {"studie": []}
    return {t["id"]: t for t in data["studie"]}


def guideline_source(passage_id: str) -> Source:
    p = guidelines()[passage_id]
    return Source(
        reference=f"guideline:{passage_id}",
        title=f"{p['doc']} – {passage_id} {p['title']}",
        excerpt=p["text"],
    )


def trial_source(trial_id: str, criterion_id: str) -> Source:
    t = trials()[trial_id]
    c = next(c for c in t["zarazeni"] + t["vyrazeni"] if c["id"] == criterion_id)
    kind = "zařazení" if criterion_id.startswith("Z") else "vyřazení"
    return Source(
        reference=f"trial:{trial_id}#{criterion_id}",
        title=f"{trial_id} {t['akronym']} – kritérium {kind} {criterion_id}",
        excerpt=c["text"],
    )
