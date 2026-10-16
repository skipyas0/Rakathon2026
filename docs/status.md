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
- Branch `yes-and/mdt-workflow`: role-based workflow per [workflow-plan.md](workflow-plan.md) (#16).
  Step 1 next: records per meeting + role switcher. Needs backend changes (listed in the plan),
  kept in `features/` to avoid clashing with Contributor 2.
- Next: decision support (guideline options, trial screening, questions) from `knowledge.py` via
  `llm.chat_json` (#13). Ground truth (`ground_truth/` in the dataset README) is not delivered.
- Not done yet: bulk-confirm per section, AI-generated patient/GP summaries, FHIR export.
- Gaps against `MDT_ZASEDANI_PROCES.md` + the record template (not started):
  - The app's decision form doesn't follow `docs/template_zaver_zasedani/form.md`; the filled
    template exists only as the `mdt-zaver` CLI PDF, and the app's export is a print of the
    follow-up page.
  - The decision doesn't separate the MDT recommendation, the patient's decision, the agreed plan
    and the care actually delivered (§6).
  - PROMs answers are only partly split by specialty: surgery gets walking + weight change, the
    other specialist sections get none, the rest is in the `patient` section (§2).

## Contributor 2

- IRIS for Health running from `FHIR-AI-Kit/docker-iris-fhir` with the full dataset loaded
  (`uv run mdt-load-fhir`, decision 12). `uv run mdt-patient P01` pretty-prints one patient's
  complete record from the server. The app itself still reads bundles from disk (`bundles.py`).
- `uv run mdt-zaver P01`: MDT conclusion (form.md) as PDF, two gpt-6-luna calls (decision 13).
  CLI only — not wired into the API/UI yet; ~40 s per patient.
- `uv run mdt-agent P01 [--runs 2]`: MDT agent over IRIS (decision 17): CACC → RED/YELLOW findings
  → radiology/surgery/oncology views → 1–2 guideline options, every citation checked in code.
  Writes `data/ai_cases/<id>.json`, which `/api/cases/{id}` then serves (delete it to get the plain
  build back). Patient data comes only from IRIS (verified: no bundle file read, all reads are
  `localhost:52773/fhir/r4`). ~2–2.5 min per run (8 LLM calls, 3 in parallel). Not triggered from the UI yet.
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
