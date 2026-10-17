# Status

Who is working on what. Each contributor (and their agent) edits **only their own section**.
Keep it short: current branch, what's in progress, what's blocked, what others should know.

## Open questions (anyone)

- FHIR server: stay on HAPI or switch to the sponsor's InterSystems IRIS for Health
  (https://github.com/intersystems-community/FHIR-AI-Hackathon-Kit/tree/V2)? Backend works with
  either via `.env`.

## yes-and (Claude Code)

- Done (on `main`): three-phase MDT app (#1) on dataset v1.1, Docker image + Fly deploy (#2) at
  https://mdt-copilot-rakathon.fly.dev behind a shared password (ask yes-and; Fly app is on
  yes-and's personal account).
- Branch `yes-and/meeting-records` (pushed, not merged): the full role-based workflow (#16).
- Branch `yes-and/journey-meets-pipeline` (on top of `backend`): the simple coordinator journey
  (#20, docs/workflow-plan.md) joined with Contributor 2's agent. Cases are meetings over the
  FHIR server's nominated patients; the agent's briefing feeds every screen, its first option +
  léčebný záměr is the recommendation (#21), its verdicts the stanoviska, its questions a new step,
  the patient's wishes a card on Pacient (#22). "ukázka" examples remain only where the agent has
  no output (pathology stanovisko, unbriefed cases).
- The agent also runs against the local HAPI (`FHIR_BASE_URL=http://localhost:8080/fhir`, empty
  `FHIR_USER`), loaded with `mdt-load-fhir`.
- Next: trial screening (still empty). Ground truth (`ground_truth/` in the dataset README) is not
  delivered.
- Not done yet: bulk-confirm per section, AI-generated patient/GP summaries, FHIR export.
- Gaps against `MDT_ZASEDANI_PROCES.md` + the record template (not started):
  - The app's decision form doesn't follow `docs/template_zaver_zasedani/form.md`; the filled
    template exists only as the `mdt-zaver` CLI PDF; the app's PDF (`features/export.py`) has its
    own simpler layout.
  - The decision doesn't separate the MDT recommendation, the patient's decision, the agreed plan
    and the care actually delivered (§6).
  - PROMs answers are only partly split by specialty: surgery gets walking + weight change, the
    other specialist sections get none, the rest is in the `patient` section (§2).

## Contributor 2

- IRIS for Health running from `FHIR-AI-Kit/docker-iris-fhir` with the full dataset loaded
  (`uv run mdt-load-fhir`, decision 12). `uv run mdt-patient P01` pretty-prints one patient's
  complete record from the server. The web API reads it too (case list, briefings, source drawer;
  decision 18), falling back to the bundles on disk only when the server is unreachable.
- `uv run mdt-zaver P01`: MDT conclusion (form.md) as PDF, two gpt-6-luna calls (decision 13).
  CLI only — not wired into the API/UI yet; ~40 s per patient.
- `uv run mdt-agent P01 [--runs 2]`: MDT agent over IRIS (decision 17): CACC → RED/YELLOW findings
  → radiology/surgery/oncology views → 1–2 guideline options, every citation checked in code.
  Writes `data/ai_cases/<id>.json`, which `/api/cases/{id}` then serves (delete it to get the plain
  build back). Patient data comes only from IRIS (verified: no bundle file read, all reads are
  `localhost:52773/fhir/r4`). Not triggered from the UI; run `uv run mdt-agent --all` to refresh.
- App integration (decision 18, no frontend change): the agent now also writes the executive
  summary (text → key facts, extra red flags, timeline), each specialist's view as text → cited
  points, the indicators to chart (values read from the record) and the patient's preference
  (leads the patient section). 15 LLM calls per patient, ≤ 4 at once (429/5xx retried). All 6
  patients generated on 2026-10-17 (`mdt-agent --all`, ~9 min each in parallel, 1–4 rejected
  citations per patient).
- Reproducibility (2 runs each, 2026-10-16): P01 — same first option (biomarker-guided endocrine
  line after ESR1/PIK3CA/BRCA + restaging, PRS-1.3/2.2, OBC-1.2; patient's no-chemo wish mentioned)
  and same second option (chemo/T-DXd only if conditions, identical passages); all-option passage
  Jaccard 0.88. P03 — same two options (restage + HBP resectability per KRC-2.1/2.4/2.5; else drop
  oxaliplatin for neuropathy per KRC-3.2 + MMR/MSI), Jaccard 0.67. Wording and the exact list of
  findings vary between runs; the RED findings overlapped (stale staging, new hip pain without
  imaging / missing chest CT, MMR/MSI, neuropathy).
- `bundles.bundle_paths()` now finds bundles in per-patient folders (`pacienti/P01/P01_bundle.json`,
  the dataset's current layout) — before, the app found no FHIR cases with that layout.

## Contributor 3

-

## Copilot - synthetic holdout fixture

- Created isolated root-level `secret_bundles.ndjson` (P07) and evaluator-only
  `secret_ground_truth.md`. Original Dataset files and application import paths are unchanged.
- Keep the answer key out of LLM/RAG inputs. Neither artifact has been imported into a FHIR
  server or evaluated by the LLM pipeline.
- Passed official FHIR R4 JSON-schema validation and local checks for composition/size,
  references, attachments, PROM answer types, chronology, citations and label leakage.
