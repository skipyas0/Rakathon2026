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

## 6. MDT records as JSON files per case — 2026-10-16, yes-and
Status: accepted
Decision: Confirmations and the board's decision are stored in `data/records/<case>.json` via
`GET|PUT /api/cases/{id}/record`; the chair's confirmation locks the decision (409 on change).
Why: Fastest persistent store for the demo. Replace with FHIR CarePlan/Task/Provenance (brief
BONUS) or a DB when export is built — the API shape can stay.

## 7. "Not found" statements name what is missing — 2026-10-16, yes-and
Status: accepted
Decision: An unsourced AI statement must *end with* `V dostupné dokumentaci se nenachází.`
(e.g. `Stav MSI/MMR: V dostupné dokumentaci se nenachází.`) instead of being exactly that text.
Why: A bare "not found" doesn't tell the clinician what is missing.

## 8. Three-phase workflow, single chair view — 2026-10-16, yes-and
Status: accepted (supersedes the role-based views from the first demo)
Decision: Each case has phases Před zasedáním → Zasedání → Po zasedání, all reopenable. Only the
chair has the app open during the meeting, so there are no per-specialty views; specialist
sections expand on demand and store the specialist's view as a note. Section order/visibility is a
per-board template.
Why: Matches how the MDT actually runs (one shared screen, 3–5 min per patient).

## 9. Trends in the Case contract; AI shown in blue — 2026-10-16, yes-and
Status: accepted
Decision: `Case.trends` (optional) carries measured values with per-point sources for charts.
Unconfirmed AI output is blue with a robot icon; record data, clinician input and confirmed AI
render as plain text. Treatment intent (curative/palliative/supportive/surveillance) is part of
the decision and has its own colour + icon everywhere.
Why: Quick orientation on one screen; the brief requires AI output to be visually distinct.

## 10. Briefings built from FHIR bundles without an LLM — 2026-10-16, yes-and
Status: accepted
Decision: `from_fhir.py` builds `Case` deterministically from the organisers' bundles; red flags
come from fixed rules (`rules.py`, shown as AI proposals). New contract fields driven by the data:
`Statement.origin = "record"`, `Source.title`, timeline kind `pathology`, `Case.board`,
`Case.mdt_date`, decision intent `deferred` (the dataset's `odlozeno`).
Why: Most of the briefing is structured in the data already; deterministic extraction is exact,
fast and cites its sources. The LLM can later add what rules can't (guideline options, trials,
questions, narrative summary) into the same `Case`.

## 11. Dataset in `Dataset/`, fictional stubs removed — 2026-10-16, yes-and
Status: accepted (supersedes the `data_trial/` location from #10)
Decision: The organisers' dataset v1.1 lives in `Dataset/` at the repo root (git-ignored, as on
`main`); `settings.dataset_dir` / `DATASET_DIR` points at it. Guideline and trial citations use
`guideline:<passage-id>` (e.g. `guideline:KRC-2.3`) and `trial:<trial-id>#<criterion-id>` (e.g.
`trial:RKT-01#Z2`), built by `knowledge.py` with verbatim text. The fictional stubs (`example`,
`lung-incomplete`) are deleted; tests create their own cases. The planned MDT date is
`Task.restriction.period.start`.
Why: One dataset location for everyone; citation ids are the ones the dataset tells us to cite; the
fictional cases would mix made-up guidelines/trials with the real ones.

