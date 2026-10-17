# MDT FHIR export: implementation rulebook

**Status:** researched implementation proposal, not implemented or clinically approved.
**Research checked:** 17 October 2026.
**Scope:** export the patient evidence, MDT process, recommendation and action plan alongside
the existing hospital-template PDF/DOCX. No new treatment decisions or automatic orders.

## 1. Recommendation: mCODE implementation patterns, ECCDM semantic alignment

Use **FHIR R4 4.0.1**, matching the dataset and IRIS deployment. Use **mCODE STU4 4.0.0**
as the concrete oncology implementation reference, and maintain an explicit crosswalk to
**HL7 Europe Cancer Common Data Model (ECCDM) 1.0.0-ballot**.

Do not describe the initial implementation as universally interoperable, fully ECCDM compliant,
or a fully conformant mCODE Data Sender. The intended initial claim is:

> FHIR R4 MDT document export, using validated mCODE profiles where applicable, with documented
> local R4 profiles for Czech MDT workflow and an ECCDM logical-model crosswalk.

### Why this choice

| Criterion | ECCDM published ballot | mCODE STU4 | Consequence for this project |
|---|---|---|---|
| Purpose | European, cancer-type-independent conceptual/logical backbone; primary and secondary use | Concrete oncology FHIR exchange specification | Keep ECCDM semantics; implement using testable FHIR patterns |
| Publication checked | 1.0.0-ballot, dated 14 June 2026 | 4.0.0, dated 16 February 2025 | Pin these versions; do not silently follow CI builds |
| Implementable profiles | Published artifact list has Patient and Comorbidities Observation profiles; implementation material is explicitly informative/future work | Approximately 40 profiles, terminology bindings and explicit conformance rules | mCODE is the more actionable oncology reference today |
| Diagnosis and staging | Logical models exist, but are not ready-made Condition/TNM resource profiles | Primary/secondary cancer conditions, cancer stage/TNM observations | Use mCODE patterns for these data |
| Czech fit | European intent is appropriate, but does not yet specify a complete Czech exchange contract | Many profiles inherit US Core 6.1.0; US terminology and demographic assumptions need checking | Preserve Czech coding; do not manufacture US-compatible data |
| MDT workflow, PROMs and AI approval | Does not supply the complete required workflow/approval contract | Does not supply the complete required workflow/approval contract either | Add narrowly scoped local profiles over base R4 |
| Honest conformance test | Crosswalk coverage and preservation of logical relationships; not blanket profile validation | Validate each declared profile and its dependencies; system-level conformance is additional work | Publish exactly what is implemented and tested |

ECCDM is **not badly defined as a clinical model**. Its current publication explicitly separates
the reviewed functional/logical model from evolving FHIR implementation material. Treating logical
models as clinical resource profiles would be the mistake.

The ECCDM continuous build checked is dated 15 September 2026, but labels itself an unauthorized,
regularly changing CI build. Reassess published releases before implementation and upgrades.

### Profile adoption policy

1. Inventory the source data against the full snapshots of the selected mCODE profiles,
   including inherited constraints, reference target profiles, invariants and terminology bindings.
2. Reuse an official profile only when the resource and relevant reference graph genuinely conform.
   Declare only those profiles in `meta.profile`.
3. Where a Czech requirement or missing source data prevents conformance, define a local profile
   directly over R4, documenting its mCODE crosswalk and differences. A derived mCODE profile
   cannot relax its parent's requirements.
4. Do not relabel Czech MKN-10 as ICD-10-CM. Preserve original codes and versions; add an equivalent
   SNOMED CT coding only through a verified terminology mapping or explicit clinical review.
5. Publish a local ImplementationGuide, supported-profile list, terminology manifest and export
   CapabilityStatement. Claiming a complete mCODE Data Sender additionally requires the applicable
   mCODE system-level requirements, not merely a valid JSON file.

