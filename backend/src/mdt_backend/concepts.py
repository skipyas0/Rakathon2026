"""Concept layer for the red-flag rules: maps whatever the record calls a thing (LOINC code, an
uncoded Observation's title, a PROMs linkId or question text, ATC code or drug name, ICD-10) onto
one controlled vocabulary, so rules are written once against concepts rather than dataset quirks.
`Facts` is everything the rules read, extracted from a bundle once."""

import datetime as dt
import re
from dataclasses import dataclass, field

from mdt_backend.bundles import (
    Bundle,
    answers,
    by_date,
    category_text,
    date_of,
    title_of,
    value_of,
)

# --- vocabularies -------------------------------------------------------------------------------
LABS: dict[str, tuple[str, ...]] = {  # concept → LOINC codes
    "hb": ("718-7", "30313-1"),
    "neutrophils": ("751-8", "26499-4", "753-3"),
    "platelets": ("777-3", "26515-7"),
    "wbc": ("6690-2", "26464-8"),
    "alt": ("1742-6", "1743-4"),
    "ast": ("1920-8",),
    "alp": ("6768-6",),
    "bilirubin": ("14631-6", "1975-2"),
    "albumin": ("1751-7",),
    "creatinine": ("14682-9", "2160-0"),
    "sodium": ("2951-2", "2947-0"),
    "potassium": ("2823-3", "6298-4"),
    "calcium": ("17861-6", "2000-8"),
    "glucose": ("15074-8", "2345-7", "2339-0"),
    "crp": ("1988-5",),
    "ld": ("14804-9", "2532-0"),
    "tsh": ("3016-3",),
    "cea": ("2039-6",),
    "ca15-3": ("6875-3",),
    "ca19-9": ("24108-3",),
    "ca125": ("10334-1",),
    "psa": ("2857-1", "83112-3"),
    "weight": ("29463-7",),
    "ecog": ("89247-1",),
    "lvef": ("10230-1", "8806-2", "18043-0"),
}
LABELS = {  # Czech display names for concepts named in flag texts
    "hb": "hemoglobin",
    "neutrophils": "neutrofily",
    "platelets": "trombocyty",
    "wbc": "leukocyty",
    "alt": "ALT",
    "ast": "AST",
    "bilirubin": "bilirubin",
    "creatinine": "kreatinin",
    "calcium": "kalcium",
    "glucose": "glykémie",
    "tsh": "TSH",
    "lvef": "LVEF",
    "sodium": "natrium",
    "potassium": "kalium",
}
MARKERS = {"cea", "ca15-3", "ca19-9", "ca125", "psa"}
NUMERIC = set(LABS) | {"ppo_fev1", "ppo_dlco", "fev1", "dlco"}
_BY_LOINC = {code: concept for concept, codes in LABS.items() for code in codes}

TITLES: list[tuple[str, str]] = [  # uncoded Observations: title regex → concept (first match)
    (r"\bLVEF\b|ejekční frakc", "lvef"),
    (r"^ppo\s*FEV1", "ppo_fev1"),
    (r"^ppo\s*DLCO", "ppo_dlco"),
    (r"^FEV1\b", "fev1"),
    (r"^DLCO\b", "dlco"),
    (r"^TNM|stadium|staging", "tnm"),
    (r"neuropati.*CTCAE|CTCAE.*neuropati", "ctcae_neuropathy"),
    (r"anémi.*CTCAE|CTCAE.*anémi", "ctcae_hb"),
    (r"neutropen.*CTCAE|CTCAE.*neutropen", "ctcae_neutrophils"),
    (r"trombocytopen.*CTCAE|CTCAE.*trombocytopen", "ctcae_platelets"),
    (r"kouřen|kuřá", "smoking"),
    (r"\bG8\b|geriatr|křehkost", "geriatric"),
    (r"ECOG|výkonnostní stav", "ecog"),
    (r"hmotnost|weight", "weight"),
]

