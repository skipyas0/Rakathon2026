# Architecture

Current state of the system. Describe what **is**, not what's planned (plans go in `status.md`).

```
browser ──► frontend (Vite dev server :5173) ──/api──► backend (FastAPI :8000) ──► IRIS for Health :52773/fhir/r4
                                                            │                        (all patient data)
                                                            ├──► Dataset/guidelines, studie (knowledge base)
                                                            └──► LLM: Azure OpenAI gpt-6-luna-dz-eu (EU data zone, via APIM)
```

Domain context (how a real MDT runs, what the final record must hold) is in
[MDT_ZASEDANI_PROCES.md](MDT_ZASEDANI_PROCES.md); the full doc list is in [AGENTS.md](../AGENTS.md).

Deployed (`Dockerfile`): one container on :8000 — FastAPI serves `/api` and the built frontend
(`frontend/dist`, mounted in `app.py` when present). The dataset's `guidelines/` + `studie/` and the
agent's briefings (`data/ai_cases/`, without traces) are baked into the image (keep it in a private
registry); mount a volume at `/app/data/records`. Live on Fly.io:
https://mdt-copilot-rakathon.fly.dev (`fly.toml`, region `fra`, volume `records`, sleeps when idle).
IRIS runs as a second, private Fly app (`iris/fly.toml`: `mdt-copilot-iris`, 2 GB, volume
`iris_data`, no public port), reached at `mdt-copilot-iris.internal:52773` over Fly's private
network. Locally `docker-compose.yml` runs the same pair.
`APP_PASSWORD` (Fly secret) turns on one shared HTTP basic-auth password for everything except
`/api/health`; unset (local dev) = no login. `/api/health` answers 200 while the app runs and says
whether IRIS answers (`fhir: true/false`); every patient-data endpoint answers 503 while it doesn't.

## Workflow (what the UI is built around)

