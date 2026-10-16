# AGENTS.md

Shared instructions for **every** coding agent on this repo (Claude Code, Codex, Antigravity, …)
and for humans. `CLAUDE.md` and `GEMINI.md` only point here — put all instructions in this file so
the agents never drift apart.

## What we're building

**MDT Copilot** — Rakathon 2026 prototype. A web app that consolidates an oncology patient's data
(FHIR records from eZdraví + PROMs questionnaires), uses AI to prepare a configurable briefing for
the multidisciplinary tumour board (MDT), and records the board's final, human-made decision.
Full brief (Czech): [docs/brief.md](docs/brief.md). Read it before working on a feature.

## Ground rules (non-negotiable)

1. **AI proposes, clinicians decide.** No AI output becomes part of the official record until a
   clinician confirms it.
2. **Label everything AI-produced.** AI content must be visually distinct from clinician-confirmed
   content, everywhere it appears (UI, exports).
3. **Every AI claim has a source** — the exact FHIR resource / questionnaire answer, viewable on
   click. If the data isn't there, say `V dostupné dokumentaci se nenachází.` — never guess.
4. **Record human decisions** with who made them and when.

These are enforced in code — use them, don't work around them:
- Backend: `Statement` / `Source` in [backend/src/mdt_backend/provenance.py](backend/src/mdt_backend/provenance.py)
  (validation rejects unsourced AI claims and unattributed human ones).
- Frontend: render clinical content only via [frontend/src/StatementView.tsx](frontend/src/StatementView.tsx);
  types mirrored in [frontend/src/provenance.ts](frontend/src/provenance.ts). Change both together.

Only synthetic/mock data in the repo. Never commit real patient data or API keys.

## Layout

```
backend/    Python 3.13, FastAPI, uv. Package: src/mdt_backend/
frontend/   TypeScript, React, Vite
data/stubs/ hand-made MDT briefings (one JSON per case) served by /api/cases — see docs/stubs.md
data/fhir/  raw FHIR bundles from the organisers (synthetic only)
docs/       brief, architecture, decisions, status, stubs (keep current — see below)
docker-compose.yml   HAPI FHIR R4 server on :8080
```

**Preparing stubs from patient records?** Follow [docs/stubs.md](docs/stubs.md). The briefing shape
(`Case` in `backend/src/mdt_backend/briefing.py`, mirrored in `frontend/src/briefing.ts`) is
the contract between data work and the frontend. Change it only in both places at once.

New features go in their own module so they can be removed in one move:
`backend/src/mdt_backend/features/<name>.py` (exposes `router`, registered in `app.py`) and
`frontend/src/features/<name>/`. Don't create these folders until the first feature needs them.

## Commands

```sh
docker compose up -d fhir                              # FHIR server → http://localhost:8080/fhir
cd backend && uv sync && uv run mdt-backend            # API → http://localhost:8000 (docs at /docs)
cd backend && uv run pytest && uv run ruff check . && uv run ruff format --check .
cd frontend && npm install && npm run dev              # UI → http://localhost:5173, /api proxied to :8000
cd frontend && npm run lint && npm run build
```

Run the relevant checks before every commit; CI runs the same ones on each PR.
Add dependencies with `uv add <pkg>` / `npm install <pkg>` — never hand-edit lockfiles.

## Git workflow

- `main` is always runnable. After the initial setup, nobody commits to `main` directly.
- Branch per task: `<contributor>/<short-topic>` (e.g. `jana/red-flags`). Open a PR into `main`;
  another contributor reviews it.
- **Squash-merge** PRs, so each feature is one commit on `main` and can be rolled back with
  `git revert <sha>`.
- Keep PRs small and short-lived; rebase on `main` often. Things will be iterated and rolled back
  fast — prefer reversible, isolated changes over sweeping refactors.

## Keeping docs current (required for every agent)

Other contributors' agents only know what's written down. In the same PR as the change:

| When you…                                          | Update                                         |
|----------------------------------------------------|------------------------------------------------|
| add/remove/move a module, endpoint, or data flow   | [docs/architecture.md](docs/architecture.md)   |
| make a choice others must follow (lib, model, API shape, reverting something) | append to [docs/decisions.md](docs/decisions.md) |
| start, finish or abandon work                      | your own section in [docs/status.md](docs/status.md) |
| change commands, layout or rules                   | this file                                      |

Rules: edit only your own section of `status.md` (avoids merge conflicts). Never rewrite past
entries in `decisions.md` — supersede them with a new entry. Keep this file agent-neutral: no
tool-specific syntax; tool-specific config goes in that tool's own folder.