PROMS: dict[str, tuple[tuple[str, ...], str]] = {  # concept → (linkIds, question-text regex)
    "pain": (("bolest",), r"^bolest"),
    "fatigue": (("unava",), r"únav"),
    "nausea": (("nevolnost",), r"nevolnost|zvracen"),
    "dyspnoea": (("dusnost",), r"dušnost"),
    "appetite": (("chut",), r"nechutenstv"),
    "neuropathy": (("brneni",), r"brnění|mravenčení|necitlivost"),
    "diarrhoea": (("prujem",), r"průjem"),
    "distress": (("psychika",), r"psychick|úzkost"),
    "sleep": (("spanek",), r"spánk"),
    "self_care": (("samostatnost",), r"běžný den|ECOG|samostatn"),
    "walking": (("chuze",), r"ujít|chůz"),
    "weight": (("hmotnost",), r"současná hmotnost"),
    "weight_change": (("hmotnost-zmena",), r"změna hmotnosti"),
    "new_symptoms": (("nove-obtize",), r"nové obtíže"),
    "pain_site": (("bolest-misto",), r"kde vás bolí"),
    "allergy": (("alergie",), r"alergi|nesnášenlivost"),
    "otc": (("leky-mimo",), r"doplňky|bylink|navíc"),
    "priority": (("priorita",), r"nejdůležitější"),
    "wishes": (("postoj",), r"přejete|postoj"),
}
FREE_TEXT = ("new_symptoms", "pain_site")  # PROMs items the symptom classifier reads

# Free-text symptom vocabulary (Czech stems). The keyword matcher is the offline fallback; the
# agent's LLM classifier maps to the same keys (handles negation, paraphrase, other languages).
SYMPTOMS: dict[str, str] = {
    "bone_pain": r"kyč|tříslo|kost|žebr|stehn|pánev|pánv|rameno|páteř",
    "back_pain": r"\bzáda\b|\bzad\b|bederní|páteř",
    "headache": r"\bhlav(a|u|y|ou|ě)\b|bolest\w* hlavy",
    "vision": r"rozmazan|dvojit|vidění|vidím",
    "neuro_deficit": r"ochrnut|slabost\w* (nohou|rukou|končetin)|nemůžu chodit|inkontinen|křeč",
    "confusion": r"zmaten|dezorient|zapomín",
    "dyspnoea": r"dušn|zadých|dýchá|dech",
    "cough": r"kašl|kašel",
    "haemoptysis": r"vykašl\w* krev|krev\w* při kašli|hemopt",
    "chest_pain": r"na hrudi|hrudník",
    "palpitations": r"buší|bušení|palpitac|nepravideln\w* tep",
    "oedema": r"otok|oteklé|otéká",
    "fever": r"horečk|teplot|zimnic",
    "bleeding": r"krvác|modřin",
    "jaundice": r"žlout|zežloutl|žluté oči",
    "nausea": r"nevoln|zvrac|špatně od žaludku",
    "appetite": r"nechutn|nechce se mi jíst|chuť k jídlu|chuť jíst",
    "weight_loss": r"zhubl|hubnu|úbytek hmotnosti",
    "fatigue": r"únav|vyčerpa",
    "neuropathy": r"brn|mravenč|necitliv",
    "neuropathy_functional": r"knofl|psaní|upouštím|držet|nejist\w* chůz|s holí",
    "diarrhoea": r"průjem",
    "abdominal_pain": r"břich|podbřiš",
    "rash": r"vyrážk|kopřivk",
}
SYMPTOM_LABELS = {
    "bone_pain": "bolest v oblasti skeletu",
    "back_pain": "bolest zad",
    "headache": "bolest hlavy",
    "vision": "porucha vidění",
    "neuro_deficit": "neurologický deficit",
    "confusion": "zmatenost",
    "dyspnoea": "dušnost",
    "cough": "kašel",
    "haemoptysis": "hemoptýza",
    "chest_pain": "bolest na hrudi",
    "palpitations": "palpitace",
    "oedema": "otoky",
    "fever": "horečka",
    "bleeding": "krvácení",
    "jaundice": "ikterus",
    "nausea": "nevolnost",
    "appetite": "nechutenství",
    "weight_loss": "úbytek hmotnosti",
    "fatigue": "únava",
    "neuropathy": "neuropatie",
    "neuropathy_functional": "neuropatie omezující běžné činnosti",
    "diarrhoea": "průjem",
    "abdominal_pain": "bolest břicha",
    "rash": "vyrážka",
}
NEGATIVE = re.compile(r"^\s*(nic|ne\b|nemám|žádn|bez (obtíží|potíží)|nevím o)", re.IGNORECASE)

