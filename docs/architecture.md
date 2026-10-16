# Architecture

Current state of the system. Describe what **is**, not what's planned (plans go in `status.md`).

```
browser ──► frontend (Vite dev server :5173) ──/api──► backend (FastAPI :8000) ──► HAPI FHIR (:8080)
                                                            │
                                                            └──► LLM provider (not chosen yet)
```

## Backend — `backend/src/mdt_backend/`

| File            | Role                                                                    |
|-----------------|-------------------------------------------------------------------------|
| `app.py`        | FastAPI app, route registration                                         |
| `config.py`     | Settings from env / `.env`                                              |
| `fhir.py`       | `get(path, **params)` → raw FHIR JSON from the FHIR server              |
| `provenance.py` | `Statement`, `Source`: AI-vs-human labelling, sources, confirmation     |
| `briefing.py`   | `Case`: the MDT briefing shape (summary, timeline, red flags, sections, decision support) |
| `features/cases.py` | Serves `Case` JSON from `data/stubs/` (to be replaced by the AI pipeline) |

Endpoints: `GET /api/health`, `GET /api/patients` (FHIR `Patient` search passthrough),
`GET /api/cases` (list), `GET /api/cases/{id}` (`Case`).

## Frontend — `frontend/src/`

| File                | Role                                                          |
|---------------------|---------------------------------------------------------------|
| `App.tsx`           | Single page; currently a health check + example statements    |
| `StatementView.tsx` | Renders a `Statement`: AI badge, confirmation, sources        |
| `provenance.ts`     | TS mirror of the backend `Statement` / `Source` models        |
| `briefing.ts`       | TS mirror of the backend `Case` model                         |

## Data

- `data/stubs/*.json`: hand-made `Case` briefings, validated by `backend/tests/test_stubs.py`.
- FHIR R4 on HAPI (H2 DB inside the container: survives restarts, wiped by `docker compose down`).
  Mock data from the organisers is not loaded yet. The backend works with any FHIR R4
  server: set `FHIR_BASE_URL` (+ `FHIR_USER`/`FHIR_PASSWORD` for IRIS, see `.env.example`).
