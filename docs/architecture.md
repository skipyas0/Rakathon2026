# Architecture

Current state of the system. Describe what **is**, not what's planned (plans go in `status.md`).

```
browser ──► frontend (Vite dev server :5173) ──/api──► backend (FastAPI :8000) ──► HAPI FHIR (:8080)
                                                            │
                                                            └──► LLM provider (not chosen yet)
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
| `fhir.py`       | `get(path, **params)` → raw FHIR JSON from the FHIR server              |
| `provenance.py` | `Statement`, `Source`: AI-vs-human labelling, sources, confirmation     |
| `briefing.py`   | `Case`: the MDT briefing (summary, timeline, red flags, sections, decision support, trends) |
| `features/cases.py` | Serves `Case` JSON from `data/stubs/` (to be replaced by the AI pipeline) |
| `features/records.py` | `CaseRecord` (confirmations, prep, specialist notes, decision, tasks), phase status, agenda |

Endpoints: `GET /api/health`, `GET /api/patients` (FHIR passthrough),
`GET /api/cases` (agenda: label, question, high-flag count, intent, `status` =
`prep`/`meeting`/`followup`/`closed`), `GET /api/cases/{id}` (`Case`),
`GET|PUT /api/cases/{id}/record` (`CaseRecord`; 409 once the decision is locked, 422 when marking a
case prepared without an MDT question).

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

- `data/stubs/*.json`: hand-made `Case` briefings, validated by `backend/tests/test_stubs.py`.
- `data/records/*.json`: records written by the running app (git-ignored).
- FHIR R4 on HAPI (H2 DB inside the container: survives restarts, wiped by `docker compose down`).
  Mock data from the organisers is not loaded yet. The backend works with any FHIR R4
  server: set `FHIR_BASE_URL` (+ `FHIR_USER`/`FHIR_PASSWORD` for IRIS, see `.env.example`).
