# Architecture

Current state of the system. Describe what **is**, not what's planned (plans go in `status.md`).

```
browser ──► frontend (Vite dev server :5173) ──/api──► backend (FastAPI :8000) ──► Dataset/ (bundles on disk)
                                                            │
                                                            ├──► FHIR server: HAPI :8080 or IRIS (/api/patients, CLI tools)
                                                            └──► LLM: Azure OpenAI gpt-6-luna-dz-eu (EU data zone, via APIM)
```

Domain context (how a real MDT runs, what the final record must hold) is in
[MDT_ZASEDANI_PROCES.md](MDT_ZASEDANI_PROCES.md); the full doc list is in [AGENTS.md](../AGENTS.md).

Deployed (`Dockerfile`): one container on :8000 — FastAPI serves `/api` and the built frontend
(`frontend/dist`, mounted in `app.py` when present). `Dataset/` is baked into the image (keep it in a
private registry); mount a volume at `/app/data/records`. Live on Fly.io:
https://mdt-copilot-rakathon.fly.dev (`fly.toml`, region `fra`, volume `records`, sleeps when idle).
`APP_PASSWORD` (Fly secret) turns on one shared HTTP basic-auth password for everything except
`/api/health`; unset (local dev) = no login.

## Workflow (what the UI is built around)

