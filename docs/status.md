# Status

Who is working on what. Each contributor (and their agent) edits **only their own section**.
Keep it short: current branch, what's in progress, what's blocked, what others should know.

## yes-and (Claude Code)

- Branch `yes-and/trim-dead-files`: repo cleanup, step 1 — holdout files moved to
  `Dataset/holdout/` (decision 23), `brief.docx` removed (`brief.md` is the same text); scope
  rewritten as core + checklist in `problem_statement.md` (decision 24); IRIS only, FHIR only (`iris/`, no
  HAPI/stubs/disk fallback). Next: one conclusion PDF following `template_zaver_zasedani`; docs
  trim. Future: patient deletion (clean re-uploads, holdout P07 evaluation).

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
- Red-flag rules v2 (decision 19): generic families A–H over a concept layer, configured in
  `backend/src/mdt_backend/rules.toml`; LLM symptom classifier in the agent, keyword fallback in
  the plain briefing. 10–15 flags per patient (P01–P06), each with record sources and guideline
  passage; unit tests on synthetic records with other codes/wording (`tests/test_rules.py`). The
  P07 holdout was not used for design or tuning — evaluate on it.
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

## Copilot - IRIS deployment documentation

- Added [iris-fhir-deployment.md](iris-fhir-deployment.md): server behavior, existing
  Docker configuration, restart steps, and a combined IRIS/web-app deployment example
  with explicit durable-volume reuse, initialization, verification, and deployment caveats.
- Documentation only; no runtime configuration or patient data changed.

## Copilot - preliminary study screening

- Implemented one cited strict-JSON LLM call in `agent.screen_trials`, feeding the existing trial
  panel and criterion confirmation flow without changing the API contract or dataset.
- User-selected priority: supported exclusion match → non-match; otherwise any supported
  inclusion match → potential match (unknown criteria allowed); otherwise data missing.
- Follow-up: a supported cancer-type mismatch also means non-match (decision 21). The same
  call adds a diagnosis statement citing `trial:<id>#diagnosis`; uncertain origin remains unknown.
- All criteria retained; absent/invalid citations become unknown and are logged. Invalid catalogue
  coverage fails explicitly. Meeting view now expands criterion evidence and labels the filter
  as preliminary, not confirmed eligibility.
- Validation: 50 screening, pipeline, briefing and provenance tests passed; changed Python files
  pass Ruff lint/format and Python syntax validation; frontend lint and production build passed.
- Live validation: all six briefings saved and served by the running API. P05 initially timed out,
  then succeeded on retry. P01–P04/P06 screening was refreshed with the cancer-type gate without
  rerunning their other LLM steps. Each case has six studies and 51 assessments (45 criteria plus
  six cancer-type assessments); saved/API results agree, with sourced claims and incompatible
  cancer types consistently marked non-match.
- Browser verified six studies, expandable criteria and source drawers with both study/patient
  evidence; P02 → COLUMBA-LM now shows non-match with the cited cancer-type explanation.

## Copilot - backend/frontend branch reconciliation

- Merged `main` into `backend` after saving the original backend tip and partial rebase under
  `recovery/backend-before-main-20261017` and `recovery/partial-rebase-20261017`.
- Preserve the v2 rules, symptom classifier and study screening; adopt the current coordinator
  journey, meeting ids, treatment intent, patient preference and AI-running status from `main`.
- The current IRIS-only policy supersedes older notes about HAPI, disk fallback and offline
  agent input. Study evidence moves to the journey discussion step; the old case view stays deleted.
- Validation: `cd backend && uv run pytest` (93 passed), `uv run ruff check .` and
  `uv run ruff format --check .` (passed); `cd frontend && npm run lint && npm run build`
  (passed). Regression tests cover the full pipeline output served under a meeting id, including
  v2 flags, studies, preference, intent and AI status, plus running-marker cleanup on failure.
