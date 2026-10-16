# Architecture

Current state of the system. Describe what **is**, not what's planned (plans go in `status.md`).

```
browser ──► frontend (Vite dev server :5173) ──/api──► backend (FastAPI :8000) ──► HAPI FHIR (:8080)
                                                            │
                                                            └──► LLM: Azure OpenAI gpt-6-luna-dz-eu (EU data zone, via APIM)
```

## Workflow (what the UI is built around)

One user at the screen (the board chair or preparing clinician); no per-specialty views. Each case
goes through three phases, and any phase can be reopened at any time:

1. **Před zasedáním** (`prep`) — consolidated sources, problems (red flags + missing data), MDT
   question, discussion questions, confirming AI statements → "Připraveno k projednání".
2. **Zasedání** (`meeting`) — one low-clutter "slide" for the board: question, key facts, trend
   charts, timeline, options/trials, patient's voice; specialist sections expand for detail and
   the specialist's view (stored as a note).
3. **Po zasedání** (`followup`) — treatment intent + structured decision (chair locks it), action
   plan tasks, PDF export; full briefing alongside.

Visual language: unconfirmed AI output is blue with a robot icon; everything else (record data,
clinician input, confirmed AI) is plain text. Treatment intent has its own colour + icon.

## Backend — `backend/src/mdt_backend/`

| File            | Role                                                                    |
|-----------------|-------------------------------------------------------------------------|
| `app.py`        | FastAPI app, route registration                                         |
| `config.py`     | Settings from env / `.env`                                              |
| `fhir.py`       | `get(path, **params)` → raw FHIR JSON; `get_patient_record(id)` → every resource of one patient (`Patient/$everything` + `Task?patient=`, which `$everything` misses); `print_patient_record(id)` / CLI `uv run mdt-patient P01` pretty-prints it |
| `llm.py`        | `chat_json(system, user, schema)`: one chat completion with strict JSON-schema output (`LLM_BASE_URL`, `LLM_MODEL`, `AZURE_API_KEY`) |
| `pdf.py`        | `PdfDoc`: flowing-text A4 PDF on pypdf (wrapping, pagination, bold/colour runs, blue AI bar); embeds a subset TrueType font for Czech (`PDF_FONT`/`PDF_FONT_BOLD`, default Arial/DejaVu) |
| `zaver.py`      | CLI `uv run mdt-zaver P01`: fills `docs/template_zaver_zasedani/form.md` → `data/zavery/<id>_zaver.{md,pdf}`. HEADER = dummy data (no LLM); BODY = LLM call 1 over the full FHIR record from the server (one field per template line + its source resources; unknown references dropped, unsourced fields flagged); RESPONSE = LLM call 2 over the filled BODY only, as the MDT. All LLM output marked as unconfirmed AI |
| `load_fhir.py`  | CLI `uv run mdt-load-fhir`: loads `Dataset/fhir/bundles.ndjson` into the FHIR server as PUT transactions, repairing what strict R4 servers (IRIS) reject — see decision 12 |
| `provenance.py` | `Statement`, `Source`: AI-vs-human labelling, sources, confirmation     |
| `briefing.py`   | `Case`: the MDT briefing (summary, timeline, red flags, sections, decision support, trends) |
| `bundles.py`    | Reads FHIR bundles from `settings.dataset_dir / "pacienti"` (default `Dataset/`), resource accessors, full text of a record |
| `knowledge.py`  | Guideline passages (`Dataset/guidelines/*.md`) and trial criteria (`Dataset/studie/studie.json`) as verbatim `Source`s: `guideline:KRC-2.3`, `trial:RKT-01#Z2` |
| `from_fhir.py`  | Builds a `Case` from a bundle deterministically (no LLM): question, summary, timeline, sections, trends |
| `rules.py`      | Rule-based red flags (`origin: "ai"`, model `pravidla-v1`): ECOG doctor vs patient, anaemia + fatigue, rising marker, worsening PROMs, new symptom, stale imaging |
| `features/cases.py` | `GET /api/cases/{id}`: FHIR bundle → `from_fhir`, else stub JSON from `data/stubs/`; `GET /api/sources/{type}/{id}`: full text of a record |
| `features/records.py` | `CaseRecord` (confirmations, prep, specialist notes, decision, tasks), phase status, agenda |

Endpoints: `GET /api/health`, `GET /api/patients` (FHIR passthrough),
`GET /api/cases` (agenda: label, question, high-flag count, intent, `status` =
`prep`/`meeting`/`followup`/`closed`), `GET /api/cases/{id}` (`Case`),
`GET|PUT /api/cases/{id}/record` (`CaseRecord`; 409 once the decision is locked, 422 when marking a
case prepared without an MDT question), `GET /api/sources/{type}/{id}` (title, date, author, full
text of one record — for the source drawer).

