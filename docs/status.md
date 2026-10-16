# Status

Who is working on what. Each contributor (and their agent) edits **only their own section**.
Keep it short: current branch, what's in progress, what's blocked, what others should know.

## Open questions (anyone)

- LLM provider/model and where it runs (EU / on-prem requirement in the brief)?
- Organiser mock data: format and how we load it into the FHIR server.
- FHIR server: stay on HAPI or switch to the sponsor's InterSystems IRIS for Health
  (https://github.com/intersystems-community/FHIR-AI-Hackathon-Kit/tree/V2)? Backend works with
  either via `.env`.

## yes-and (Claude Code)

- Branch `yes-and/frontend-demo`: three-phase MDT app (prep → meeting slide → decision/follow-up),
  clinical palette, AI in blue with robot icon, trend charts, source drawer, specialist notes,
  intent + locked decision, action plan, print export.
- **For stub authors:** `Case.trends` now exists (see docs/stubs.md) — please add 2–4 series per patient.
- Demo stubs: `data/stubs/example.json` (colorectal, full, with trends) and `lung-incomplete.json`.
- Not done yet: bulk-confirm per section, AI-generated patient/GP summaries, FHIR export.

## Contributor 2

-

## Contributor 3

-