**First profile candidates:** Primary Cancer Condition, Secondary Cancer Condition, TNM Stage Group
and TNM component profiles, ECOG Performance Status, Tumor Marker Test, Cancer Disease Status and
Cancer Genomics profiles when the underlying data support them. This is a candidate set, not a
promise that today's dataset passes those profiles.

## 2. Existing application: what must change

The relevant contracts are [CaseRecord and Decision](../backend/src/mdt_backend/features/records.py),
[Statement and Source](../backend/src/mdt_backend/provenance.py), the
[current export](../backend/src/mdt_backend/features/export.py), and the
[journey UI](../frontend/src/Journey.tsx). The [workflow](workflow-plan.md) and
[confirmed MDT process](MDT_ZASEDANI_PROCES.md) govern the implementation.

| Current behavior | Required implementation change |
|---|---|
| PDF/DOCX work; FHIR is a disabled export tile | Add a downloadable R4 document, then a separately controlled IRIS publishing operation |
| Decision confirmation is a typed name and timestamp | Bind clinical approval to authenticated identity and authorization; preserve the typed display name only as display |
| Coordinator records consensus; member support defaults to true | Start each member undecided, explicitly record support/opposition/abstention and recorder/time; do not invent member signatures |
| Confirmations are keyed by mutable statement paths | Give claims stable IDs and revisions; bind approval to exact content, source versions and mapping version |
| AI history is generated on the Export screen after decision confirmation | Generate before final review; require its own approval. Earlier decision approval cannot approve later text |
| AI template fields contain values and source IDs, not full claim-level approval metadata | Use the shared claim/provenance contract for every exported AI field, including narrative and terminology proposals |
| Tasks have text, free-text assignee, due date and done flag | Add stable IDs, responsible identities, lifecycle state and completion evidence; preserve unknown legacy values |
| Confirmed decision is locked, but other content can change and demo reset deletes records | Freeze a full approved export revision; use amendment/supersession instead of deleting published history |
| Patient stance and agreed plan exist in the backend but not the simple journey | Expose them when captured; keep them distinct from the MDT recommendation and delivered treatment |

PDF/DOCX already exist, so retain them. Their inclusion of AI history marked "to be checked" must
not be mistaken for approval. Official PDF and FHIR should eventually render the same approved
snapshot; a working draft can remain available but must be unmistakably non-final.

## 3. Shared translation rules

**R1 — Deterministic export.** Read a frozen clinical snapshot and serialize it. Do not call an LLM
while downloading or publishing a final record. AI extraction, summarization and coding proposals
occur upstream and require review.

**R2 — Preserve evidence.** Existing clinician-authored FHIR resources and patient responses retain
their authors, status, clinical time, original coding and identity. Copying evidence does not mean
the board reauthored it. Record export assembly separately.

**R3 — Do not infer clinical facts.** Never infer stage from metastases, treatment administration
from a recommendation, consent from attendance, or study enrollment from AI pre-screening.
Structured terminology assignment by AI is itself an AI-generated assertion requiring approval.

**R4 — Keep times distinct.** Preserve diagnosis, sample, observation, questionnaire, meeting,
AI generation, human approval and export times. Export time must not replace clinical time.
Keep date-only/year-only precision; use timezone-aware instants where required.

**R5 — Keep uncertainty and disagreement.** Distinguish unknown, not measured, not applicable,
negative and conflicting. Never emit zero/false/negative because a field is absent.
Do not silently select the newest or most convenient conflicting result.

**R6 — Stable identity.** Identify patient, cancer episode, meeting, claim, plan, task and document
revision separately. Resolve identities through identifiers and an explicit mapping, not names.
Two independent primary tumors require separate cancer identities.