One linear journey for the coordinator (decision #20, [workflow-plan.md](workflow-plan.md)), one
screen per step and one **Další** each: Nahrání (`#/new`) → Komise → Pacient → Klíčové informace →
Vývoj → Léčebný záměr → Závěr → Potvrzení (`#/case/<id>/<step>`), plus Přehled (`#/`). Soulad s
doporučenými postupy is derived on the last screen (chosen léčebný záměr = recommended); on a
difference, Potvrdit first asks for důvod odchylky. Potvrdit is the board's consensus and locks
the conclusion; then Export: PDF (download rendered by the backend, `features/export.py`) or FHIR (not built yet).

Visual language: unconfirmed AI output is blue with a robot icon; examples standing in for AI
output are labelled "ukázka"; everything else (record data, clinician input) is plain text.

## Backend — `backend/src/mdt_backend/`

| File            | Role                                                                    |
|-----------------|-------------------------------------------------------------------------|
| `app.py`        | FastAPI app, route registration                                         |
| `config.py`     | Settings from env / `.env`                                              |
| `fhir.py`       | `get(path, **params)` → raw FHIR JSON; `get_patient_record(id)` → every resource of one patient (`Patient/$everything` + `Task?patient=`, which `$everything` misses); `print_patient_record(id)` / CLI `uv run mdt-patient P01` pretty-prints it |
| `llm.py`        | `chat_json(system, user, schema)`: one chat completion with strict JSON-schema output (`LLM_BASE_URL`, `LLM_MODEL`, `AZURE_API_KEY`) |
| `pdf.py`        | `PdfDoc`: flowing-text A4 PDF on pypdf (wrapping, pagination, bold/colour runs, blue AI bar); embeds a subset TrueType font for Czech (`PDF_FONT`/`PDF_FONT_BOLD`, default Arial/DejaVu) |
| `zaver.py`      | CLI `uv run mdt-zaver P01`: fills `docs/template_zaver_zasedani/form.md` → `data/zavery/<id>_zaver.{md,pdf}`. HEADER = dummy data (no LLM); BODY = LLM call 1 over the full FHIR record from the server (one field per template line + its source resources; unknown references dropped, unsourced fields flagged); RESPONSE = LLM call 2 over the filled BODY only, as the MDT. All LLM output marked as unconfirmed AI |
| `agent.py`      | CLI `uv run mdt-agent P01 [P03 …] \| --all [--runs 2] [--source iris\|file]`: the MDT agent (decisions 17, 18). Record from IRIS only (`$everything`, ids mapped back to the dataset's via the loader's `dataset-id` tag; `--source file` = bundle on disk, for offline use) → diagnosis → guideline docs (KRC/PLI/PRS + OBC) → LLM: completeness-and-consistency checklist (CACC) → LLM: RED/YELLOW findings → in parallel: LLM picks the indicators to chart (points read from the record, never from the model) and LLM extracts the patient's preferences → executive summary (LLM free text → LLM extracts key facts, extra red flags, timeline events) and per radiology/surgery/oncology: LLM picks records, agent fetches them from IRIS, LLM writes the view as text → LLM extracts cited points, verdict, missing data → LLM: 1–2 guideline options (+ patient preference, questions). Fills the `Case` the frontend already renders: `summary` (AI facts, then record facts), `red_flags`, `timeline`, `trends`, `sections` (preference leads `patient`), `decision_support`. LLM calls: at most 4 at once, 429 and 5xx retried with backoff (`llm.py`). Every citation checked (passage allowed for the diagnosis, reference in the record, quote verbatim) or dropped and logged. Output = `build_case` + AI statements → `data/ai_cases/<id>.json` (+ `.trace.json`), served by `/api/cases/{id}` when present |
| `load_fhir.py`  | CLI `uv run mdt-load-fhir`: loads `Dataset/fhir/bundles.ndjson` into the FHIR server as PUT transactions, repairing what strict R4 servers (IRIS) reject — see decision 12 |
| `provenance.py` | `Statement`, `Source`: AI-vs-human labelling, sources, confirmation     |
| `briefing.py`   | `Case`: the MDT briefing (summary, timeline, red flags, sections, decision support, trends) |
| `bundles.py`    | Reads FHIR bundles from `settings.dataset_dir / "pacienti"` (default `Dataset/`), resource accessors, full text of a record |
| `knowledge.py`  | Guideline passages (`Dataset/guidelines/*.md`) and trial criteria (`Dataset/studie/studie.json`) as verbatim `Source`s: `guideline:KRC-2.3`, `trial:RKT-01#Z2` |
| `from_fhir.py`  | Builds a `Case` from a bundle deterministically (no LLM): question, summary, timeline, sections, trends, previous MDT's board (`CareTeam`) |
| `rules.py`      | Rule-based red flags (`origin: "ai"`, model `pravidla-v1`): ECOG doctor vs patient, anaemia + fatigue, rising marker, worsening PROMs, new symptom, stale imaging |
| `features/cases.py` | Case list = patients on the FHIR server (IRIS). A case is one meeting: id = patient + planned MDT date (`p03-2026-10-21`, from `Task.restriction`), records are keyed by it; `GET /api/cases/{id}`: `data/ai_cases/<patient>.json` if the agent ran (id set to the meeting), else the IRIS record → `from_fhir`, else stub JSON from `data/stubs/`; `GET /api/sources/{type}/{id}`: full text of a record, read from IRIS by dataset id. Bundles on disk only while the server is unreachable (decision 18) |
| `features/intake.py` | `POST /api/intake` (one FHIR Bundle, base64 in JSON) → `data/intake/<patient>/bundle.json`, replacing that patient's dataset bundle; returns the case id. `kind: "pdf"` answers 501 until AI extraction exists |
| `features/records.py` | `CaseRecord` (confirmations, prep, specialist notes, decision, tasks; coordinator's board, finding triage, section layout + detail level, visibility per specialty; after the meeting: patient's stance, agreed plan), phase status, agenda |
| `features/history.py` | `GET /api/cases/{id}/history`: the patient's previous MDT records and treatment decisions from the health record (`Composition`, sections as text) and every meeting of the patient recorded in the app (status, decision). Read-only |
| `features/recommendation.py` | `GET /api/cases/{id}/recommendation`: the recommended postup to compare the conclusion with: `{intent, statement}` or null. ponytail: hand-written examples per dataset patient (`model: "ukázka"`) citing real guideline passages via `knowledge.py`, until the AI pipeline recommends |
| `features/export.py` | `GET /api/cases/{id}/zaver.pdf`: the confirmed conclusion as a PDF download (`pdf.PdfDoc`; question, board, léčebný záměr, postup, zdůvodnění, soulad, who confirmed); 409 before it's confirmed. Needs a TrueType font with Czech glyphs (DejaVu in the Docker image) |

Endpoints: `GET /api/health`, `GET /api/patients` (FHIR passthrough),
`GET /api/cases` (agenda: label, question, high-flag count, intent, `status` =
`prep`/`meeting`/`followup`/`closed`, board `specialties`; specialists see only their cases), `GET /api/cases/{id}` (`Case`),
`GET /api/cases/{id}/history` (patient's MDT history), `GET /api/cases/{id}/recommendation`, `GET /api/cases/{id}/zaver.pdf`, `GET|PUT /api/cases/{id}/record` (`CaseRecord`; 409 once the decision is locked, 422 when marking a
case prepared without an MDT question or with fewer than 3 specialties on the board, or locking
the decision while a board member doesn't support it), `GET /api/sources/{type}/{id}` (title, date, author, full
text of one record — for the source drawer; searches intake bundles too), `POST /api/intake` (upload a
case).

Statement origins: `record` = taken from the health record (ground truth, plain text in the UI),
`human` = written by a clinician (nomination question, notes), `ai` = machine proposal (blue,
needs confirmation). Guideline options and trial screening are empty until an LLM step fills them; it must
cite via `knowledge.py` (the frontend shows `guideline:`/`trial:` sources by their excerpt).

Confirmations are keyed by the statement's path in the briefing (`summary.0`,
`sections.surgery.2`, `trials.0.1`, …), so they stay valid only while the briefing's order is unchanged.

