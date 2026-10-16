# Status

Who is working on what. Each contributor (and their agent) edits **only their own section**.
Keep it short: current branch, what's in progress, what's blocked, what others should know.

## Open questions (anyone)

- FHIR server: stay on HAPI or switch to the sponsor's InterSystems IRIS for Health
  (https://github.com/intersystems-community/FHIR-AI-Hackathon-Kit/tree/V2)? Backend works with
  either via `.env`.

## yes-and (Claude Code)

- Branch `yes-and/frontend-demo`: three-phase MDT app (prep → meeting slide → decision/follow-up),
  clinical palette, AI in blue with robot icon, trend charts, source drawer, specialist notes,
  intent + locked decision, action plan, print export.
- Dataset v1.1 integrated from `Dataset/` (git-ignored): patients → `from_fhir.py` + `rules.py`,
  guidelines + trials → `knowledge.py`. Fictional stubs removed; the agenda is P01–P06 only.
- Next: decision support (guideline options, trial screening, questions) from `knowledge.py` —
  needs the LLM decision. Ground truth (`ground_truth/` in the dataset README) is not delivered.
- Branch `yes-and/docker-deploy`: one `Dockerfile` (frontend built in, served by FastAPI on :8000),
  `app` service in `docker-compose.yml`, deployed to https://mdt-copilot-rakathon.fly.dev behind a
  shared password (ask yes-and). Fly app is on yes-and's personal Fly account.
- Not done yet: bulk-confirm per section, AI-generated patient/GP summaries, FHIR export.

## Contributor 2

- IRIS for Health running from `FHIR-AI-Kit/docker-iris-fhir` with the full dataset loaded
  (`uv run mdt-load-fhir`, decision 12). `uv run mdt-patient P01` pretty-prints one patient's
  complete record from the server. The app itself still reads bundles from disk (`bundles.py`).
- `uv run mdt-zaver P01`: MDT conclusion (form.md) as PDF, two gpt-6-luna calls (decision 13).
  CLI only — not wired into the API/UI yet; ~40 s per patient.

## Contributor 3

-