## 12. Loading the dataset into a FHIR server (IRIS) — 2026-10-16
Status: accepted
Decision: `mdt-load-fhir` sends each `collection` bundle as a `transaction` of PUTs (keeps the
dataset IDs, reload is idempotent). Three R4 violations that IRIS rejects are repaired on load:
IDs with `_` get `-` instead (26 Observations, e.g. `P01-lab01-hb_f` → `P01-lab01-hb-f`, with
references rewritten); `Observation.derivedFrom` → `DiagnosticReport` (44×, type not allowed) moves
to extension `https://rakathon.example.org/fhir/StructureDefinition/derived-from-report` with the same
`valueReference`; one empty `valueString` answer (P03-prom02 `bolest-misto`) is dropped.
Why: Strict servers refuse the raw bundles; these repairs are lossless, so source links still work.
Code that reads from the server must use the repaired IDs and the extension, not the raw ones.
Update 2026-10-16: each rewritten resource also carries `meta.tag` {system
`https://rakathon.example.org/fhir/sid/dataset-id`, code = original id} (`load_fhir.dataset_id`),
so server readers (the agent, #17) can cite the dataset's ids without reading the bundle files.

## 13. LLM: Azure OpenAI gpt-6-luna (EU data zone) with strict structured output — 2026-10-16
Status: accepted
Decision: LLM calls go to `gpt-6-luna-dz-eu` behind the hackathon Azure APIM
(`https://apim-rakathon-q7146n.azure-api.net/openai/v1`, OpenAI-compatible, key in the `api-key`
header, `AZURE_API_KEY` in `.env`), through `llm.chat_json` only, always with a strict JSON schema.
Plain httpx, no SDK. Model output that cites FHIR resources is checked against the record; unknown
IDs are dropped. PDFs are rendered with pypdf + an embedded subset TrueType font (pypdf's built-in
fonts can't encode Czech).
Why: EU data zone answers the brief's data-residency question; schema-constrained output gives
parseable, field-by-field answers with sources (ground rule 3).

## 14. Deploy on Fly.io behind one shared password — 2026-10-16, yes-and
Status: accepted
Decision: The `Dockerfile` image (frontend + API, `Dataset/` baked in) runs on Fly.io as
`mdt-copilot-rakathon` in `fra`, one machine with a `records` volume. `APP_PASSWORD` (Fly secret)
enables HTTP basic auth for everything but `/api/health`.
Why: A public URL for the team and the jury without exposing the organisers' dataset (redistribution
terms unknown) or letting anyone lock decisions. Per-user login only when decisions must be
attributed to authenticated clinicians.

## 15. Consensus of the board, recorded by the chair — 2026-10-16, yes-and
Status: accepted (clarifies #6 and #8)
Decision: The final conclusion needs consensus of all board members
([MDT_ZASEDANI_PROCES.md](MDT_ZASEDANI_PROCES.md) §4.3). The chair keeps the record in the app during
the meeting and confirms (locks) it on the board's behalf once the board agrees; the record lists
the members present (`Decision.attendees`). Differing views from the discussion go in `dissent`.
Per-member sign-off is not built. In real practice the coordinator often keeps the record; in our
prototype that is the chair.
Why: Matches the confirmed process (the chair can't decide alone) while keeping one person at the
screen (#8). "Chair's confirmation" in #6 means "the chair records the board's agreement".

## 16. Role-based workflow: coordinator runs the case — 2026-10-16, yes-and
Status: accepted (supersedes #8 and #15)
Decision: Target workflow in [workflow-plan.md](workflow-plan.md). Roles via a switcher (no login):
the coordinator (intake, triage, board, structure, visibility, minutes) and the specialists (own
section, confirm AI claims, opinion); the chair is one of the specialists, marked, with no extra
rights. The coordinator writes the minutes and ticks each member's consent before locking. Records
are per meeting, not per patient. Scope = POVINNÉ items of `problem_statement.md`;
`MDT_ZASEDANI_PROCES.md` wins over the brief (the consultation notes don't).
Why: The partners' process (MDT_ZASEDANI_PROCES.md) has the coordinator keep the record and all
members consent; specialists need their own filtered view; patients return to the MDT, so one
record per patient would overwrite history.

## 17. MDT agent as a fixed pipeline over IRIS, citations verified in code — 2026-10-16, Contributor 2
Status: accepted (builds on #12, #13)
Decision: `agent.py` runs a fixed chain of steps — gather (IRIS) → diagnosis → CACC → findings →
per-specialist context + view (radiology, surgery, oncology) → 1–2 options — each LLM step one
strict-JSON `llm.chat_json` call. The kit's pattern (LangChain `create_agent` with tool calling,
`FHIR-AI-Kit/skills/iris-ai-agents`) is followed in spirit, not adopted: the "tools" (FHIR
`$everything`, read one resource from IRIS) are called by the pipeline, and the model chooses only
*which* records each specialist reads. The diagnosis → guideline mapping is deterministic (ICD-10
prefix → KRC/PLI/PRS, always + OBC). Passage ids outside those documents, references not in the
patient's record and quotes not found verbatim (word-level) in the record are dropped and logged
in the trace; an AI statement left without sources is dropped; an option without a passage is
dropped; at most 2 options. RED → `high`, YELLOW → `medium` red flags; missing checklist items
become `NOT_FOUND` statements in the area's section. Output is the existing `Case` (rule output
from `build_case` kept, AI statements appended), no contract change.
Why: The Azure endpoint rejects function tools with reasoning on `/chat/completions` (only
`/responses` or `reasoning_effort: none`), and a free tool loop is harder to make reproducible and
auditable than a fixed chain. Checking citations in code instead of trusting the prompt is what
the brief's "no hallucinations, every claim sourced" rule needs. Two runs on the same patient give
the same first-line recommendation, though wording and the set of findings vary (status.md).

## 18. Agent output feeds the app as-is; the web API reads IRIS — 2026-10-17, Contributor 2
Status: accepted (builds on #12, #17)
Decision: The agent fills every part of the existing `Case` the UI renders, with no frontend
change: findings → `red_flags`; executive summary written as free text, then extracted into
`summary` (AI facts first, record facts kept after), extra `red_flags` (not repeating known ones)
and `timeline` events (only dates not already there for that kind); each specialist's view written
as text, then extracted into cited points + verdict + `NOT_FOUND` gaps in `sections.<id>`;
indicators to chart → `trends`; patient preference → first items of `sections.patient` (shown as
the patient's voice in the meeting). For `trends` the model only *chooses* which measurements form
an indicator: every point's value, date, unit and reference range are read from the cited
Observation / questionnaire answer, so charts (rendered as record facts) never carry a model
number. Generation is a batch step (`mdt-agent --all`, results in `data/ai_cases/`), not triggered
from the UI. The web API's case list, plain briefings and source drawer read the IRIS FHIR server
(dataset ids via the loader's tag); the bundles on disk are used only while the server is down.
Why: The user asked for the app to show the pipeline without touching the frontend, and for all
patient data to come from IRIS. Text-then-extract keeps the narrative the model reasons in, while
the app gets small, individually cited statements. A full run is ~2.5 min per patient alone (~9
min each with all 6 in parallel under the APIM rate limit), too slow to run on page load.