**R7 — Controlled terminology.** Prefer the exact profile's terminology where applicable:
LOINC for observation questions/tests, SNOMED CT for suitable clinical concepts, UCUM for physical
units, original MKN-10 and ICD-O-3 for diagnosis/topography/morphology as appropriate.
Record system, code, display and version when known. Preserve original text.
Local codes need an owned canonical namespace and published definitions; dataset example.org
identifiers are not production terminology services.

**R8 — No fake profile claims.** A resource with an mCODE-looking shape is not automatically
conformant. Required and extensible bindings, inherited US Core requirements and referenced
profiles matter. Check terminology licensing and availability with the receiving organization.

**R9 — Explicit incompleteness.** Surface missing facts and mappings in an export-readiness report.
Omit optional unknown elements; use `dataAbsentReason` only where semantically appropriate and
permitted by the selected profile. Do not create an empty required-value Tumor Marker Test to
represent a test never performed. An approved deferred/conditional recommendation may be exported
despite missing clinical evidence if it faithfully states the limitations.

## 4. Resource mapping rulebook

### 4.1 Patient case: Condition and staging Observation

| Board/source data | FHIR representation | Translation and review rules |
|---|---|---|
| Primary diagnosis | `Condition.code`, `subject`, `bodySite`, `onset[x]`, `recordedDate`, clinical/verification status | One identity per primary cancer; retain original coding and uncertainty. Clinical verification status is not an AI-approval flag |
| Histology, morphology, behavior, grade | Selected mCODE extensions/profiles, or documented local R4 equivalents | Keep ICD-O morphology distinct from diagnosis code and topography; do not pack all meanings into `Condition.code` |
| TNM stage group | Stage-group `Observation`, with `focus` referencing the cancer Condition | Preserve assessment date, staging system/edition and clinical/pathological/post-therapy context |
| T, N and M categories | Separate TNM category Observations, grouped through the selected stage profile's `hasMember` pattern | Preserve c/p/yc/yp context; do not mix components from different dates or systems |
| Condition-level stage summary | `Condition.stage.summary`, `type`, `assessment` references | Link to detailed stage Observations. A summary must not be the only structured TNM representation |
| Metastasis or second primary | Secondary cancer Condition versus another primary Condition, with documented relationship | Suspected origin remains suspected. The board must resolve or explicitly retain uncertainty |
| Progression/current disease state | Dated disease-status Observation focused on the relevant cancer | Preserve initial diagnosis/stage; new evidence must not erase historical assessments |

The brief's “Condition (diagnóza, TNM)” is satisfied by a diagnosis Condition linked to staging
Observations. mCODE explicitly requires staging in Observations rather than only a TNM text string
on Condition. If the source only has unstructured TNM, keep that evidence until extraction and
coding are reviewed.

Do not equate AJCC and UICC editions or derive a stage group automatically from T/N/M. Missing
staging method/edition is a readiness finding and can prevent declaring a particular profile.

### 4.2 Biomarkers, performance status and PROMs: Observation

| Data | Mapping | Critical distinctions |
|---|---|---|
| HER2, ER/PR, MSI/MMR, PD-L1, tumor markers | Observation with exact test code, typed `value[x]`, clinical time, specimen/method/performer when available | Preserve IHC versus ISH, percentage versus qualitative result, PD-L1 TPS versus CPS, and tumor site/sample date |
| Gene variants, e.g. BRCA2/KRAS | Appropriate genomics Observation/report pattern where evidence supports it | Tumor finding is not a germline diagnosis; do not infer pathogenicity, inheritance or eligibility |
| Clinician ECOG | ECOG Observation; mCODE uses LOINC `89247-1` and integer value | Keep clinician performer and assessment date; enforce the selected profile's range/invariants |
| Patient-reported functional status | Separate patient-reported Observation derived from QuestionnaireResponse | Never silently replace clinician ECOG or claim a locally worded question is a validated clinician assessment |
| PROM symptom scores | One Observation per selected answer/score and collection time, `derivedFrom` the source QuestionnaireResponse | Preserve scale, recall period, respondent and exact question identity; trends require multiple dated observations |
| Calculated score or RECIST summary | Derived Observation with evidence links, calculation/method version and provenance | AI-derived values remain drafts until reviewed; do not label an indicative calculation a confirmed radiology assessment |

