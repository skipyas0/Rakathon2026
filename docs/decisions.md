# Decisions

The decisions in force: choices others must follow. Numbers are stable anchors (code and docs
cite them), so gaps are decisions that no longer hold; git history keeps their text. To change a
decision, edit it in place and add the date to its Status line; to drop one, delete it.

```
## N. Title — YYYY-MM-DD, <who>
Status: accepted [| updated YYYY-MM-DD]
Decision: …
Why: …
```

## 1. Stack — 2026-10-16, initial setup
Status: accepted | updated 2026-10-17 (#24)
Decision: Python 3.13 + FastAPI (uv) backend, TypeScript + React (Vite) frontend, InterSystems IRIS
for Health as the FHIR R4 server (`iris/`, docker compose).
Why: A FHIR server gives standard storage and search for the patient data; FastAPI/Pydantic give
typed models for provenance; Vite is the minimal TS setup.

## 2. Provenance is a type, not a convention — 2026-10-16, initial setup
Status: accepted
Decision: All clinical content flows as `Statement` (backend `provenance.py`, frontend
`provenance.ts`) and is rendered only by `StatementView`.
Why: The ground rules (label AI output, cite sources, human confirmation) must hold everywhere;
enforcing them in one model is easier than reviewing every feature for them.

## 3. One shared instructions file for all agents — 2026-10-16, initial setup
Status: accepted
Decision: `AGENTS.md` is the single source of agent instructions; `CLAUDE.md` and `GEMINI.md`
just import it.
Why: Contributors use different agents; one file prevents divergent rules.

## 4. Squash-merge PRs — 2026-10-16, initial setup
Status: accepted
Decision: Work on `<contributor>/<topic>` branches, PR into `main`, squash-merge.
Why: Fast iteration with frequent rollbacks — one commit per feature makes `git revert` trivial.

## 6. MDT records as JSON files per meeting — 2026-10-16, yes-and
Status: accepted | updated 2026-10-17 (#20)
Decision: The board, confirmations and the decision are stored in `data/records/<case>.json` via
`GET|PUT /api/cases/{id}/record`, one record per meeting (case id = patient + planned MDT date).
Confirming the conclusion locks it (409 on change).
Why: Fastest persistent store for the demo; patients return to the MDT, so a record per patient
would overwrite history. Replace with FHIR CarePlan/Task/Provenance or a DB when FHIR export is
built — the API shape can stay.

## 7. "Not found" statements name what is missing — 2026-10-16, yes-and
Status: accepted
Decision: An unsourced AI statement must *end with* `V dostupné dokumentaci se nenachází.`
(e.g. `Stav MSI/MMR: V dostupné dokumentaci se nenachází.`) instead of being exactly that text.
Why: A bare "not found" doesn't tell the clinician what is missing.

## 9. Trends in the Case contract; AI shown in blue — 2026-10-16, yes-and
Status: accepted | updated 2026-10-17 (dotted underline)
Decision: `Case.trends` carries measured values with per-point sources for charts. Unconfirmed AI
output is blue with a robot icon; record data, clinician input and confirmed AI render as plain
text. Every statement that opens its sources has a dotted underline (teal, or blue for AI), so
clickable is visible without making record facts blue. The léčebný záměr (curative/palliative/supportive/surveillance/deferred) has its own colour
and icon everywhere.
Why: Quick orientation on one screen; AI output must be visually distinct.

## 10. The base briefing is built from the record without an LLM — 2026-10-16, yes-and
Status: accepted | updated 2026-10-17 (verbatim excerpts)
Decision: `from_fhir.py` builds `Case` deterministically from the patient's FHIR resources; red
flags come from fixed rules (`rules.py`, shown as AI proposals). Contract fields driven by the
data: `Statement.origin = "record"`, `Source.title`, timeline kind `pathology`, `Case.board`,
`Case.mdt_date`, intent `deferred`. Excerpts quote the record verbatim, one passage per line
(`bundles.answer_line` / `observation_line`, the same lines `text_of` shows), so the source drawer
can highlight them in the whole record; `test_excerpts_are_verbatim…` guards it.
Why: Most of the briefing is structured in the data already; deterministic extraction is exact,
fast and cites its sources. The agent (#17) adds what rules can't into the same `Case`.

## 11. Dataset location and citation ids — 2026-10-16, yes-and
Status: accepted
Decision: The organisers' dataset lives in `Dataset/` at the repo root (git-ignored;
`DATASET_DIR` overrides it). Guideline and trial citations use `guideline:<passage-id>` (e.g.
`guideline:KRC-2.3`) and `trial:<trial-id>#<criterion-id>` (e.g. `trial:RKT-01#Z2`), built by
`knowledge.py` with verbatim text. The planned MDT date is `Task.restriction.period.start`.
Why: One dataset location for everyone; the citation ids are the ones the dataset says to cite.

## 12. Loading the dataset into the FHIR server — 2026-10-16
Status: accepted
Decision: `mdt-load-fhir` sends each `collection` bundle as a `transaction` of PUTs (keeps the
dataset ids, reload is idempotent). Three R4 violations IRIS rejects are repaired on load: ids
with `_` get `-` (26 Observations, e.g. `P01-lab01-hb_f` → `P01-lab01-hb-f`, references rewritten),
each rewritten resource keeping its original id as `meta.tag` {system
`https://rakathon.example.org/fhir/sid/dataset-id`} (`load_fhir.dataset_id`);
`Observation.derivedFrom` → `DiagnosticReport` (44×) moves to extension
`https://rakathon.example.org/fhir/StructureDefinition/derived-from-report` with the same
`valueReference`; one empty `valueString` answer is dropped.
Why: Strict servers refuse the raw bundles; the repairs are lossless, so source links still work.
Readers of the server cite the dataset's ids via the tag.

## 13. LLM: Azure OpenAI gpt-6-luna (EU data zone) with strict structured output — 2026-10-16
Status: accepted
Decision: LLM calls go to `gpt-6-luna-dz-eu` behind the hackathon Azure APIM
(`https://apim-rakathon-q7146n.azure-api.net/openai/v1`, OpenAI-compatible, key in the `api-key`
header, `AZURE_API_KEY` in `.env`), through `llm.chat_json` only, always with a strict JSON schema.
Plain httpx, no SDK. Model output that cites FHIR resources is checked against the record; unknown
ids are dropped. PDFs are rendered with pypdf + an embedded subset TrueType font (Czech glyphs).
Why: The EU data zone answers the data-residency question; schema-constrained output gives
parseable, field-by-field answers with sources (ground rule 3).

## 14. Deploy on Fly.io: the app behind one shared password, IRIS private — 2026-10-16, yes-and
Status: accepted | updated 2026-10-17 (#24)
Decision: The `Dockerfile` image (frontend + API) runs on Fly.io as `mdt-copilot-rakathon` in
`fra`, one machine with a `records` volume; `APP_PASSWORD` (Fly secret) enables HTTP basic auth for
everything but `/api/health`. IRIS runs as a second app, `mdt-copilot-iris` (`iris/fly.toml`, 2 GB,
volume `iris_data`, no public port), reached over Fly's private network.
Why: A public URL for the team and the jury without exposing the dataset or letting anyone lock
decisions. Per-user login only when decisions must be attributed to authenticated clinicians.

## 17. MDT agent as a fixed pipeline over IRIS, citations verified in code — 2026-10-16, Contributor 2
Status: accepted
Decision: `agent.py` runs a fixed chain of steps — gather (IRIS) → diagnosis → CACC → findings →
per-specialist context + view (radiology, surgery, oncology) → 1–2 options — each LLM step one
strict-JSON `llm.chat_json` call; the model chooses only *which* records each specialist reads. The
diagnosis → guideline mapping is deterministic (ICD-10 prefix → KRC/PLI/PRS, always + OBC).
Passage ids outside those documents, references not in the record and quotes not found verbatim
are dropped and logged in the trace; an AI statement left without sources is dropped; an option
without a passage is dropped. RED → `high`, YELLOW → `medium` red flags; missing checklist items
become `NOT_FOUND` statements. Output is the existing `Case`.
Why: The Azure endpoint rejects function tools with reasoning on `/chat/completions`, and a free
tool loop is harder to make reproducible and auditable than a fixed chain. Checking citations in
code instead of trusting the prompt is what "every claim sourced" needs.

## 18. Agent output feeds the app as-is — 2026-10-17, Contributor 2
Status: accepted | updated 2026-10-17 (#24: no disk fallback)
Decision: The agent fills every part of `Case` the UI renders: findings → `red_flags`; an executive
summary written as text, then extracted into `summary` (AI facts first), extra `red_flags` and
`timeline` events; each specialist's view as text, then cited points + verdict + `NOT_FOUND` gaps
in `sections.<id>`; indicators → `trends`, where the model only *chooses* measurements and every
point's value, date, unit and range is read from the cited resource; the patient's preference →
`preference` (#22). Generation is a batch step (`mdt-agent --all` → `data/ai_cases/`), not
triggered from the UI.
Why: Text-then-extract keeps the narrative the model reasons in while the app gets small,
individually cited statements. A full run is ~2.5 min per patient (~9 min each with all 6 in
parallel under the APIM rate limit), too slow for page load.

## 19. Previous MDT's board in the briefing — 2026-10-17, yes-and
Status: accepted
Decision: `Case.previous_board` lists the members of the patient's latest previous MDT from the
record's `CareTeam`: practitioner id (`""` when only the role is recorded), role text, `chair` =
the qualification says "předseda". The coordinator can adopt it; it is never applied silently.
Why: The board for a repeat MDT is usually the same team; the coordinator starts from facts.

## 20. One simple journey for the coordinator; the board decides by consensus — 2026-10-17, yes-and
Status: accepted | updated 2026-10-17 (#27: specialist journeys)
Decision: The coordinator's frontend is one linear journey (`docs/workflow-plan.md`): upload → board
(specialty bubbles) → patient → key facts → trends → questions → léčebný záměr → závěr → potvrzení
→ export, plus a case overview. Specialists get their own short journey (#27). No triage,
visibility or section configuration in the UI (the backend keeps those record fields for later). The final conclusion
needs consensus of all board members (`MDT_ZASEDANI_PROCES.md` §4.3): the coordinator records it,
Potvrdit means the board agreed, anyone against blocks it; no per-member sign-off. Soulad s
doporučenými postupy is derived: chosen léčebný záměr = recommended one (#21). Where the agent has
no output, a hand-written example labelled "ukázka" stands in (recommendation, stanoviska).
Why: The demo has to be simple and legible end to end; the role-based screens were too much.

## 21. The agent recommends a léčebný záměr — 2026-10-17, yes-and
Status: accepted
Decision: Each option the agent proposes carries its léčebný záměr; the first kept option's goes
to `DecisionSupport.intent`. `/recommendation` returns that option and intent when present, so
Potvrzení compares the conclusion with real AI output.
Why: Soulad is derived from the léčebný záměr (#20); without one per option the app could only
compare with the examples.

## 22. The patient's preference on its own in the briefing — 2026-10-17, yes-and
Status: accepted
Decision: `Case.preference` holds the agent's statements of the patient's treatment wishes and
goals (or one `NOT_FOUND` statement); the same statements lead `sections.patient`. Empty when the
agent hasn't briefed the case. Pacient shows them under the MDT question.
Why: The process doc (§3.1, §4.1) puts the patient's view next to the question.

## 23. Holdout patient lives in `Dataset/holdout/`, not in git — 2026-10-17, yes-and
Status: accepted
Decision: `secret_bundles.ndjson` (P07) and `secret_ground_truth.md` live in `Dataset/holdout/`
(one copy; P07 isn't in `pacienti/` or `fhir/bundles.ndjson`), git-ignored and excluded from the
Docker image by `.dockerignore`. They remain in git history (commit 214594b); fictional data, so
no rewrite.
Why: The answer key must never reach the pipeline or a coding agent's context; `holdout/` is
outside every path the code reads.

## 24. Core scope: IRIS only, FHIR only — 2026-10-17, yes-and
Status: accepted
Decision: `docs/problem_statement.md` is the scope: the core definition plus every item of the
brief as a checklist. IRIS for Health is the only FHIR server and the only store of patient data:
the app never reads patient files from disk (intake loads into IRIS; an unreachable IRIS is a 503,
so an upload is never half-saved; `/api/health` stays 200 and reports `fhir`). IRIS is built from
`iris/` (pinned community image, endpoint created on first start, same namespace and endpoint as
the sponsor kit). Running the app needs no test suite; checks stay light, and tests use a fake FHIR
server holding the dataset as the loader stores it.
Why: Cuts parallel paths (HAPI vs IRIS, server vs disk) and gives every change one yardstick; IRIS
earns the sponsor bonus.

## 25. The conclusion is the filled template: PDF preview, DOCX for edits — 2026-10-17, yes-and
Status: accepted
Decision: Export renders `template_zaver_zasedani/form.md` for the meeting: header from the
confirmed decision's attendees and the FHIR Patient, history fields drafted by one LLM call over
the IRIS record (cached per meeting, each value with its FHIR sources, blue in PDF and DOCX), the
question from the nomination, Závěr MDT from the board's confirmed decision. The coordinator
previews the PDF; to change anything they download the DOCX and edit it. No AI writes the board's
conclusion. Data the dataset lacks (birth number, address, phone) print as `NOT_FOUND`.
Why: The template is the official output; a preview with an editable DOCX is the smallest flow that
keeps AI output labelled and sourced without a per-field confirmation screen.

## 26. One type scale that grows with the screen — 2026-10-17, yes-and
Status: accepted
Decision: Five font sizes only, as CSS variables (`--fs-s` 0.875rem, `--fs-m` 1rem, `--fs-l` 1.2rem,
`--fs-xl` 1.5rem, `--fs-2xl` 2rem); nothing smaller than `--fs-s`. The root size is fluid,
`clamp(16px, 8px + 0.6vw, 20px)`: 16px on laptops and in a narrow window beside the hospital
system, up to 20px on big or projected screens. Sizes and the main widths (page, journey column,
Přehled, source drawer) are rem, so the UI scales as one; browser zoom works on top. Chart labels
are HTML around the stretched SVG, so they keep the scale too.
Why: The app is projected in the meeting and also sits in a narrow window next to the hospital
information system; 21 ad-hoc sizes down to 9px were not legible in either.

## 27. Specialists: a picked role, a short journey, their own stanovisko — 2026-10-17, yes-and
Status: accepted
Decision: A role button (top right) opens a pop-up of role bubbles: Koordinátor or one of the process doc's 4
specialist roles (surgery, oncology, radiology, pathology), stored per browser, not authenticated.
A specialist sees only the cases whose board the coordinator put their specialty on, and walks
Pacient → Klíčové informace → Stanovisko: the coordinator's screens narrowed to their section, the
patient's and the red flags for their area (`RedFlag.area`; none = everyone), then their stance and
stanovisko. The stanovisko is empty until the specialist generates it (the agent's specialist step
alone, blue, to confirm) or writes it (signed); editing makes it theirs. Stances and stanoviska are
written only through `/stanovisko/{specialty}` (the coordinator's stance bubbles too); the record
PUT keeps the stored ones. The agent's batch verdict per specialty is not shown. Board specialties
outside the 4 keep the "ukázka" stanovisko, with a warning.
Why: The board members prepare their part before the meeting (process doc §3); one shared record
written from two screens must not lose a specialist's input to the coordinator's stale copy.
