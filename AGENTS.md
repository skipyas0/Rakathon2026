# AGENTS.md

Shared instructions for **every** coding agent on this repo (Claude Code, Codex, Antigravity, …)
and for humans. `CLAUDE.md` and `GEMINI.md` only point here — put all instructions in this file so
the agents never drift apart.

## What we're building

**MDT Copilot** — Rakathon 2026 prototype. A web app that consolidates an oncology patient's data
(FHIR records from eZdraví + PROMs questionnaires), uses AI to prepare a configurable briefing for
the multidisciplinary tumour board (MDT), and records the board's final, human-made decision.
Full brief (Czech): [docs/brief.md](docs/brief.md). Read it before working on a feature.

Domain docs (Czech). `MDT_ZASEDANI_PROCES.md` is confirmed with the challenge partners and wins over
the brief, which is general and may not hold. The consultation notes are unverified hints and defer
to the brief, as their header says. The dataset's `README.md` is the authority on the data.
Scope = the POVINNÉ items in `problem_statement.md`.

| Doc | What it is |
|-----|------------|
| [docs/workflow-plan.md](docs/workflow-plan.md) | **Agreed target workflow, roles and screens** (English) |
| [docs/brief.md](docs/brief.md) | Official brief (original [brief.docx](docs/brief.docx)), general |
| [docs/problem_statement.md](docs/problem_statement.md) | The same brief restructured as a checklist (POVINNÉ vs BONUS) |
| [docs/MDT_ZASEDANI_PROCES.md](docs/MDT_ZASEDANI_PROCES.md) | How a real MDT runs: roles, nomination, meeting, consensus, follow-up, repeat MDTs |
| [docs/MDT_COPILOT_KONZULTACE_OBECNE_RADY.md](docs/MDT_COPILOT_KONZULTACE_OBECNE_RADY.md) | Mentor consultation notes: priorities and hints, not verified requirements |
| [docs/template_zaver_zasedani/](docs/template_zaver_zasedani/) | Template for the board's final record, to be filled in live in the app |

The board reaches its final conclusion by **consensus of all members**; in the app the
**coordinator records it** and ticks each member's consent (decision #16).

## Ground rules (non-negotiable)

1. **AI proposes, clinicians decide.** No AI output becomes part of the official record until a
   clinician confirms it.
2. **Label everything AI-produced.** AI content must be visually distinct from clinician-confirmed
   content, everywhere it appears (UI, exports).
3. **Every AI claim has a source** — the exact FHIR resource / questionnaire answer, viewable on
   click. If the data isn't there, say what is missing + `V dostupné dokumentaci se nenachází.` — never guess.
4. **Record human decisions** with who made them and when.

These are enforced in code — use them, don't work around them:
- Backend: `Statement` / `Source` in [backend/src/mdt_backend/provenance.py](backend/src/mdt_backend/provenance.py)
  (validation rejects unsourced AI claims and unattributed human ones).
- Frontend: render clinical content only via [frontend/src/StatementView.tsx](frontend/src/StatementView.tsx);
  types mirrored in [frontend/src/provenance.ts](frontend/src/provenance.ts). Change both together.

Only synthetic/mock data in the repo. Never commit real patient data or API keys.

The dataset contains **deliberate mistakes and gaps** — finding them is part of the task. Never
"fix" files in `Dataset/` and don't make the code silently pick the convenient value: surface the
inconsistency (red flag / missing data) with both sources.

## Layout

```
backend/    Python 3.13, FastAPI, uv. Package: src/mdt_backend/
frontend/   TypeScript, React, Vite
data/records/ the app's saved records, one JSON per case (git-ignored)
data/stubs/ optional hand-made briefings served by /api/cases — none now, so the folder is absent;
            create it with the first stub (see docs/stubs.md)
Dataset/    organisers' dataset v1.1 (git-ignored, see its README): pacienti/ → from_fhir.py,
            guidelines/ + studie/ → knowledge.py
docs/       brief + domain docs (listed above), architecture, decisions, status, stubs
            (keep current — see below)
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
# or IRIS for Health (FHIR → http://localhost:52773/fhir/r4); first run also needs fhir_server_setup_native.py
# (FHIRServerSetup.create_fhir_server, without the kit's sample data — see docs/architecture.md)
docker compose -f FHIR-AI-Kit/docker-iris-fhir/docker-compose.yml up -d
cd backend && uv run mdt-load-fhir                     # load Dataset/fhir/bundles.ndjson into FHIR_BASE_URL
cd backend && uv run mdt-patient P01                   # pretty-print one patient's full record from the server
cd backend && uv run mdt-zaver P01                     # MDT conclusion PDF → data/zavery/ (needs FHIR server + AZURE_API_KEY)
cd backend && uv run mdt-agent P01 --runs 2            # MDT agent → data/ai_cases/ (IRIS + AZURE_API_KEY; --source file = no server)
cd backend && uv sync && uv run mdt-backend            # API → http://localhost:8000 (docs at /docs)
cd backend && uv run pytest && uv run ruff check . && uv run ruff format --check .
cd frontend && npm install && npm run dev              # UI → http://localhost:5173, /api proxied to :8000
cd frontend && npm run lint && npm run build
docker compose up -d --build app                       # whole app in one container → http://localhost:8000
fly deploy                                             # redeploy https://mdt-copilot-rakathon.fly.dev (needs Dataset/)
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