Use UCUM for actual physical quantities. A locally defined 0–10 ordinal score is not a physical
measurement: preserve the scale definition and use an appropriate integer or supported score
representation rather than inventing a UCUM unit.

### 4.3 QuestionnaireResponse: preserve the patient's voice

- Include the original responses and the exact Questionnaire definition/version, including both
  time points where available. Preserve nested/repeated items and all answers, not just the first.
- Preserve `questionnaire`, `subject`, `authored`, `author`, `source`, `status`, `item.linkId` and
  typed answers. Author/data-entry person and respondent need not be the same person.
- For derived PROM Observations, record `derivedFrom` to the response and an explicit item selector.
  A clinical reviewer approves the extraction/interpretation, not the truth of a patient's feelings.
- The supplied `MDT-PROMS-1` is a custom illustrative instrument. Do not relabel it as EORTC QLQ-C30,
  PRO-CTCAE or another validated instrument, and do not invent their scoring algorithms.
- Original patient responses can be exported as attributed source evidence without pretending they
  were AI-generated or clinician-authored. Any AI summary or recoding of them needs approval.

### 4.4 MDT process and selected treatment: Composition, CarePlan and Task

Use `Composition` for the signed-off meeting record and `CarePlan` for the structured
recommendation. Include the referring `ServiceRequest`, original nomination Task and previous MDT
references when relevant, rather than representing every meeting as an isolated patient summary.

| Application data | FHIR mapping | Rule |
|---|---|---|
| Board, date, patient, meeting ID | Composition subject/date/identifier; CareTeam and identified participants | Meeting date is not the export date |
| MDT question and referral | Composition question section; nomination ServiceRequest and supporting evidence | Preserve referring clinician; AI refinement must be approved |
| Attendees and specialties | CareTeam participants with Practitioner/PractitionerRole references | Attendance is not agreement or attestation |
| Specialist notes, alternatives, rationale, dissent, consensus | Distinct Composition sections with attributable content; local extensions only for genuinely structured gaps | Preserve authors/times. Coordinator's recorded consensus is not a claim that each member digitally signed |
| Selected approach | CarePlan `description`, `addresses`, `supportingInfo`, `careTeam`, activities; Composition conclusion section | A confirmed board recommendation normally has `intent = proposal`; approval does not make it an order |
| Treatment aim | Suitable treatment-intent extension and/or referenced Goal under the chosen profile | Curative/palliative/supportive/surveillance/deferred must not be put in CarePlan.intent |
| Guideline assessment and deviation | Attributed Composition section, evidence references and separately recorded human decision/reason | AI assessment and board's disposition remain distinct |
| Follow-up/re-evaluation | CarePlan activity and Task with responsible party and requested date | Do not fabricate a deadline or assignee |
| Action plan | Task per action, `for` patient, `basedOn` CarePlan, `owner`, requester, description, status and timestamps | CarePlan.activity.reference can reference Task in R4; use Task.focus for a concrete request being actioned |
| Patient acceptance/refusal/discussion | Attributed patient-stance section; separate agreed CarePlan if one exists | Not equivalent to consent paperwork and must not rewrite the MDT recommendation |
| Actual treatment | Existing Procedure/MedicationAdministration and other event resources | Never manufacture performed treatment from the selected approach |

**Lifecycle rules:**

- Clinical CarePlan status and authorship approval are separate concepts. An operative recommendation
  can be `active` while still having `intent = proposal`. Use `draft` while being prepared.
  “Deferred” is a board outcome, not automatically `CarePlan.status = on-hold`.
- Use Task `draft` before release, `requested` when released but not accepted, and later
  `accepted`/`ready`/`in-progress`/`completed` only on the relevant recorded workflow transition.
  Export does not start or complete work.