DRUGS: dict[str, tuple[tuple[str, ...], str]] = {  # class → (ATC prefixes, name regex)
    "cdk46": (("L01EF",), r"palbocik|ribocik|abemacik"),
    "anti_her2": (("L01FD",), r"trastuzum|pertuzum|emtansin|deruxtek"),
    "anthracycline": (("L01DB",), r"doxorubic|epirubic"),
    "vegf": (("L01FG", "L01XX44"), r"bevacizum|ramucirum|aflibercept"),
    "oxaliplatin": (("L01XA03",), r"oxaliplat"),
    "platinum": (("L01XA",), r"cisplat|karboplat|carboplat|oxaliplat"),
    "taxane": (("L01CD",), r"paklitax|paclitax|docetax|kabazitax"),
    "fluoropyrimidine": (("L01BC02", "L01BC06", "L01BC53"), r"fluorouracil|kapecitab|capecitab"),
    "immunotherapy": (("L01FF",), r"pembroliz|nivolum|atezoliz|durvalum|ipilimum|cemiplim"),
    "parp": (("L01XK",), r"olapar|talazopar|niraparib|rukapar|PARP"),
    "bone_agent": (("M05BX04", "M05BA08"), r"denosum|zoledron"),
    "corticosteroid": (("H02AB",), r"dexametazon|prednison|methylprednis|hydrokortizon"),
    "endocrine": (("L02",), r"letrozol|anastrozol|exemestan|tamoxif|fulvestrant|elacestrant"),
}
SYSTEMIC = {
    "cdk46",
    "anti_her2",
    "anthracycline",
    "vegf",
    "platinum",
    "taxane",
    "fluoropyrimidine",
    "immunotherapy",
    "parp",
    "endocrine",
}
METASTASIS_ICD = re.compile(r"^C7[7-9]")
NOT_DONE = re.compile(
    r"nevyšetř|probíhá|nedostupn|nedostatek|neproveden|nehodnotiteln|chybí|nebyl", re.IGNORECASE
)


def num(text: str) -> float | None:
    """First number in free text, preferring one followed by % ("1,9 l (58 %)" → 58)."""
    m = re.search(r"(\d+(?:[,.]\d+)?)\s*%", text) or re.search(r"(\d+(?:[,.]\d+)?)", text)
    return float(m.group(1).replace(",", ".")) if m else None


def grade_of(text: str) -> int | None:
    m = re.search(r"(?:grade|stupe[nň]|G)\s*(\d)", text, re.IGNORECASE)
    return int(m.group(1)) if m else None


def classify(text: str) -> list[str]:
    """Keyword fallback: symptom concepts in a free-text answer, skipping negated clauses."""
    found: list[str] = []
    for clause in re.split(r"[.;,]|\ba\b|\bale\b", text):
        if not clause.strip() or NEGATIVE.match(clause):
            continue
        found += [
            c
            for c, rx in SYMPTOMS.items()
            if re.search(rx, clause, re.IGNORECASE) and c not in found
        ]
    return found


# --- facts ----------------------------------------------------------------------------------------
@dataclass
class Lab:
    concept: str
    label: str
    value: float
    unit: str
    low: float | None
    high: float | None
    date: dt.date | None
    r: dict


