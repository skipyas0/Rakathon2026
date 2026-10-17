# MDT Copilot: what we build

**Audience:** the team and their coding agents. This is the scope: our core definition (§1–3)
plus every item of the official brief as a checklist (§4–7). The brief itself, verbatim, stays in
[brief.md](brief.md); how a real MDT runs is in [MDT_ZASEDANI_PROCES.md](MDT_ZASEDANI_PROCES.md),
which wins on process questions. Tags: **POVINNÉ** = mandatory in the brief, **BONUS** = optional
(up to +10 %, quality over count), **CORE** = required by our core though the brief doesn't ask.

## 1. Core

A multidisciplinary tumour board (MDT: clinical oncologist, surgeon, radiation oncologist,
radiologist, pathologist) has **3–5 minutes per patient**. Today its members dig through
unstructured reports and PDFs from eZdraví by hand and rarely see how the patient actually feels
(PROMs questionnaires).

MDT Copilot is a workflow for the **coordinator**, running over the hospital information system
(NIS), that simplifies the MDT process:

- The coordinator and the specialists get a **clear view of the patient's status**, so they decide
  better informed than when reading the provided PDFs one by one.
- A **friendly UI captures every decision that must be documented**. The record it builds follows
  [template_zaver_zasedani](template_zaver_zasedani/) (§6) and is filled in live during the meeting;
  the filled template is the meeting's conclusion.
- Everything important from the brief is covered, but not every item has to be followed literally.
- The board decides by consensus; AI proposes, clinicians decide (§3).

## 2. Inputs, outputs and where the LLM is used

- **In:** FHIR (bundles, stored on the FHIR server) and PDF (reports parsed by the LLM). **CORE**
- **Out:** PDF following the template and FHIR. **CORE** (the brief asks for PDF and/or FHIR)
- **LLM always used for:** parsing PDF input; suggestions (treatment options, questions for
  discussion); catching inconsistencies (red flags, missing data); checking that the final verdict
  is compatible with the guidelines. Everything it produces is AI output under the rules of §3.

## 3. Rules for the AI (POVINNÉ, enforced in code: see AGENTS.md)

**AI may:**
- Consolidate, filter and summarise: join free text from eZdraví with PROMs answers, structure them
  into a timeline and per-specialty sections.
- Refine the wording of the MDT question entered by the nominating doctor.
- Detect conflicts between sources and flag them: red flags, missing documents, untested
  biomarkers, a conclusion that departs from the guidelines.
- Present material for the decision: guideline passages (RAG over the provided documents only),
  trial eligibility screening, 2–3 questions for discussion, drafts of the record, indicative
  RECIST 1.1 sums.

**AI must not:**
- Choose the treatment or decide. It presents structured options; the board chooses.
- Guess, infer or use the model's general knowledge outside the provided documents. Missing data
  (MDT question, biomarker, trial criterion) is stated explicitly: *„V dostupné dokumentaci se
  nenachází.“* (or *„chybí údaj“*), and the case is marked incomplete.
- Block the board's decision. A departure from the guidelines gets a non-blocking warning and a
  request for a short justification.
- Put unconfirmed output into the official record: no text, extracted value, RECIST sum or scribe
  draft becomes official without a clinician's explicit confirmation.

**Output format:**
- AI output is visually distinct from clinician-confirmed content, in the UI and in exports.
- Every AI claim is interactive: a click shows the primary source (the finding in eZdraví, the
  guideline passage, the PROMs answer).
- Every red flag has a severity and cites both conflicting sources.
- Trial screening states, per criterion, `potenciálně vhodný` / `nevhodný` / `chybí údaj` + reason.

## 4. Technical constraints (CORE)

- **FHIR server = InterSystems IRIS for Health** (sponsor bonus). The app works only over FHIR: patient
  data are read from the server, never from files on disk.
- **Deployment:** Docker, on Fly.io (a machine big enough to run IRIS alongside the app).
- **Quick iteration:** layout and functionality are tuned by trying the running app. Getting it
  running needs no test suite; checks stay light (lint, build, a few smoke tests).
- Follow the usual conventions for a FastAPI + React app wherever possible.
- Synthetic data only; never real patient data or keys in the repo.

## 5. Requirements checklist

### Data
- **POVINNÉ** Consolidate two different sources: unstructured reports from eZdraví (discharge
  reports, labs and tumour markers, CT/MRI reports, medication) with structured PROMs (quality of
  life, symptoms) and the nomination data.

### Block A: Executive Summary (orientation in 30 seconds)
- **POVINNÉ** Identification and clinical state: main oncological diagnosis, main reason for the MDT,
  ECOG 0–4 rated by the doctor and reported by the patient side by side (a marked difference is
  automatically a red flag).
- **POVINNÉ** MDT question: the structured question from the nominating doctor. AI may refine it but
  never invent it; if missing, the case is marked incomplete.