- Requested fulfillment dates belong in `Task.restriction.period`; actual work timestamps belong
  in `executionPeriod`. A calendar due date needs an agreed local timezone/date-boundary convention.
- Existing `done = true` does not establish when, by whom, or what treatment was delivered.
  Preserve legacy completion with explicit provenance and unknown timestamps; do not invent them.
- An assigned task is not a medication/procedure order. Initially export only recommendations and
  coordination tasks. Creating actionable MedicationRequest/ServiceRequest orders requires a
  separate authorized clinical ordering workflow.
- Current consensus policy blocks finalization if anyone opposes or has not explicitly responded.
  Historical dissent or alternative opinions can remain documented alongside the final consensus.
  Never retroactively invent individual approvals from the default-support state.

## 5. Trustworthy AI and sign-off

### 5.1 Approval contract

Every AI-generated clinical assertion, interpretation, narrative paragraph, calculated value,
terminology proposal, guideline verdict and proposed action included in the **official record**
must have explicit human approval of its exact revision.

Maintain a claim ledger with:

- Stable claim ID and revision; clinical meaning and export target.
- Original AI wording/value and final human-approved wording/value.
- Origin: original record, patient-reported, human-entered, deterministic derivation or AI proposal.
- Exact source resource identity/version and selectors for the relevant field, passage or answer.
- Model/deployment version, prompt/template version, generation time and calculation/mapping version.
- Review state: proposed, approved, rejected or superseded; reviewer identity, role, time and reason.
- Content/source digest binding the review to the exact reviewed artifact.

Approval flow:

1. Coordinator prepares evidence and drafts; reviewers see sources, conflicts and missing data.
2. An authorized clinician approves/edits/rejects AI claims. A batch approval is acceptable only
   when it explicitly enumerates the displayed claims and revisions; no implicit blanket checkbox.
3. Record each board member's stance and the coordinator recording the consensus.
4. The authorized clinical attester reviews the complete export snapshot and approves it.
   A non-clinical coordinator may record consensus but cannot substitute for clinical AI approval.
5. Freeze the revision, validate, and enable the official download/publish action.

Changing approved text, coding, source versions or relevant interpretation invalidates the affected
approval and the final snapshot attestation. A new AI generation never inherits approval.
An unchanged re-download of the same approved revision does not require fresh clinical approval.

Unapproved/rejected AI content stays in a clearly separated audit/draft store, not in official
Condition/Observation/CarePlan values or final narrative. Required unresolved draft content blocks
finalization; optional omitted proposals are listed in the readiness report for explicit review.
Missing clinical evidence can remain explicitly unknown in a clinically approved conditional plan.

### 5.2 Provenance resource rules

Represent separate generation, revision, approval and assembly events with separate Provenance
resources, rather than overwriting the AI origin with the human reviewer's name.

| Event | Provenance content |
|---|---|
| AI generation | `activity` identifies generation; `agent.who` references a software Device; source evidence in `entity`; generation time distinct from `recorded` |
| Human editing | Editing clinician as agent, prior revision as entity, newly approved/reviewable content as target |
| Clinical approval | Authenticated Practitioner/PractitionerRole as agent with approval role/activity; exact approved resource revision(s) as target; occurrence and recorded time |
| Document assembly/export | Exporting software/organization as agent; source snapshot and source resources as entities; assembled document as target |

Use an owned, published CodeSystem for local activity/role codes where standard codes do not express
the intended event. Do not claim custom AI flags or approval states are standard FHIR elements.

Provenance generally targets **resources**, not arbitrary JSON properties. Prefer separately
attributable clinical resources. Where a Composition contains claims with different origins or
reviewers, define a local claim-selector/approval-manifest extension with stable IDs and exact
element paths; validate it and provide a readable origin/approval legend in the narrative.
Do not treat one Provenance over a mixed resource as proof that every field shares the same origin.

