# Status

Who is working on what. Each contributor (and their agent) edits **only their own section**.
Keep it short: current branch, what's in progress, what's blocked, what others should know.

## yes-and (Claude Code)

- `yes-and/specialist-roles` (decision #27): role picker, the specialist's journey (Pacient →
  Klíčové informace → Stanovisko), their stanovisko generated live (~20 s) or written, their
  stance; also chevrons that remember the furthest step, "Uložit a další/zavřít", an unsaved-input
  warning, signing by role (no name fields), gender-neutral export wording.
- `yes-and/font-sizes` (on top of specialist-roles): one font size per kind of text on every
  screen (decision #26). Pacient, Průběh and Klíčové informace still scroll with P01's amount of
  data at some widths; that needs fewer items or another page, not smaller type.
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