## Frontend — `frontend/src/`

| File                | Role                                                          |
|---------------------|---------------------------------------------------------------|
| `App.tsx`           | Shell: top bar (Přehled / Nový případ, user name), hash routing `#/`, `#/new`, `#/case/<id>/<step>` |
| `Overview.tsx`      | Přehled: cases, confirmed or in progress; opens where the work continues |
| `Intake.tsx`        | Step 1: FHIR bubble (pick or drop, uploads at once), PDF bubble greyed out |
| `Journey.tsx`       | Steps 2–8 for one case: board bubbles, patient, key facts (urgent red flags first), up to 3 trends, léčebný záměr bubbles, závěr, potvrzení (compare with the recommendation, stanoviska in a pop-up, důvod odchylky, Potvrdit), export (PDF = download of `GET /api/cases/{id}/zaver.pdf`, FHIR greyed out) |
| `Steps.tsx`         | Progress through the journey; finished steps link back        |
| `Stanoviska.tsx`    | Stance bubbles per board specialty (green supports / red doesn't, `Member.supports`), pop-up with the stanovisko (example text) and the specialty's facts; used on Závěr and Potvrzení |
| `Charts.tsx`        | `TrendChart` (SVG line + reference band; every point opens its source) |
| `StatementView.tsx` | Renders a `Statement` (`card` or `inline`); AI = blue + robot |
| `SourceDrawer.tsx` + `sources.ts` | Side panel with the exact source records; `useSources()` opens it |
| `render.tsx`        | `renderer`, `now` helpers                                     |
| `layout.ts`         | Labels (specialties, tumours, intents), journey `STEPS`, formatting, localStorage |
| `icons.tsx`         | Inline SVG icons (robot, intents, …)                          |
| `api.ts`            | Backend calls + TS mirror of records types                    |
| `provenance.ts` / `briefing.ts` | TS mirrors of backend models                      |

The user name lives in localStorage and signs the confirmation. Shared state lives in the backend.
Export = PDF download from `GET /api/cases/{id}/zaver.pdf`.

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
- `data/stubs/*.json`: hand-made `Case` briefings, validated by `backend/tests/test_stubs.py`. None
  now, so the folder doesn't exist (`cases.py` and the test treat it as empty). The fictional demo
  stubs were removed once the dataset was integrated.
- `data/records/*.json`: records written by the running app (git-ignored).
- `data/intake/<patient>/`: cases added through intake (git-ignored; not on the Fly volume, so lost
  on redeploy).
- `data/zavery/`: generated MDT conclusions (`mdt-zaver`, AI drafts, git-ignored).
- `data/ai_cases/`: AI-augmented briefings (`mdt-agent`, `Case` JSON + trace of every step and
  rejected citation, git-ignored). `/api/cases/{id}` serves these instead of the plain build.
- FHIR R4 on HAPI (H2 DB inside the container: survives restarts, wiped by `docker compose down`).
  The backend works with any FHIR R4
  server: set `FHIR_BASE_URL` (+ `FHIR_USER`/`FHIR_PASSWORD` for IRIS, see `.env.example`).
- InterSystems IRIS for Health (alternative FHIR server), from the sponsor kit in `FHIR-AI-Kit/`
  (container `iris-fhir`, FHIR at `http://localhost:52773/fhir/r4`, `SuperUser`/`SYS`, data in a
  Docker volume). Holds only our dataset (all 6 patients, via `mdt-load-fhir`), not the kit's
  Synthea samples. The container has restart policy `unless-stopped` (set with `docker update`;
  needs Docker Desktop running). It is the only patient-data source of `mdt-agent`, `mdt-zaver`
  and `mdt-patient`, and of the web API (case list, briefings, source drawer; decision 18), which
  falls back to the bundles on disk only while the server is unreachable.
  Known gap: `Practitioner/LEK-P05-09` is only named in `Procedure.note` text, never
  referenced, so `get_patient_record("P05")` can't reach it.