@dataclass
class Symptom:
    concept: str
    r: dict  # the QuestionnaireResponse (or other resource) it came from
    item: str | None
    excerpt: str
    new: bool


@dataclass
class Exposure:
    cls: str
    names: list[str]
    first: dt.date | None
    last: dt.date | None
    r: dict  # most recent administration / request
    current: bool


@dataclass
class Facts:
    b: Bundle
    mdt: dt.date
    age: int | None
    labs: dict[str, list[Lab]] = field(default_factory=dict)
    texts: dict[str, list[dict]] = field(default_factory=dict)  # concept → uncoded Observations
    biomarkers: list[dict] = field(default_factory=list)
    proms: list[dict] = field(default_factory=list)
    conditions: list[dict] = field(default_factory=list)
    drugs: dict[str, Exposure] = field(default_factory=dict)
    imaging: list[dict] = field(default_factory=list)
    symptoms: list[Symptom] = field(default_factory=list)

    def qa(self, i: int = -1) -> dict[str, tuple[str, str, dict]]:
        """concept → (linkId, question, answer) of the i-th questionnaire (by date)."""
        if not self.proms or abs(i) > len(self.proms) or i >= len(self.proms):
            return {}
        out = {}
        for link_id, (text, a) in answers(self.proms[i]).items():
            concept = prom_concept(link_id, text)
            if concept and concept not in out:
                out[concept] = (link_id, text, a)
        return out

    def icd(self, pattern: str) -> list[dict]:
        return [c for c in self.conditions if re.match(pattern, icd_of(c))]

    @property
    def metastatic(self) -> bool:
        if any(METASTASIS_ICD.match(icd_of(c)) for c in self.conditions):
            return True
        return any(re.search(r"\bc?M1|stadium IV", value_of(o)) for o in self.texts.get("tnm", []))

    @property
    def primary(self) -> str:
        onco = [c for c in self.conditions if re.match(r"^C(?!7[7-9])", icd_of(c))]
        return icd_of(onco[0]) if onco else ""


def prom_concept(link_id: str, text: str) -> str | None:
    for concept, (ids, rx) in PROMS.items():
        if link_id in ids:
            return concept
    return next((c for c, (_, rx) in PROMS.items() if re.search(rx, text, re.IGNORECASE)), None)


def icd_of(c: dict) -> str:
    return ((c.get("code") or {}).get("coding") or [{}])[0].get("code", "")


def drug_class(med: dict) -> list[str]:
    cc = med.get("medicationCodeableConcept") or {}
    codes = [c.get("code", "") for c in cc.get("coding", [])]
    name = " ".join([cc.get("text", "")] + [c.get("display", "") for c in cc.get("coding", [])])
    return [
        cls
        for cls, (atc, rx) in DRUGS.items()
        if any(code.startswith(a) for code in codes for a in atc)
        or re.search(rx, name, re.IGNORECASE)
    ]


UNIT_FACTORS = {  # (concept, unit lower-case) → factor to the units the thresholds use
    ("hb", "g/dl"): 10,
    ("albumin", "g/dl"): 10,
    ("glucose", "mg/dl"): 1 / 18,
    ("calcium", "mg/dl"): 1 / 4.008,
    ("creatinine", "mg/dl"): 88.4,
    ("bilirubin", "mg/dl"): 17.1,
}


def _lab(concept: str, o: dict) -> Lab | None:
    q = o.get("valueQuantity") or {}
    if "value" in q:
        value = float(q["value"])
    elif "valueInteger" in o:
        value = float(o["valueInteger"])
    elif "valueString" in o and (v := num(o["valueString"])) is not None:
        value = v
    else:
        return None
    unit = q.get("unit") or q.get("code") or ("%" if "%" in o.get("valueString", "") else "")
    f = UNIT_FACTORS.get((concept, unit.lower()), 1)
    rr = (o.get("referenceRange") or [{}])[0]
    low, high = (rr.get(k, {}).get("value") for k in ("low", "high"))
    return Lab(
        concept=concept,
        label=title_of(o),
        value=value * f,
        unit=unit,
        low=low * f if low is not None else None,
        high=high * f if high is not None else None,
        date=date_of(o),
        r=o,
    )


