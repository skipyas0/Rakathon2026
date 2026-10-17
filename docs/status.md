# Status

Who is working on what. Each contributor (and their agent) edits **only their own section**.
Keep it short: current branch, what's in progress, what's blocked, what others should know.

## yes-and (Claude Code)

- `yes-and/specialist-roles` (decision #27): role picker, the specialist's journey (Pacient →
  Klíčové informace → Stanovisko), their stanovisko generated live (~20 s) or written, their
  stance; also chevrons that remember the furthest step, "Uložit a další/zavřít", an unsaved-input
  warning, signing by role (no name fields), gender-neutral export wording.
  After merging, rerun `mdt-agent --all`: red flags then carry `area` (until then a specialist
  sees all of them) and the batch adds a pathology view.
- Fly: the web app (https://mdt-copilot-rakathon.fly.dev, yes-and's account) runs the IRIS build
  against the private app `mdt-copilot-iris` (#14); `/api/health` reports `fhir: true`.
- Next, by the scope (`problem_statement.md`): trial screening (POVINNÉ, empty); section
  order/detail configuration (POVINNÉ, 20 % of the score); PDF intake and FHIR export (CORE);
  running the agent from the app; LLM red flags and an LLM guideline-compliance check instead of
  `rules.py` and the derived soulad (CORE). Later: deleting a patient (clean re-uploads, holdout
  P07 evaluation).
- Gaps against `MDT_ZASEDANI_PROCES.md`: the decision doesn't separate the MDT recommendation, the
  patient's decision, the agreed plan and the care delivered (§6); PROMs are only partly split by
  specialty (§2).
- Open issue: every board member's stance starts as "Podporuje" (`Member.supports = True`), so
  consensus exists by default; proposed: start undecided, Potvrdit only once every stance is set.
- The agent's output leaks "[refs: …]" placeholders into some statements; strip them in the agent.
- `data/ai_cases/` is from the first agent run (old intent prompt); rerun `mdt-agent --all`.
  Ground truth (`ground_truth/` in the dataset README) is not delivered.

## Contributor 2

- IRIS for Health running from `FHIR-AI-Kit/docker-iris-fhir` with the full dataset loaded
  (`uv run mdt-load-fhir`, decision 12). `uv run mdt-patient P01` pretty-prints one patient's
  complete record from the server. The web API reads it too (case list, briefings, source drawer;
  decision 18), falling back to the bundles on disk only when the server is unreachable.
- `uv run mdt-zaver P01`: MDT conclusion (form.md) as PDF, two gpt-6-luna calls (decision 13).
- Hospital-template PDF/DOCX (decision 30): decisions only from the board (empty ones printed
  "nevyplněno"); "Zobrazovací metody MDT" = the radiologist's signed stanovisko or "Stanovisko
  radiologa nebylo zaznamenáno"; compliance = AI assessment + the board's own reasons.
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

## Codex

- PDF export typography now follows the 15 pt / 11.5 pt / 9.5 pt legend; AI-source captions remain
  at 6.5 pt. Header uses the gender-neutral coordinator label, lists each mapped member as
  `Jméno, odbornost`, and no longer adds a "Další odbornosti" row. Export tests pass (4/4).

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
- Second merge: `origin/main` at `c0b502f` (UI polish + deployment/export fixes), preserving
  v2 rules and study screening. Adopted the new navigation, responsive charts and PDF/DOCX
  export; ported verbatim ECOG/PROM excerpts into v2 rules and exposed patient age in source text.
  Recovery ref: `recovery/backend-before-main-20261017-0729`.
- Second-merge validation: backend pytest (101 passed), Ruff lint/format (passed), frontend
  lint/build (passed); browser shows all six studies alongside Předchozí / Další navigation.

## Copilot - FHIR export rulebook

- Initial research: prepared [fhir-export-rulebook.md](fhir-export-rulebook.md) as an implementation
  proposal without application changes; the implemented subset is recorded below.
- Recommendation: R4 document export using validated mCODE STU4 profiles where applicable, local
  Czech MDT workflow profiles, and a versioned ECCDM logical-model crosswalk. ECCDM's published
  1.0.0-ballot implementation material is informative, not a complete oncology profile contract.
- Covers the brief's Condition/TNM, Observation, QuestionnaireResponse, CarePlan/Task and Provenance
  requirements; exact-revision clinical approval, consensus, immutable snapshots and acceptance tests.
- Initial research inspected official published specifications and current source contracts;
  no implementation/conformance claim was made in that documentation-only phase.
- Extended the rulebook with an explicit pre-confirmation field contract, parsing-versus-existing-AI
  reuse matrix and one-review snapshot workflow. Live IRIS/API inventory: 31 Conditions,
  578 Observations (500 coded), 24 clinician ECOG, 10 textual TNM, 46 text-code biomarkers
  (8 unperformed-test entries), 12 QuestionnaireResponses across P01-P06.
- Checked mCODE STU4 snapshots: structured Patient name and coded TNM method remain real gaps.
  Existing AI prose can supply reviewed narrative, not automatic typed mCODE facts. That research
  inventory made no LLM calls or clinical mutations; it did not establish export conformance.
- Implemented the separate report-review line/dialog below Stanoviska on Potvrzení. Final decision
  confirmation requires and approves the exact prepared revision; changed clinical/source/specialty
  inputs invalidate it. Frozen source dialogs and FHIR R4 JSON require no export-time AI
  or live clinical refresh. Legacy decisions can attest a report without resetting their plan.
- User explicitly selected the existing coordinator-role demo attestation, not verified accounts.
  Export retains source codes/text and visibly reports mCODE gaps; strict mCODE profiling and NIS
  publishing are not implemented. Questionnaire definition asset is packaged for portable PROMs.
- Validation: `cd backend && uv run pytest -q` (121 passed; existing Starlette/httpx deprecation
  warning), `cd backend && uv run ruff check .` and `uv run ruff format --check .` (passed),
  `cd frontend && npm run lint && npm run build` (passed), `git diff --check` (passed).
  Browser verified the report button, blocked confirmation before review, report dialog and frozen-source inspection.
  Six locally generated P01-P06 documents passed the official FHIR R4 JSON schema (zero errors);
  this does not claim full mCODE/terminology validation. No real case was finally confirmed in testing.
- Subsequent user change: restored original hospital-template PDF/DOCX and cached AI-history draft
  workflow for later clinician review, independent of FHIR approval. Removed the appended FHIR
  evidence/warnings from those formats and the mCODE disclaimer from the download button.
  The report viewer retains conformance limitations; the FHIR snapshot/approval behavior is unchanged.
  Revalidation: 122 backend tests passed; frontend lint/build passed. Regression tests assert the
  original three template sections, AI review notice, no FHIR appendix and independent FHIR gating.
