"""The recommended postup the board's conclusion is compared with (soulad s doporučenými postupy).

ponytail: hand-written examples ("ukázka") per dataset patient until the AI pipeline recommends
from the guidelines. Each paraphrases and cites a real passage from Dataset/guidelines (verbatim
text via knowledge.py), so the source is one click away. Not clinical advice."""

from fastapi import APIRouter

from mdt_backend.features import cases
from mdt_backend.knowledge import guideline_source
from mdt_backend.provenance import Statement

router = APIRouter(prefix="/api/cases")

# patient → (léčebný záměr, postup, cited guideline passages)
EXAMPLES: dict[str, tuple[str, str, list[str]]] = {
    "p01": (
        "palliative",
        (
            "Doplnit ESR1 a PIK3CA/AKT1/PTEN z ctDNA a podle výsledku zvolit další endokrinní linii; "
            "při endokrinní rezistenci trastuzumab deruxtekan (HER2-low)."
        ),
        ["PRS-2.2", "PRS-2.3"],
    ),
    "p02": (
        "palliative",
        "Stereotaktická radioterapie mozkových metastáz a pokračování dosavadní anti-HER2 léčby.",
        ["PRS-3.3"],
    ),
    "p03": (
        "curative",
        (
            "Kompletní restaging (CT, MR jater) a resekce jaterních metastáz bez dalšího prodlužování "
            "chemoterapie; bevacizumab vysadit nejméně 6 týdnů před operací."
        ),
        ["KRC-2.2", "KRC-2.3", "KRC-2.4"],
    ),
    "p04": (
        "curative",
        (
            "Anatomická resekce (lobektomie) po neoadjuvantní chemoimunoterapii, je-li pacient funkčně "
            "operabilní."
        ),
        ["PLI-2.2", "PLI-3.1"],
    ),
    "p05": (
        "palliative",
        (
            "Pokračovat v léčbě se sníženou dávkou podle protokolu studie; doplnit genetické "
            "poradenství a ověření germinální varianty BRCA2."
        ),
        ["PRS-1.4", "PRS-1.3"],
    ),
    "p06": (
        "palliative",
        (
            "Rebiopsie rostoucího plicního ložiska k odlišení metastázy od druhého nádoru; do výsledku "
            "pokračovat v anti-HER2 léčbě."
        ),
        ["PRS-1.1", "PRS-3.2"],
    ),
}


@router.get("/{case_id}/recommendation")
def recommendation(case_id: str) -> dict | None:
    """{intent, statement} for the case's patient, or null when there is none to compare with."""
    patient = cases.get_case(case_id).patient.split("/")[-1].lower()  # 404 for an unknown case
    if patient not in EXAMPLES:
        return None
    intent, text, passages = EXAMPLES[patient]
    s = Statement(
        text=text,
        origin="ai",
        model="ukázka",
        sources=[guideline_source(p) for p in passages],
    )
    return {"intent": intent, "statement": s}
