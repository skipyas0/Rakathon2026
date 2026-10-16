# Preparing case stubs for the frontend demo

**Audience:** coding agents (and people) writing MDT briefings by hand.

> **Update:** the organisers' FHIR bundles (`Dataset/pacienti/`) are now converted
> automatically by `backend/src/mdt_backend/from_fhir.py`. Hand-made stubs are only needed for
> content the converter can't produce yet (guideline options, trial screening, AI questions) or for
> extra demo scenarios. Prefer improving the converter over writing stubs.

A stub is the exact JSON the backend's AI pipeline will produce later. Get the shape right and the
frontend works unchanged when the real pipeline replaces the stubs.

## The contract

- One file per patient case: `data/stubs/<case-id>.json` (lowercase, hyphenated, e.g.
  `crc-progression.json`). The folder doesn't exist while there are no stubs; create it. The `id` field must equal the filename without `.json`.
- Shape: `Case` in [backend/src/mdt_backend/briefing.py](../backend/src/mdt_backend/briefing.py),
  built from `Statement` in [provenance.py](../backend/src/mdt_backend/provenance.py).
  As a template, save a generated case: `curl localhost:8000/api/cases/p03 > data/stubs/<id>.json`.
- Validate before committing: `cd backend && uv run pytest tests/test_stubs.py`.
- The stub is served at `GET /api/cases/<case-id>` (start the backend with `uv run mdt-backend`).

If you need a field the contract doesn't have, **don't add it to your JSON only**. Change
`briefing.py` and `frontend/src/briefing.ts` together in your PR and add an entry to
[decisions.md](decisions.md). The test rejects unknown shapes, so a silent mismatch can't happen.

## Rules for every `Statement`

Every sentence a clinician will read is a `Statement`. These rules come from the brief and are
checked by the validator:

Use `origin: "record"` for facts copied from the health record (with a source, no model), `"ai"`
for anything interpreted or summarised by a machine, `"human"` for clinician-written text.

| Field          | AI-prepared content                            | Human content (the MDT question) |
|----------------|-----------------------------------------------|----------------------------------|
| `origin`       | `"ai"`                                         | `"human"`                        |
| `model`        | `"stub"` (marks it as hand-made)              | omit                             |
| `sources`      | at least 1, see below                         | the nomination record            |
| `confirmed_by` | omit (the clinician confirms it in the app)   | name of the referring doctor     |

- **Sources point to real records in the dataset.** `reference` is `ResourceType/id` using the id
  from the organisers' FHIR data (e.g. `Observation/abc-123`). For a single questionnaire answer
  use `QuestionnaireResponse/<id>#<linkId>`. For guidelines use `guideline:<passage-id>`
  (e.g. `guideline:KRC-2.3`) and for trials `trial:<trial-id>#<criterion-id>` (e.g. `trial:RKT-01#Z2`,
  Z = inclusion, V = exclusion). `knowledge.py` builds these sources with the verbatim text.
- **`excerpt` is the verbatim passage** from that record (the UI highlights it when clicked). Copy
  it; don't paraphrase. Add `date` and `author` when the record has them.
- **Missing data:** if something isn't in the records, name it and end with the exact wording,
  e.g. `"Stav MSI/MMR: V dostupné dokumentaci se nenachází."`, with `sources: []`. Never fill gaps from general
  medical knowledge. Gaps are a feature the demo needs to show.
- **No question in the nomination → `"question": null`.** That marks the case as incomplete. Don't
  invent a question.
- Write the text in Czech: short, clinical, one fact per statement.

## What to put in each part

Follow the brief, section 2 ([brief.md](brief.md)). Aim for the brief's demo flow: a 30-second
summary, at least one red flag you can click through to both sources, and a decision panel with
cited options.

| Field              | Content                                                                         |
|--------------------|---------------------------------------------------------------------------------|
| `summary`          | 3–6 statements: diagnosis, current state, ECOG from the doctor **and** the patient, reason for MDT |
| `timeline`         | diagnosis, staging, surgery, systemic lines, RT, key imaging, progression, previous MDTs (`kind` must be one of these values) |
| `red_flags`        | inconsistencies with `severity`; **each cites both sources** (e.g. lab + questionnaire). The test enforces ≥ 2 sources |
| `sections`         | at least 3 of `surgery`, `oncology`, `radiology`, `pathology`, `patient` (PROMs, goals, preferences) |
| `decision_support` | `options` cite a guideline passage; `trials` give one criterion statement each with `eligible` / `ineligible` / `missing_data`; 2–3 `questions` |
| `trends`           | measured values over time for the meeting charts (see below). Not AI: copy the numbers from the records |

### Trends (charts on the meeting screen)

Pick the 2–4 series that matter for the MDT question: tumour markers (CEA, CA 19-9, PSA…), a
lab tied to a red flag (e.g. Hb), and PROMs scores with at least two time points. Each point needs
its own source (the exact `Observation` or `QuestionnaireResponse#linkId`), so clicking a dot opens it.

```json
{ "id": "cea", "label": "CEA", "unit": "µg/l", "ref_high": 5.0,
  "points": [{ "date": "2026-07-01", "value": 6.1,
               "source": { "reference": "Observation/abc", "excerpt": "CEA 6,1 µg/l", "date": "2026-07-01" } }] }
```

Use `ref_low` / `ref_high` for the reference range (drawn as a band). For questionnaire scales,
set `"axis": [0, 10]` so the chart shows the full scale.

The brief says the dataset has deliberate inconsistencies and gaps with ground-truth answers. Make
sure each stub surfaces the ones for its patient. Those are what the judges will click.

## Hygiene

- Synthetic data only. Never put real patient data in the repo.
- The dataset lives in `Dataset/` (git-ignored; not in git until we know the organisers allow redistribution).
- Add your stub work to your section of [status.md](status.md) (which patients, what's done).
