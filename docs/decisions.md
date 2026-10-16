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