- **POVINNÉ** Clinical timeline (AI-generated): date of diagnosis, staging, surgeries, lines of
  systemic therapy and radiotherapy, key imaging, progression, previous MDT conclusions.
- **BONUS** Case readiness: a traffic light for completeness against the tumour type's template
  (missing histology, staging older than 6 weeks, untested mandatory biomarkers); AI recommends
  returning or postponing an incomplete case.

### Block B: sections per specialty
- **POVINNÉ** At least **3** of these 5 views:
  - *Surgery:* resectability, TNM staging, comorbidities affecting operability, previous surgeries,
    self-reported cardiorespiratory fitness (PROMs).
  - *Clinical oncology & pharmacotherapy:* histology and molecular pathology (HER2, MSI, KRAS,
    PD-L1, …), previous lines of chemo/immunotherapy, toxicity and side effects reported by the
    patient (PROMs).
  - *Radiology:* timeline and comparison of CT/MRI/PET-CT by RECIST (shrinking vs growing lesions,
    new metastases).
  - *Pathology:* key biopsy findings, grading, histological type, further biomarkers needed.
  - *Patient (PROMs / quality of life):* symptoms (pain, weight loss, mental state, socioeconomic
    support), the patient's goals and preferences (quality of life vs aggressive treatment,
    attitude to surgery), PROMs trend over time.
- **BONUS** AI pre-calculation of RECIST 1.1 response (sums of target lesions from report text),
  clearly marked as indicative, for the radiologist to confirm.
- **BONUS** AI suggestion of missing biomarkers required by diagnosis and guidelines (e.g. MSI/MMR
  in colorectal cancer).
- **BONUS** More roles: *nuclear medicine* (PET-CT, scintigraphy: SUVmax, new lesions); *palliative
  and supportive care* (pain, dyspnoea, nutrition; alert on worse PS + high symptom burden +
  progression); *geriatric oncology / frailty* (G8 screening, polypharmacy, social background for
  treatment intensity); *clinical genetics* (counselling and germline testing, e.g. BRCA1/2, Lynch,
  from diagnosis, age, family history); *coordinator / oncology nurse* (logistics, appointments,
  patient contact, status of previous MDT conclusions).

### Block B2: Decision Support Panel (AI)
- **POVINNÉ** Treatment options from the provided guidelines (by diagnosis, stage, biomarkers,
  previous treatment), via RAG only, citing the exact passage.
- **POVINNÉ** Trial pre-screening: the patient against inclusion/exclusion criteria of open trials,
  per-criterion status and reason (§3).
- **POVINNÉ** 2–3 key questions the board must resolve.
- **POVINNÉ** Guideline compliance check when the conclusion is written: non-blocking warning on a
  departure, asks for a short justification. (LLM, §2.)
- **BONUS** Similar cases: anonymised previous MDT conclusions with a similar constellation, as
  inspiration, not recommendation.

### Block C: MDT resolution & action plan
- **POVINNÉ** Write and edit the final recommendation during or at the end of the meeting, including
  the re-evaluation date.
- **POVINNÉ** Structured record (not just free text): members present and specialties (quorum),
  options considered, chosen course, justification, guideline compliance (yes/no + reason for the
  departure), dissenting opinions, trial enrolment. **CORE:** it fills the template (§6).
- **POVINNÉ** Export the final briefing with the conclusion to the health record. **CORE:** both PDF
  (the template) and FHIR.
- **BONUS** FHIR R4 / mCODE mapping of the export (§7).
- **BONUS** AI scribe: draft the conclusion and action items from a transcript (text or audio) of the
  discussion, AI draft distinct from the chair's confirmed text.