For stored resources use version-specific references where available. Within the immutable document,
bundle-local references identify the frozen copies. Preserve the source server URI/version and
digest as lineage; do not carry source-server `meta.versionId` as if it were the destination version.

The existing `QuestionnaireResponse/id#linkId` convention is an application citation, not a portable
FHIR item reference. In FHIR, fragments identify contained resources; migrate answer locators to
an explicit selector tied to the actual QuestionnaireResponse reference. Likewise, guideline
citations such as local passage IDs need resolvable DocumentReference/Library evidence metadata
and passage selectors, not fake clinical resource references.

Use `Composition.attester` for final document attestation. An authenticated electronic attestation
is not automatically a cryptographic signature or qualified signature. Add `Provenance.signature`
or Bundle signature only when actual signature generation/verification, trust and institutional
requirements are implemented. A typed name alone is insufficient evidence of trusted identity.

Store rejected drafts and approval history with appropriate access/retention controls. Use
AuditEvent or equivalent security audit logs for viewing/export/publishing; this complements rather
than replaces Provenance. Do not export hidden prompts, credentials or unnecessary patient context.

## 6. ECCDM crosswalk

Maintain this as a versioned mapping artifact, not an unsupported compliance label.
Expand it to field-level mappings, cardinalities and missing-data rules during implementation.

| ECCDM logical concept | Proposed FHIR graph | Scope/limitations |
|---|---|---|
| CancerPatient | Patient | Identity matching and available demographic precision; no invented identifiers |
| CancerConditionAtDiagnosis | Primary Condition plus histology/grade evidence and diagnostic report references | Preserve bodySite, histology/behavior and diagnostic dates. ECCDM bodySite is required; report a gap if absent |
| CancerStage | Stage and T/N/M Observations linked to Condition and evidence | Preserve classification/type and evidence; ECCDM models first-diagnosis staging separately |
| ClinicalCancerProgression | Dated disease-status Observation, secondary Conditions and site evidence | Link back to initial cancer; preserve disease status, asserted date and extent without inferring them |
| OverallCancerTreatmentResponse | Response Observation linked to cancer and treatment evidence | Record response type/date; approximate AI RECIST is not a confirmed response |
| Surgery / Radiotherapy / SystemicTreatment | Actual Procedure/MedicationAdministration and treatment-course representation | Only from documented delivered treatment. A proposed CarePlan is not an administered ECCDM treatment episode |
| ActiveSurveillance / LastFollowUp | Appropriate plan plus separately dated follow-up assessments | Intention to monitor is distinct from an actual follow-up event |
| MDT recommendation, PROMs, AI review | Composition/CarePlan/Task, QuestionnaireResponse/Observation, Provenance | Additional local workflow semantics; do not force them into unrelated ECCDM concepts |

For each field record: source path, ECCDM path/version, FHIR target/profile/version, terminology,
transformation, provenance selector, reviewer rule, validation rule and known loss/gap.
Use a ConceptMap for terminology mappings where appropriate, not as a substitute for the full
structural crosswalk. Classify mappings as exact, narrower, broader or unmapped.

## 7. Export packaging and integration

### First deliverable: portable clinical document

Download one JSON FHIR Bundle with:

- `type = document`, a globally unique business identifier and timestamp.
- Composition as the first entry, final only after approval, with sections for question, evidence,
  clinical assessment, PROMs/preferences, MDT discussion/consensus, recommendation, action plan and
  approval/provenance summary.
- Patient, cancer Conditions, relevant Observations, Questionnaire/Responses, CarePlan, Tasks,
  CareTeam/PractitionerRole/Practitioner/Organization/Device and relevant source evidence.
- All document-required references resolved within the bundle; stable `fullUrl` values and
  consistent references. Select clinically relevant evidence rather than dumping the entire chart.
