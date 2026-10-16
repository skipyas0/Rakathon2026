# Decisions

Append-only log. Newest at the bottom. To roll a decision back, add a new entry that says
"Supersedes #N" and why — don't edit or delete old entries.

Template:

```
## N. Title — YYYY-MM-DD, <who>
Status: accepted | superseded by #M
Decision: …
Why: …
```

## 1. Stack — 2026-10-16, initial setup
Status: accepted
Decision: Python 3.13 + FastAPI (uv) backend, TypeScript + React (Vite) frontend, HAPI FHIR R4
server via docker compose.
Why: FHIR server gives standard storage/search for the provided mock data; FastAPI/Pydantic give
typed models for provenance; Vite is the minimal TS setup.

## 2. Provenance is a type, not a convention — 2026-10-16, initial setup
Status: accepted
Decision: All clinical content flows as `Statement` (backend `provenance.py`, frontend
`provenance.ts`) and is rendered only by `StatementView`.
Why: The brief's ground rules (label AI output, cite sources, human confirmation) must hold
everywhere; enforcing them in one model is easier than reviewing every feature for them.

## 3. One shared instructions file for all agents — 2026-10-16, initial setup
Status: accepted
Decision: `AGENTS.md` is the single source of agent instructions; `CLAUDE.md` and `GEMINI.md`
just import it.
Why: Three contributors use three different agents; one file prevents divergent rules.

## 4. Squash-merge PRs — 2026-10-16, initial setup
Status: accepted
Decision: Work on `<contributor>/<topic>` branches, PR into `main`, squash-merge.
Why: Fast iteration with frequent rollbacks — one commit per feature makes `git revert` trivial.

## 5. Stubs share the AI pipeline's output shape — 2026-10-16, initial setup
Status: accepted
Decision: Hand-made briefings in `data/stubs/` validate against `Case` (`briefing.py`) and are
served by `/api/cases`. The AI pipeline will return the same shape.
Why: Frontend and data work can run in parallel; swapping stubs for real output needs no frontend
change.

## 6. MDT records as JSON files per case — 2026-10-16, yes-and
Status: accepted
Decision: Confirmations and the board's decision are stored in `data/records/<case>.json` via
`GET|PUT /api/cases/{id}/record`; the chair's confirmation locks the decision (409 on change).
Why: Fastest persistent store for the demo. Replace with FHIR CarePlan/Task/Provenance (brief
BONUS) or a DB when export is built — the API shape can stay.

## 7. "Not found" statements name what is missing — 2026-10-16, yes-and
Status: accepted
Decision: An unsourced AI statement must *end with* `V dostupné dokumentaci se nenachází.`
(e.g. `Stav MSI/MMR: V dostupné dokumentaci se nenachází.`) instead of being exactly that text.
Why: A bare "not found" doesn't tell the clinician what is missing.

## 8. Three-phase workflow, single chair view — 2026-10-16, yes-and
Status: accepted (supersedes the role-based views from the first demo)
Decision: Each case has phases Před zasedáním → Zasedání → Po zasedání, all reopenable. Only the
chair has the app open during the meeting, so there are no per-specialty views; specialist
sections expand on demand and store the specialist's view as a note. Section order/visibility is a
per-board template.
Why: Matches how the MDT actually runs (one shared screen, 3–5 min per patient).

## 9. Trends in the Case contract; AI shown in blue — 2026-10-16, yes-and
Status: accepted
Decision: `Case.trends` (optional) carries measured values with per-point sources for charts.
Unconfirmed AI output is blue with a robot icon; record data, clinician input and confirmed AI
render as plain text. Treatment intent (curative/palliative/supportive/surveillance) is part of
the decision and has its own colour + icon everywhere.
Why: Quick orientation on one screen; the brief requires AI output to be visually distinct.

## 10. Briefings built from FHIR bundles without an LLM — 2026-10-16, yes-and
Status: accepted
Decision: `from_fhir.py` builds `Case` deterministically from the organisers' bundles; red flags
come from fixed rules (`rules.py`, shown as AI proposals). New contract fields driven by the data:
`Statement.origin = "record"`, `Source.title`, timeline kind `pathology`, `Case.board`,
`Case.mdt_date`, decision intent `deferred` (the dataset's `odlozeno`).
Why: Most of the briefing is structured in the data already; deterministic extraction is exact,
fast and cites its sources. The LLM can later add what rules can't (guideline options, trials,
questions, narrative summary) into the same `Case`.

## 11. Dataset in `Dataset/`, fictional stubs removed — 2026-10-16, yes-and
Status: accepted (supersedes the `data_trial/` location from #10)
Decision: The organisers' dataset v1.1 lives in `Dataset/` at the repo root (git-ignored, as on
`main`); `settings.dataset_dir` / `DATASET_DIR` points at it. Guideline and trial citations use
`guideline:<passage-id>` (e.g. `guideline:KRC-2.3`) and `trial:<trial-id>#<criterion-id>` (e.g.
`trial:RKT-01#Z2`), built by `knowledge.py` with verbatim text. The fictional stubs (`example`,
`lung-incomplete`) are deleted; tests create their own cases. The planned MDT date is
`Task.restriction.period.start`.
Why: One dataset location for everyone; citation ids are the ones the dataset tells us to cite; the
fictional cases would mix made-up guidelines/trials with the real ones.

## 12. Loading the dataset into a FHIR server (IRIS) — 2026-10-16
Status: accepted
Decision: `mdt-load-fhir` sends each `collection` bundle as a `transaction` of PUTs (keeps the
dataset IDs, reload is idempotent). Three R4 violations that IRIS rejects are repaired on load:
IDs with `_` get `-` instead (26 Observations, e.g. `P01-lab01-hb_f` → `P01-lab01-hb-f`, with
references rewritten); `Observation.derivedFrom` → `DiagnosticReport` (44×, type not allowed) moves
to extension `https://rakathon.example.org/fhir/StructureDefinition/derived-from-report` with the same
`valueReference`; one empty `valueString` answer (P03-prom02 `bolest-misto`) is dropped.
Why: Strict servers refuse the raw bundles; these repairs are lossless, so source links still work.
Code that reads from the server must use the repaired IDs and the extension, not the raw ones.

## 13. LLM: Azure OpenAI gpt-6-luna (EU data zone) with strict structured output — 2026-10-16
Status: accepted
Decision: LLM calls go to `gpt-6-luna-dz-eu` behind the hackathon Azure APIM
(`https://apim-rakathon-q7146n.azure-api.net/openai/v1`, OpenAI-compatible, key in the `api-key`
header, `AZURE_API_KEY` in `.env`), through `llm.chat_json` only, always with a strict JSON schema.
Plain httpx, no SDK. Model output that cites FHIR resources is checked against the record; unknown
IDs are dropped. PDFs are rendered with pypdf + an embedded subset TrueType font (pypdf's built-in
fonts can't encode Czech).
Why: EU data zone answers the brief's data-residency question; schema-constrained output gives
parseable, field-by-field answers with sources (ground rule 3).