def facts(b: Bundle, mdt: dt.date | None, symptoms: list[Symptom] | None = None) -> Facts:
    dated = [d for r in b.by_ref.values() if (d := date_of(r))]
    patient = (b.all("Patient") or [{}])[0]
    age = next((e["valueInteger"] for e in patient.get("extension", []) if "vek" in e["url"]), None)
    mdt = mdt or (max(dated) if dated else dt.date.today())
    if age is None and patient.get("birthDate"):
        age = mdt.year - int(patient["birthDate"][:4])
    f = Facts(b=b, mdt=mdt, age=age, conditions=b.all("Condition"))

    for o in by_date(b.all("Observation")):
        concept = _BY_LOINC.get(((o.get("code") or {}).get("coding") or [{}])[0].get("code", ""))
        title = title_of(o)
        if not concept:
            concept = next((c for rx, c in TITLES if re.search(rx, title, re.IGNORECASE)), None)
        if concept in NUMERIC and (lab := _lab(concept, o)):
            f.labs.setdefault(concept, []).append(lab)
        if concept and "valueString" in o:
            f.texts.setdefault(concept, []).append(o)
        elif not concept and "valueString" in o and "biomarker" in category_text(o).lower():
            f.biomarkers.append(o)
        elif not concept and "valueString" in o:
            f.texts.setdefault("other", []).append(o)

    f.proms = by_date(b.all("QuestionnaireResponse"))
    reports = by_date(b.all("DiagnosticReport"))
    f.imaging = [
        r for r in reports if re.search(r"zobraz|imaging|radiol", category_text(r), re.IGNORECASE)
    ]
    f.imaging = by_date(f.imaging + b.all("ImagingStudy"))

    meds = b.all("MedicationAdministration") + b.all("MedicationStatement")
    meds += [m for m in b.all("MedicationRequest") if m.get("status") in ("active", None)]
    for m in by_date(meds):
        for cls in drug_class(m):
            d = date_of(m)
            name = (m.get("medicationCodeableConcept") or {}).get("text", cls)
            e = f.drugs.get(cls)
            if not e:
                f.drugs[cls] = e = Exposure(cls, [], d, d, m, False)
            e.names += [name] if name not in e.names else []
            e.last, e.r = (d, m) if d and (not e.last or d >= e.last) else (e.last, e.r)
            # an active prescription counts as current; administrations must be recent
            if m["resourceType"] == "MedicationRequest" or (d and (mdt - d).days <= 60):
                e.current = True

    f.symptoms = symptoms if symptoms is not None else keyword_symptoms(f)
    return f


def free_text_answers(f: Facts) -> list[tuple[dict, str, str, str, str]]:
    """(questionnaire, linkId, concept, question, answer) for the classifier: latest PROMs only."""
    out = []
    for concept, (link_id, text, a) in f.qa(-1).items():
        if concept in FREE_TEXT and value_of(a).strip():
            out.append((f.proms[-1], link_id, concept, text, value_of(a).strip()))
    return out


def keyword_symptoms(f: Facts) -> list[Symptom]:
    before = f.qa(-2)
    out = []
    for qr, link_id, concept, _, answer in free_text_answers(f):
        prev = value_of(before[concept][2]) if concept in before else ""
        prev_found = set(classify(prev))
        for s in classify(answer):
            if concept == "new_symptoms":
                new = not NEGATIVE.match(answer)
            else:  # a pain site the previous questionnaire didn't mention
                new = s not in prev_found
            out.append(Symptom(s, qr, link_id, answer, new))
    return out