- Provenance alongside the clinical resources and a human-readable legend distinguishing
  original evidence, patient-reported data, AI-assisted/clinician-approved content and human decisions.
- `application/fhir+json` media type; deterministic content for the same frozen revision.

Include the PDF through DocumentReference/Binary only if useful and permitted by the agreed size
and content policy. The machine-readable document must not depend on the hospital PDF template.
Generate PDF and FHIR from the same approved content, not by parsing the generated PDF.

### Separate deliverable: IRIS/NIS publishing

A document Bundle is not a transaction Bundle. Persist the signed-off document and/or publish
individual resources through an explicitly designed transaction adapter, according to the receiver's
CapabilityStatement and document-ingestion contract.

- Agree patient/organization/practitioner identity matching and a sandbox endpoint first.
- Agree supported profiles, terminology versions, extension handling and unknown-data behavior.
- Use stable business identifiers, conditional operations where supported, version-aware updates
  and optimistic concurrency. Repeated publication of one revision must not duplicate clinical data.
- Publish clinical resources and provenance consistently; verify transaction/reference behavior
  on IRIS rather than assuming support. Capture returned IDs/versions in a publication manifest.
- Inspect OperationOutcome and response entries. Report validation/identity/partial-processing
  failures explicitly; never display success merely because an HTTP request was sent.
- Corrections create an amended/superseding document with linkage to its predecessor; original
  attestation remains attached to the original content. Later Task progress must not mutate the
  historical document snapshot.
- Downloads do not equal NIS ingestion, patient consent, execution of tasks, or delivered treatment.

## 8. Implementation sequence and acceptance gates

| Step | Concrete work | Exit criterion |
|---|---|---|
| 1. Agree the exchange contract | Clinical lead and receiving-system owner approve R4, profile adoption, role authority, clinical scope and terminology policy | Signed-off profile/field inventory with explicit mCODE/ECCDM gaps |
| 2. Strengthen recording and approval | Stable claim/task/member IDs and revisions, authenticated attesters, explicit consensus, immutable snapshots, amendment rules | No AI field can become official without a valid approval of its exact revision |
| 3. Publish the local specification | Local IG/profiles/extensions, CodeSystems, terminology mappings, ECCDM crosswalk and examples | Validator can load pinned R4/mCODE/local packages; no invented canonical claims |
| 4. Implement deterministic mapping | New isolated FHIR-export feature using shared source/claim models; preserve original evidence | Required resources and relationships survive synthetic fixture round trips |
| 5. Wire the journey | Move AI draft review before final attestation; add readiness/errors, FHIR download and origin/source review | Final export cannot generate new AI text; PDF/FHIR reflect the same approved revision |
| 6. Validate IRIS/NIS integration | Test download/import separately from publishing; identity resolution, transactions, deduplication and amendments | Imported structured data and provenance are retrievable and semantically intact |
| 7. Document and release | Update architecture, decisions, workflow and status; retain PDF/DOCX regression checks | Exact supported profiles, limitations and validation evidence published |

### Required test scenarios

1. Each available P01–P06 case maps without modifying the source dataset; use synthetic fixtures
   for additional states. Do not feed evaluator-only ground truth into generation or mapping.
2. Every official AI-derived claim has source lineage, model/prompt identity and an authorized
   approving clinician/time; missing, rejected or stale approvals block official inclusion.
3. Approving a decision and then generating history does not approve that history.
4. Text/coding/source revision changes invalidate approval. Re-downloading the unchanged revision
   preserves the same frozen content and does not rerun AI.
5. All member stances must be explicit; default support, blank names and a coordinator's typed
   name cannot masquerade as individual clinical signatures.
6. Contradictory results, absent biomarkers, uncertain lesion origin and multiple primaries remain
   distinct and traceable; no fabricated stage, negative result or missing-date precision.
7. Clinical/pathological/post-treatment TNM, staging method/edition and historical stages remain
   distinguishable and tied to the right cancer.