One linear journey for the coordinator (decision #20, [workflow-plan.md](workflow-plan.md)), one
screen per step and one **Další** each: Nahrání (`#/new`) → Komise → Pacient → Klíčové informace →
Vývoj → Otázky k diskusi → Léčebný záměr → Závěr → Potvrzení (`#/case/<id>/<step>`), plus Přehled (`#/`). Soulad s
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
| `iris/` (repo root) | IRIS for Health image (`intersystems/irishealth-community:2026.1`). `setup.script` runs after IRIS starts (`iris-main --after`): sets the password of SuperUser/_SYSTEM/Admin from `IRIS_PASSWORD` (default `SYS`) and, on a fresh data volume, creates namespace `FHIRSERVER` with the R4 endpoint `/fhir/r4` (JsonAdvSQL storage) — the same as the sponsor kit's `create_fhir_server()`, without its sample patients |
| `fhir.py`       | `get(path, **params)` → raw FHIR JSON; `get_patient_record(id)` → every resource of one patient (`Patient/$everything` + `Task?patient=`, which `$everything` misses); `print_patient_record(id)` / CLI `uv run mdt-patient P01` pretty-prints it |
| `llm.py`        | `chat_json(system, user, schema)`: one chat completion with strict JSON-schema output (`LLM_BASE_URL`, `LLM_MODEL`, `AZURE_API_KEY`) |
| `pdf.py`        | `PdfDoc`: flowing-text A4 PDF on pypdf (wrapping, pagination, bold/colour runs, blue AI bar); embeds a subset TrueType font for Czech (`PDF_FONT`/`PDF_FONT_BOLD`, default Arial/DejaVu) |
| `zaver.py`      | CLI `uv run mdt-zaver P01`: fills `docs/template_zaver_zasedani/form.md` → `data/zavery/<id>_zaver.{md,pdf}`. HEADER = dummy data (no LLM); BODY = LLM call 1 over the full FHIR record from the server (one field per template line + its source resources; unknown references dropped, unsourced fields flagged); RESPONSE = LLM call 2 over the filled BODY only, as the MDT. All LLM output marked as unconfirmed AI |
| `agent.py`      | CLI `uv run mdt-agent P01 [P03 …] \| --all [--runs 2]`: the MDT agent (decisions 17, 18). Record from IRIS only (`$everything`, ids mapped back to the dataset's via the loader's `dataset-id` tag) → diagnosis → guideline docs (KRC/PLI/PRS + OBC) → LLM: completeness-and-consistency checklist (CACC) → LLM: RED/YELLOW findings → in parallel: LLM picks the indicators to chart (points read from the record, never from the model) and LLM extracts the patient's preferences → executive summary (LLM free text → LLM extracts key facts, extra red flags, timeline events) and per radiology/surgery/oncology: LLM picks records, agent fetches them from IRIS, LLM writes the view as text → LLM extracts cited points, verdict, missing data → LLM: 1–2 guideline options, each with its léčebný záměr (+ patient preference, questions). Fills the `Case` the frontend already renders: `summary` (AI facts, then record facts), `red_flags`, `timeline`, `trends`, `sections` (preference leads `patient`), `decision_support`. LLM calls: at most 4 at once, 429 and 5xx retried with backoff (`llm.py`). Every citation checked (passage allowed for the diagnosis, reference in the record, quote verbatim) or dropped and logged. While a patient runs, `data/ai_cases/<id>.running` exists (the app shows "AI připravuje…"). Output = `build_case` + AI statements → `data/ai_cases/<id>.json` (+ `.trace.json`), served by `/api/cases/{id}` when present |
| `load_fhir.py`  | CLI `uv run mdt-load-fhir`: loads `Dataset/fhir/bundles.ndjson` into the FHIR server as PUT transactions, repairing what strict R4 servers (IRIS) reject — see decision 12 |
| `provenance.py` | `Statement`, `Source`: AI-vs-human labelling, sources, confirmation     |
| `briefing.py`   | `Case`: the MDT briefing (summary, timeline, red flags, sections, decision support, trends) |
| `bundles.py`    | `Bundle`: one patient's resources in memory (built from IRIS by `agent.Record`), resource accessors, full text of a record |
| `knowledge.py`  | Guideline passages (`Dataset/guidelines/*.md`) and trial criteria (`Dataset/studie/studie.json`) as verbatim `Source`s: `guideline:KRC-2.3`, `trial:RKT-01#Z2` |
| `from_fhir.py`  | Builds a `Case` from a bundle deterministically (no LLM): question, summary, timeline, sections, trends, previous MDT's board (`CareTeam`); optional classified symptoms feed the v2 rules |
| `concepts.py`   | Concept layer for the rules: LOINC (+ aliases) / uncoded titles / PROMs linkId or question / ATC or drug name / ICD-10 → one vocabulary; `Facts` extracted once per bundle; keyword symptom classifier (offline fallback) |
| `rules.py`      | Rule-based red flags (`origin: "ai"`, model `pravidla-v2:<rule>`, decision 19): families A–H (abnormal values, trends, discordance, corroboration, drug monitoring, alarm symptoms, stale/missing data, context), each citing record sources and its guideline passage |
| `rules.toml`    | Thresholds, severities, drug classes and guideline ids for every rule; override with `RULES_CONFIG=<file>` |
| `features/cases.py` | Case list = patients on the FHIR server (IRIS). A case is one meeting: id = patient + planned MDT date (`p03-2026-10-21`, from `Task.restriction`), records are keyed by it; `GET /api/cases/{id}`: `data/ai_cases/<patient>.json` if the agent ran (id set to the meeting), else the IRIS record → `from_fhir`; `GET /api/sources/{type}/{id}`: full text of a record, read from IRIS by dataset id. IRIS unreachable → 503 (decision 24) |
| `features/intake.py` | `POST /api/intake` (one FHIR Bundle, base64 in JSON) → validated (a `Case` must build from it) → into IRIS (`load_fhir.put`); returns the case id. IRIS unreachable → 503, bundle rejected by IRIS → 422; nothing is stored elsewhere. Resources of an earlier upload missing from the new one stay (needs patient deletion, not built). `kind: "pdf"` answers 501 until AI extraction exists |
| `features/records.py` | `CaseRecord` (confirmations, prep, specialist notes, decision, tasks; coordinator's board, finding triage, section layout + detail level, visibility per specialty; after the meeting: patient's stance, agreed plan), phase status, agenda |
| `features/history.py` | `GET /api/cases/{id}/history`: the patient's previous MDT records and treatment decisions from the health record (`Composition`, sections as text) and every meeting of the patient recorded in the app (status, decision). Read-only |
| `features/recommendation.py` | `GET /api/cases/{id}/recommendation`: the recommended postup to compare the conclusion with: `{intent, statement}` or null. The agent's first option and its `decision_support.intent` when the agent briefed the case; otherwise ponytail: hand-written examples per dataset patient (`model: "ukázka"`) citing real guideline passages via `knowledge.py` |
| `features/export.py` | `GET /api/cases/{id}/zaver.pdf`: the confirmed conclusion as a PDF download (`pdf.PdfDoc`; question, board, léčebný záměr, postup, zdůvodnění, soulad, who confirmed); 409 before it's confirmed. Needs a TrueType font with Czech glyphs (DejaVu in the Docker image) |

Endpoints: `GET /api/health`, `GET /api/patients` (FHIR passthrough),
`GET /api/cases` (agenda: label, question, high-flag count, intent, `status` =
`prep`/`meeting`/`followup`/`closed`, board `specialties`, `ai` (as `/ai` below); specialists see only their cases), `GET /api/cases/{id}` (`Case`),
`GET /api/cases/{id}/history` (patient's MDT history), `GET /api/cases/{id}/recommendation`, `GET /api/cases/{id}/ai` (`{status}`: `running` while `mdt-agent` briefs the patient, `done`, or null), `GET /api/cases/{id}/zaver.pdf`, `GET|PUT /api/cases/{id}/record` (`CaseRecord`; 409 once the decision is locked, 422 when marking a
case prepared without an MDT question or with fewer than 3 specialties on the board, or locking
the decision while a board member doesn't support it), `GET /api/sources/{type}/{id}` (title, date, author, full
text of one record — for the source drawer), `POST /api/intake` (upload a
case).

The agent also classifies free-text symptoms against `concepts.SYMPTOMS`, verifies excerpts
and recomputes the v2 rule flags. This runs alongside indicators and preference extraction;
the deterministic briefing uses keyword classification instead. Patient preference is available
both as `Case.preference` for the journey and at the start of `sections.patient`.

Study prefilter (`agent.screen_trials`, "One-call preliminary study filter" decision): one additional strict-JSON LLM call over
the patient digest, MDT date and all studies from `knowledge.trials()`. Each inclusion/exclusion
gets a cited reason and matched / not matched / unknown outcome. Code checks catalogue coverage,
patient references, non-empty verbatim excerpts and questionnaire item references; unsupported
outcomes become unknown and are logged in `rejected_citations`. Every displayed criterion also
cites the exact study criterion. A separate cited cancer-type assessment uses the study's
`diagnoza` (`trial:<id>#diagnosis`); supported incompatible cancer types → `ineligible`.
Uncertain tumour origin stays unknown, and solid-tumour/basket studies remain cross-organ.
Otherwise verdict priority: any supported exclusion match → `ineligible`;
otherwise any supported inclusion match → `eligible` (even with unknown criteria); otherwise
`missing_data`, including when no inclusion matches. These are preliminary filtering labels,
not clinical eligibility decisions. Missing catalogue or invalid output coverage fails explicitly.
The existing `TrialMatch` contract is unchanged; criteria remain AI `Statement`s. The journey
discussion screen shows expandable criteria and sources, with a provisional-filter notice.
No automatic enrolment, protocol dose recommendations or changes to the official record.
Saved briefings must be regenerated with `uv run mdt-agent --all` to include the new screening;
the deterministic no-LLM fallback continues to leave trials empty.

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
| `Journey.tsx`       | Steps 2–10 for one case: board bubbles, patient (+ the patient's wishes), key facts (urgent red flags first), up to 3 trends, the agent's questions for discussion + expandable study screening and evidence, léčebný záměr bubbles, závěr, potvrzení (compare with the recommendation, stanoviska in a pop-up, důvod odchylky, Potvrdit), export (PDF = download of `GET /api/cases/{id}/zaver.pdf`, FHIR greyed out) |
| `Steps.tsx`         | Progress through the journey; finished steps link back        |
| `Stanoviska.tsx`    | Stance bubbles per board specialty (green supports / red doesn't, `Member.supports`), pop-up with the stanovisko (the agent's verdict for that specialty, else example text) and the specialty's facts; used on Závěr and Potvrzení |
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
  FHIR R4 bundles; the app doesn't read them, tests use them as a fake FHIR server's content),
  `guidelines/`, `studie/`, `dotaznik/` (Questionnaire `MDT-PROMS-1`),
  `fhir/bundles.ndjson` (same bundles, loaded into IRIS by `mdt-load-fhir`). Its README is the reference; it mentions a
  `ground_truth/` folder that isn't delivered (yet). Override the location with `DATASET_DIR`. `P0x_pacient.md` is a readable rendering of the same records. Mapping notes: question =
  `ServiceRequest.reasonCode.text`; patient ECOG = PROMs item `samostatnost` (code 0–4); treatment
  history with real start dates = the nomination note "Předchozí onkologická léčba" (the bundle's
  MedicationAdministrations only cover recent doses); previous MDTs = `Composition` (`mdt-zaznam`); planned MDT date = `Task.restriction.period.start`
  (not `ServiceRequest.occurrenceDateTime`, which differs); Condition `category` text is
  `onkologická diagnóza` / `komorbidita` / `nežádoucí účinek léčby`.
- `Dataset/holdout/` (git-ignored, excluded from the Docker image): an extra synthetic patient
  P07 (`secret_bundles.ndjson`) and its evaluator-only answer key (`secret_ground_truth.md`). Not
  read by any code path (`pacienti/`, `fhir/bundles.ndjson`, `guidelines/` don't include it); keep
  the answer key out of every LLM/RAG input. Decision 23.
- `data/records/*.json`: records written by the running app (git-ignored).
- `data/zavery/`: generated MDT conclusions (`mdt-zaver`, AI drafts, git-ignored).
- `data/ai_cases/`: AI-augmented briefings (`mdt-agent`, `Case` JSON + trace of every step and
  rejected citation, git-ignored). `/api/cases/{id}` serves these instead of the plain build.
- FHIR R4 on InterSystems IRIS for Health (`iris/`, decision 24), the only patient-data source of
  the web API (case list, briefings, source drawer, intake) and of `mdt-agent`, `mdt-zaver` and
  `mdt-patient`. Local: `docker compose up -d iris` → `http://localhost:52773/fhir/r4`
  (`SuperUser` / `IRIS_PASSWORD`, default `SYS`; Management Portal at `/csp/sys/UtilHome.csp`; a 404
  at `/` is normal). Data in the `iris-data` volume; a fresh volume gets the endpoint on first start
  (~2 min) and the dataset via `mdt-load-fhir`. Reloading overwrites same-id resources; it is not a
  reset. Contributor 2's older kit volume (`docker-iris-fhir_iris-data`) has the same namespace and
  endpoint, so it can be reused as `iris-data`.
  Known gap: `Practitioner/LEK-P05-09` is only named in `Procedure.note` text, never
  referenced, so `get_patient_record("P05")` can't reach it.