Statement origins: `record` = taken from the health record (ground truth, plain text in the UI),
`human` = written by a clinician (nomination question, notes), `ai` = machine proposal (blue,
needs confirmation). Guideline options and trial screening are empty until an LLM step fills them; it must
cite via `knowledge.py` (the frontend shows `guideline:`/`trial:` sources by their excerpt).

Confirmations are keyed by the statement's path in the briefing (`summary.0`,
`sections.surgery.2`, `trials.0.1`, …), so they stay valid only while the stub's order is unchanged.

## Frontend — `frontend/src/`

| File                | Role                                                          |
|---------------------|---------------------------------------------------------------|
| `App.tsx`           | Shell: top bar (user name, board template dialog), hash routing `#/`, `#/case/<id>/<phase>` |
| `Home.tsx`          | Agenda: patient cards with phase steps (each phase links directly) |
| `CasePage.tsx`      | Loads case + record, phase stepper, saving (optimistic, rolls back on error) |
| `PrepPhase.tsx` / `MeetingPhase.tsx` / `FollowupPhase.tsx` | The three phases |
| `DecisionForm.tsx`  | Intent cards + structured decision; locked read-only view     |
| `CaseView.tsx`      | Shared blocks: flags, missing data, trials, full `CaseDetail` |
| `Charts.tsx`        | `TrendChart` (SVG line + reference band), `TimelineStrip`     |
| `StatementView.tsx` | Renders a `Statement` (`card` or `inline`); AI = blue + robot |
| `SourceDrawer.tsx` + `sources.ts` | Side panel with the exact source records; `useSources()` opens it |
| `render.tsx`        | `renderer`, `confirmer`, `isPending`, `missing` helpers       |
| `layout.ts`         | Labels (sections, tumours, intents, phases), board template, localStorage |
| `icons.tsx`         | Inline SVG icons (robot, intents, …)                          |
| `api.ts`            | Backend calls + TS mirror of records types                    |
| `provenance.ts` / `briefing.ts` | TS mirrors of backend models                      |

Per-browser settings (user name, board template) live in localStorage. Shared state lives in the
backend. Export = browser print-to-PDF (`@media print` in `index.css`).

## Data

- `Dataset/` (git-ignored): the organisers' dataset v1.1 — `pacienti/P0x_bundle.json` (6 synthetic
  FHIR R4 bundles), `guidelines/`, `studie/`, `dotaznik/` (Questionnaire `MDT-PROMS-1`),
  `fhir/bundles.ndjson` (same bundles, for bulk import). Its README is the reference; it mentions a
  `ground_truth/` folder that isn't delivered (yet). Override the location with `DATASET_DIR`. `P0x_pacient.md` is a readable rendering of the same records. Mapping notes: question =
  `ServiceRequest.reasonCode.text`; patient ECOG = PROMs item `samostatnost` (code 0–4); treatment
  history with real start dates = the nomination note "Předchozí onkologická léčba" (the bundle's
  MedicationAdministrations only cover recent doses); previous MDTs = `Composition` (`mdt-zaznam`); planned MDT date = `Task.restriction.period.start`
  (not `ServiceRequest.occurrenceDateTime`, which differs); Condition `category` text is
  `onkologická diagnóza` / `komorbidita` / `nežádoucí účinek léčby`.
- `data/stubs/*.json`: hand-made `Case` briefings, validated by `backend/tests/test_stubs.py`. Empty
  now — the fictional demo stubs were removed once the dataset was integrated.
- `data/records/*.json`: records written by the running app (git-ignored).
- `data/zavery/`: generated MDT conclusions (`mdt-zaver`, AI drafts, git-ignored).
- FHIR R4 on HAPI (H2 DB inside the container: survives restarts, wiped by `docker compose down`).
  The app itself still reads the bundles from disk. The backend works with any FHIR R4
  server: set `FHIR_BASE_URL` (+ `FHIR_USER`/`FHIR_PASSWORD` for IRIS, see `.env.example`).
- InterSystems IRIS for Health (alternative FHIR server), from the sponsor kit in `FHIR-AI-Kit/`
  (container `iris-fhir`, FHIR at `http://localhost:52773/fhir/r4`, `SuperUser`/`SYS`, data in a
  Docker volume). Holds only our dataset (all 6 patients, via `mdt-load-fhir`), not the kit's
  Synthea samples. Known gap: `Practitioner/LEK-P05-09` is only named in `Procedure.note` text, never
  referenced, so `get_patient_record("P05")` can't reach it.