8. Clinician ECOG and patient-reported function remain separate; both PROM time points and exact
   Questionnaire versions/items survive export, including nested/repeated/multiple answers.
9. Recommendation, patient refusal, later agreed plan, orders and actual administration cannot be
   confused. Deferred plans and unknown Task owner/due date are represented honestly.
10. Validator reports zero unresolved errors against R4 and every declared profile. Review and
    record all warnings. Terminology-unavailable/skipped checks are not reported as passes.
11. No dangling document-required references; no cross-patient leakage; every selected evidence
    version and AI approval is locatable from the exported record.
12. IRIS round-trip retrieves Condition, Observation, QuestionnaireResponse, CarePlan, Task and
    Provenance with their relationships intact. Re-publishing is idempotent; amendments preserve
    the original document and signature/attestation scope.
13. Existing PDF/DOCX tests still pass, and matched approved facts/decisions agree across formats.
    Access controls and security auditing cover download and publication.

Use the official HL7 FHIR Validator with pinned packages for profile/terminology validation and
application tests for approval, consensus and workflow rules. JSON Schema or IRIS acceptance alone
is insufficient proof of profile conformance or clinical correctness.

## 9. Primary sources

Checked official specifications rather than relying on search summaries:

1. [ECCDM published 1.0.0-ballot: scope and publication status](https://hl7.eu/fhir/cancer-common/1.0.0-ballot/)
   and [published artifact inventory](https://hl7.eu/fhir/cancer-common/1.0.0-ballot/artifacts.html).
2. ECCDM logical models:
   [CancerConditionAtDiagnosis](https://hl7.eu/fhir/cancer-common/1.0.0-ballot/StructureDefinition-CancerConditionAtDiagnosis.html),
   [CancerStage](https://hl7.eu/fhir/cancer-common/1.0.0-ballot/StructureDefinition-CancerStage.html),
   [ClinicalCancerProgression](https://hl7.eu/fhir/cancer-common/1.0.0-ballot/StructureDefinition-ClinicalCancerProgression.html).
   Corresponding published StructureDefinition JSON also checked for field names/cardinalities.
3. [ECCDM CI build and its non-authorized-publication warning](https://build.fhir.org/ig/hl7-eu/cancer-common/).
4. [mCODE STU4 4.0.0 overview](https://hl7.org/fhir/us/mcode/STU4/),
   [profile conformance and US Core dependency](https://hl7.org/fhir/us/mcode/STU4/conformance-profiles.html),
   [in-scope patients/system behavior](https://hl7.org/fhir/us/mcode/STU4/conformance-patients.html).
5. mCODE [Primary Cancer Condition](https://hl7.org/fhir/us/mcode/STU4/StructureDefinition-mcode-primary-cancer-condition.html),
   [TNM Stage Group](https://hl7.org/fhir/us/mcode/STU4/StructureDefinition-mcode-tnm-stage-group.html),
   [ECOG Performance Status](https://hl7.org/fhir/us/mcode/STU4/StructureDefinition-mcode-ecog-performance-status.html),
   [Cancer Patient](https://hl7.org/fhir/us/mcode/STU4/StructureDefinition-mcode-cancer-patient.html).
   Published profile JSON also checked for dependencies, bindings and value types.
6. FHIR R4 [Documents](https://hl7.org/fhir/R4/documents.html),
   [CarePlan](https://hl7.org/fhir/R4/careplan.html), [Task](https://hl7.org/fhir/R4/task.html),
   [Provenance](https://hl7.org/fhir/R4/provenance.html). Published CarePlan/Task definitions also
   checked for action references and requested versus actual execution periods.

**Open deployment decisions, not blockers to this plan:** receiving NIS contract; institutional
identity/role authority and signature requirements; licensed terminology services; source-version
availability; intended treatment/order scope; and the clinical governance owner for local profiles.