- **BONUS** Action plan: each task has an owner, deadline and status (e.g. "order PET-CT –
  coordinator – within 14 days"); track whether the conclusion was carried out.
- **BONUS** Plain-language summary for the patient and a short report for the GP / referring doctor,
  approved by a clinician.
- **BONUS** Locking and versioning: the chair confirms and locks the record; every later change is a
  new version with an audit trail.

### System, AI interpretation and safety
- **POVINNÉ** Configuration before generating, by the chair or an admin: which sections and in what order, which specialties
  are present (hide or move an absent one), level of detail (bullets vs narrative).
- **POVINNÉ** Red flags with severity and double citation: conflicts between objective findings and
  the questionnaire (e.g. falling haemoglobin + extreme fatigue, doctor's vs patient's ECOG).
- **POVINNÉ** Explainability: the exact source record (eZdraví or questionnaire) on click for every AI
  claim; missing data admitted, never estimated.
- **BONUS** Templates per tumour type / board (colorectal, breast, lung, GI, uro-oncology) with
  mandatory data elements for the completeness check.
- **BONUS** Configurable red-flag rules (activation, thresholds) and choice of guideline/trial
  documents the AI uses.
- **BONUS** Default view per role (e.g. the surgeon's section right under the summary).
- **BONUS** More red-flag types: conflicts between reports (different TNM), stale documents, a new
  symptom without matching tests (bone pain → consider scintigraphy), rising markers with "stable"
  imaging, significant drug interactions, worsening PROMs trend.
- **BONUS** Sentence-level citations: highlighted passage in the source with its date and author;
  confidence score for derived values.
- **BONUS** Structured NLP extraction (single source of truth): TNM, histology, biomarkers, lines of
  treatment, doses, RECIST, linked to sources, confirmed or corrected in one click; every section is
  built from the same elements, so one value can't differ between sections.
- **BONUS** Q&A assistant over the case during the meeting, answering only from the patient's data,
  with citations.
- **BONUS** Safety and evaluation: *audit trail* (model version, prompt, sources, who confirmed or
  edited); *data protection* (pseudonymisation before the model, EU / on-premise processing, data
  minimisation, GDPR; how it fits AI Act and MDR as a likely high-risk system / medical device);
  *evaluation* on a control set of facts and planted errors (citation accuracy, hallucination rate,
  red-flag recall against ground truth).

## 6. The final record: template_zaver_zasedani

The template ([form.md](template_zaver_zasedani/form.md), original `.docx` alongside) is available
in the app and filled in continuously during the meeting; the filled template is the automatic
output saved as the meeting's conclusion. It comes from a sarcoma board, so its department names are
an example of the board's composition. Fields:

- **Header:** board members per department (imaging, oncology, surgery, pathology, oncology care
  coordinator); patient name, birth number (insurer), address, phone.
- **Body:** short epicrisis; history: main diagnosis; staging (CT, MR, PET/CT, histology); therapy
  (neoadjuvant, surgery, operative and post-operative complications, definitive histology,
  adjuvant); follow-up (duration, local recurrence, generalisation); latest imaging (CT, MR, PET/CT,
  other); imaging presented at the MDT; question for the MDT.
- **Response:** the MDT conclusion, carrying the structured record of Block C (quorum, options
  considered, chosen course, re-evaluation date, justification, guideline compliance, dissent,
  trial).

## 7. Standards and FHIR mapping

- FHIR R4 with the oncology profiles **mCODE** or **HL7 Europe Common Cancer Model**: `Condition`
  (diagnosis, TNM), `Observation` (biomarkers, ECOG, PROMs), `QuestionnaireResponse`, `CarePlan` +
  `Task` (decision and action items), `Provenance` (where each claim came from, who confirmed it).
- Code systems where possible: **MKN-10 / ICD-O-3** (diagnoses, tumour morphology), **LOINC** (labs),
  **SNOMED CT** (clinical concepts); profiles mCODE / IPS.

## 8. The MDT process the app supports

Three phases, all supported (detail in [MDT_ZASEDANI_PROCES.md](MDT_ZASEDANI_PROCES.md)):

1. **Before (nomination, preparation):** the treating doctor nominates the patient with a question;
   completeness is checked (histology, current staging, biomarkers, PROMs); the agenda is set. App:
   takes the nomination, checks the question (missing → incomplete), configures the report for the
   specialties present and tumour type; *(bonus)* case readiness.
2. **During (discussion, decision):** orientation in 3–5 minutes, each specialty's view, options
   against guidelines, trials and the patient's preferences, verdict with justification. App:
   executive summary + timeline, per-specialty sections, red flags with sources, Decision Support
   Panel, structured decision form with the compliance check; *(bonus)* Q&A, scribe.
3. **After (delivery, follow-up):** the conclusion goes into the record and to the patient and
   doctors; tasks with owners and deadlines; re-evaluation planned. App: exports the confirmed
   record (PDF, FHIR) with the re-evaluation date; *(bonus)* tasks, patient/GP summaries, locking
   and versioning.

## 9. How it's judged (from the brief)

| Criterion | Weight | What counts |
|-----------|--------|-------------|
| Clinical value & UX for the MDT | 30 % | Clear summary, understandable role sections, intuitive recording of the final recommendation |
| Configurability | 20 % | Templates, adding/removing/reordering sections for different boards |
| AI technique & reliability | 20 % | Prompting that minimises hallucination, interactive source checking, output structure kept |
| Data integration & standards | 15 % | Questionnaire joined with eZdraví findings, export, FHIR and standard terminologies |
| MDT process & responsible AI | 15 % | Decision Support Panel quality, structured decision with justification, human-in-the-loop, AI labelling |
| Bonus features | up to +10 % | Quality of implemented BONUS items |

**Demo (max 5 min, one dataset patient):** generate the briefing from a chosen configuration →
orientation in the summary within 30 s → verify one AI claim and one red flag by clicking through to
the source → Decision Support Panel (options with guideline citations, trial screening) → write and
confirm the conclusion → export. Plus implemented bonuses and a short description of the AI
architecture (model, grounding/RAG, hallucination prevention, data protection).
