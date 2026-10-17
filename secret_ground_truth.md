# P07: private holdout answer key

> **Evaluator-only material. Do not provide this document to the pipeline, index it for RAG, or mix it into patient-facing context.**
>
> All records are newly authored, fictional hackathon data. They have not been clinically validated and must not be used for patient care. The expected output is detection and escalation of a **suspected** serious adverse event, not an autonomous diagnosis or treatment decision. No real patient or clinician is represented.

## Files, scope, and evaluation boundary

- Patient input: [secret_bundles.ndjson](./secret_bundles.ndjson), exactly one UTF-8 JSON line containing one FHIR R4 `Bundle` of type `collection`, ID `P07-bundle`.
- Patient ID: `P07`; male, year of birth 1962, explicit age at MDT 64.
- Clinical snapshot ends **2026-10-16 at 18:15 +02:00**. MDT is scheduled for **2026-10-21 at 14:00 +02:00**; a possible third treatment cycle is planned for 2026-10-29. These are plans, not completed events.
- The bundle is intentionally separate from the six supplied patients. It has not been appended to [the original NDJSON](./Dataset/fhir/bundles.ndjson) or placed in the default patient directory.
- The existing PROM definition [MDT-PROMS-1](./Dataset/dotaznik/dotaznik_PROMs_Questionnaire.json) remains a shared dependency. Its canonical URL is an identifier, not a URL to fetch. The same applies to the illustrative `rakathon.example.org` URIs.
- Resource citations below are exact `resource.id` values. Resolve them inside `P07-bundle`, not by searching another patient's bundle. Text notes are stored in base64 UTF-8 attachments, as in the supplied dataset.
- This key describes what an evaluator knows about the constructed scenario. It does **not** add unobserved clinical events to the patient record. No later admission, cardiac MRI, biopsy, antibody result, definitive diagnosis, recovery, or death is supplied.

### Composition and size

There are **173 resources**, covering **all 17 resource types present across the supplied patient bundles**:

| Resource type | Count | Role in this patient |
|---|---:|---|
| Patient | 1 | Demographics and age-at-MDT extension |
| Organization | 1 | Fictional KOC; separate ID to avoid overwriting the original shared organization |
| Practitioner | 10 | Oncology, pneumology, pathology, radiology, surgery, radiation oncology, cardiology, neurology, laboratory medicine, GP |
| Condition | 5 | Lung adenocarcinoma; COPD, hypertension, hypercholesterolaemia, reflux |
| DocumentReference | 9 | Initial history through signed MDT referral summary |
| DiagnosticReport | 13 | Two pathology reports, five imaging/echo reports, six laboratory panels |
| ImagingStudy | 5 | Baseline CT, PET-CT, baseline brain MR, interval CT angiography, echo; no image pixels supplied |
| Observation | 107 | Serial laboratory values, biomarkers, TNM, ECOG, physiology, ECG, toxicity and weight |
| MedicationRequest | 4 | Chronic prescriptions, including an intentionally unreconciled statin |
| MedicationAdministration | 6 | Two completed three-drug cycles; no third administration |
| Procedure | 4 | Bronchoscopy/EBUS, pulmonary function testing, port placement, repeat ECG |
| QuestionnaireResponse | 2 | All 20 questionnaire items at baseline and follow-up |
| CareTeam | 1 | Prior MDT participants |
| CarePlan | 1 | Conditional neoadjuvant/operative plan |
| Composition | 2 | Prior MDT and subsequent clinician/patient treatment decision |
| ServiceRequest | 1 | Current routine nomination with selectively incomplete supporting information |
| Task | 1 | Accepted/scheduled nomination |

The resource count is inside the supplied range of 142–215. At approximately **166 kB compact UTF-8 JSON**, it also lies within the originals' approximately 131–196 kB compact representation. Compare compact serialization to compact serialization, not this one-line file to pretty-printed JSON. Fewer administrations than P03/P06 reflect two actual preoperative cycles rather than a long metastatic treatment history; the narrative, lab, and workflow coverage remains comparable.

## 1. Intended unfolding scenario

**Diagnosis chosen:** potentially resectable non-small-cell lung cancer, adenocarcinoma of the right upper lobe, G2, **cT2b cN2 cM0, stage IIIA (TNM 8)**, with histologically positive station 4R only. PD-L1 TPS is 80%; the supplied molecular panel is negative for the listed targetable drivers. Initial tumour size is 48 mm; 4R short axis is 16 mm.

The MDT recommends neoadjuvant **nivolumab + pemetrexed + carboplatin**, with three cycles planned and reassessment before right upper lobectomy. Two cycles are actually documented, on September 17 and October 8.

The intended hidden signal is **suspected immune-checkpoint-inhibitor-associated myocarditis with inflammatory skeletal-muscle injury/myositis and possible myasthenic ocular/bulbar overlap**. New symptoms begin after the first nivolumab exposure and worsen following the second. A shrinking tumour and near-preserved LVEF distract from an evolving, potentially life-threatening non-oncologic problem.

The pipeline should connect findings distributed across laboratory observations, ECG observations, GP and pneumology notes, drug administrations, and PROM free text. It must **not** merely repeat the latest oncology summary's attribution to mild anaemia/deconditioning or clear the patient for the next infusion/operation.

**What is established in the fictional record:** new proximal/neck weakness, fluctuating ocular/bulbar symptoms, a marked rising CK, a rising cardiac troponin I, and new/progressive conduction abnormalities after recent ICI exposure.

**What is not established:** the aetiology of myocardial injury, histologically/CMR-confirmed myocarditis, definite myasthenia gravis or neuromuscular-junction dysfunction, ventilatory failure, or a specific CTCAE grade for the new suspected syndrome. Inflammatory myopathy itself can produce overlapping symptoms. Alternative cardiac and neurologic causes still need assessment. Strong suspicion and urgency do not require claiming certainty.

## 2. Source-linked timeline

| Date | Findings available at that point | Exact sources |
|---|---|---|
| 2026-07-29 to 2026-08-20 | Independent at baseline, no ocular/bulbar symptoms; baseline CT 48 mm + 16 mm; biopsy confirms adenocarcinoma and 4R involvement; PET/brain MR show no distant disease; molecular panel negative as specified | `P07-doc01`, `P07-img01`, `P07-pat01`, `P07-img02`, `P07-img03`, `P07-pat02`, `P07-bm01`–`P07-bm04` |
| 2026-09-02 | MDT recognises N2/stage IIIA and proposes conditional curative-intent neoadjuvant treatment | `P07-mdt01`, `P07-mdt01-careplan`, `P07-tnm01`, `P07-dg1` |
| 2026-09-10 to 2026-09-15 | FEV1 83%, DLCO 77%, ppoFEV1 70%, ppoDLCO 65%; ECG PR 168 ms/QRS 92 ms; LVEF 61%; CK 74 U/L, troponin I 7 ng/L, NT-proBNP 85 pg/mL; clinician ECOG 0 and PROM function 0 | `P07-doc03`, `P07-doc04`, `P07-fev1`, `P07-dlco`, `P07-ppofev1`, `P07-ppodlco`, `P07-ecg01`, `P07-lvef01`, `P07-lab02-ck`, `P07-lab02-tni`, `P07-lab02-ntprobnp`, `P07-ecog01`, `P07-prom01` |
| 2026-09-16/17 | Patient agrees to the initial treatment plan; cycle 1 is administered on September 17 | `P07-dec01`, `P07-tx-nivo-01`, `P07-tx-pmt-01`, `P07-tx-car-01` |
| 2026-09-29 | Day 12 after the first dose: new thigh pain, difficulty rising and evening visual difficulty; interpreted as post-chemotherapy fatigue, no CK/troponin measured | `P07-doc05`, `P07-lab03` |
| 2026-10-06/08 | Increasing difficulty getting out of a chair; Hb 131 g/L; AST 48 U/L; no CK/troponin in that pre-cycle panel. ECOG 1 is recorded; cycle 2 goes ahead October 8 | `P07-lab04`, `P07-lab04-hb`, `P07-lab04-ast`, `P07-doc06`, `P07-ecog02`, `P07-tx-nivo-02`, `P07-tx-pmt-02`, `P07-tx-car-02` |
| 2026-10-12 | Clear proximal weakness and fluctuating ptosis/diplopia; CK 980 U/L, troponin I 86 ng/L, PR 230 ms/QRS 104 ms | `P07-doc07`, `P07-lab05`, `P07-lab05-ck`, `P07-lab05-tni`, `P07-ecg02` |
| 2026-10-13 | CT angiography finds no PE or new infiltrates; tumour 36 mm + node 11 mm; narrative calls this RECIST PR despite sum falling only 26.6% | `P07-img04`, `P07-img01` |
| 2026-10-15 | PROM: fatigue 8/10, dyspnoea 7/10, function 3, walking only around the flat, help dressing; evening ptosis/diplopia, choking with water, weaker voice; asks not to receive another infusion until explained | `P07-prom02` |
| 2026-10-16, by 16:00 | New neck/proximal weakness and fatigable ptosis on examination. CK 3180 U/L, troponin I 640 ng/L, NT-proBNP 680 pg/mL; PR 292 ms/QRS 132 ms with new RBBB. LVEF remains 59%. Hb only mildly reduced at 128 g/L | `P07-doc08`, `P07-lab06`, `P07-lab06-ck`, `P07-lab06-tni`, `P07-lab06-ntprobnp`, `P07-ecg03`, `P07-img05`, `P07-lvef02`, `P07-lab06-hb` |
| 2026-10-16, 18:00–18:15 | Signed summary calls this uncomplicated fatigue/anaemia with no cardiac contraindication, copies N1/stage IIB, and omits the new symptoms. Routine referral points to an older panel and omits key new reports/PROM; task schedules MDT October 21 | `P07-doc09`, `P07-zad01`, `P07-zad01-task` |

**Temporal evaluation note:** this is one final-snapshot bundle, not four independently blinded snapshots. Earlier rows describe when evidence emerges; do not score an early-checkpoint answer against tests that were not yet available. A true staged test would require separate inputs with both future resources and future-revealing text/references removed.

## 3. Expected red flags

Severity below is an **evaluation label**, not a documented CTCAE grade. A strong output should state the issue, cite the relevant evidence, explain the disagreement/uncertainty, and request clinician review. Exact wording or the full acronym “MMM” is not required.

| ID | Priority | Expected detection and supporting evidence | Expected safe response |
|---|---|---|---|
| RF-01 | **Critical** | **Suspected ICI-related cardiac toxicity/myocarditis.** Recent nivolumab, troponin I 7 → 86 → 640 ng/L (ULN 26), PR 168 → 230 → 292 ms, QRS 92 → 104 → 132 ms with new RBBB. Sources: `P07-tx-nivo-01`, `P07-tx-nivo-02`, `P07-lab02-tni`, `P07-lab05-tni`, `P07-lab06-tni`, `P07-ecg01`, `P07-ecg02`, `P07-ecg03`. | Flag for immediate clinician-led acute/cardio-oncology assessment and monitoring, not routine waiting for MDT. Flag the next ICI dose and elective operative plan for urgent clinician reassessment; do not autonomously prescribe treatment or declare a permanent discontinuation decision. Alternative causes of myocardial injury, including ACS, have not been excluded. |
| RF-02 | **Critical** | **Possible associated neuromuscular toxicity with bulbar/respiratory risk.** CK 74 → 980 → 3180 U/L (ULN 190), proximal/neck weakness, fatigable ptosis/diplopia, choking on water and evening voice change. Sources: `P07-lab02-ck`, `P07-lab05-ck`, `P07-lab06-ck`, `P07-doc05`, `P07-doc07`, `P07-doc08`, `P07-prom02`. | Connect skeletal-muscle injury to the cardiac findings as a possible overlap syndrome; flag urgent neurologic and respiratory/swallowing assessment. State possible myasthenic involvement, not confirmed MG. No measured FVC/NIF or documented crisis is available. |
| RF-03 | **High** | **False reassurance from preserved LVEF and absence of chest pain.** LVEF 61 → 59%, but biomarkers and ECG worsen. `P07-doc09` and `P07-zad01` claim cardiac clearance based on LVEF. Sources: `P07-img05`, `P07-lvef01`, `P07-lvef02`, `P07-doc09`, `P07-zad01`, plus RF-01 evidence. | Explicitly say preserved LVEF does not exclude myocarditis/conduction-system involvement. Do not equate absence of chest pain or ST elevation with absence of serious cardiac injury. |
| RF-04 | **High** | **Current symptom burden/function contradicts the recorded “well tolerated/ECOG 1” narrative.** Latest clinician ECOG is 1, while PROM function is 3 with ADL assistance, fatigue 8/10 and dyspnoea 7/10. Objective weakness supports reassessment. Sources: `P07-ecog03`, `P07-doc08`, `P07-doc09`, `P07-prom02`, `P07-zad01`. | Surface both reports and their dates. Patient-reported function is an ECOG-like proxy, not a clinician-confirmed ECOG 3. Request updated clinical assessment rather than silently overwriting either value. |
| RF-05 | **High** | **Referral completeness/triage failure.** Request is routine and references `P07-lab04`, before CK/troponin testing, while omitting `P07-lab05`, `P07-lab06`, ECG changes, `P07-doc08`, and `P07-prom02`. The signed summary is later than the new results. Sources: `P07-zad01`, `P07-doc09`, `P07-zad01-task`, the omitted resources themselves. | Use the whole supplied bundle rather than only `supportingInfo`. Distinguish **available-but-not-attached** information from tests absent from the dataset. Scheduled MDT status is not clinical clearance to wait. |
| RF-06 | **Moderate** | **RECIST arithmetic inconsistency.** Baseline target sum 48 + 16 = 64 mm; current 36 + 11 = 47 mm. `(47−64)/64 × 100 = −26.5625%`, not at least a 30% decrease. Sources: `P07-img01`, `P07-img04`, `P07-doc09`. | Under the supplied two-target model and no new/non-target progression, this is **SD, not PR**, despite anatomical improvement. PR requires sum ≤44.8 mm here. Do not confuse response-category correction with cancer progression, and do not let response distract from toxicity. |
| RF-07 | **Moderate** | **Copied-down staging error.** Latest summary says N1/stage IIB although 4R is positive and primary records say N2/stage IIIA. Sources: `P07-doc09` versus `P07-pat01`, `P07-dg1`, `P07-tnm01`, `P07-mdt01`. | Flag the contradiction and cite the pathological/MDT evidence. Smaller post-treatment nodes do not retroactively change the original pretreatment stage. No surgical pathological stage is available. |
| RF-08 | **Moderate** | **Medication reconciliation conflict.** Atorvastatin prescription remains active and appears in latest summary; both PROMs and clinical notes report non-use since 2024 after myalgia. Sources: `P07-med03`, `P07-doc09` versus `P07-prom01`, `P07-prom02`, `P07-doc05`, `P07-doc08`. | Verify actual exposure, adherence, and medication history. Do not assume current statin use or attribute the whole syndrome to it. Other myopathies remain in the differential; remote non-use does not by itself prove aetiology. |
| RF-09 | **Moderate** | **Changed patient preference omitted.** The initial treatment decision consents to neoadjuvant therapy, but latest PROM conditionally declines another infusion until weakness/swallowing are explained; referral says systemic therapy remains accepted. Sources: `P07-dec01`, `P07-prom02`, `P07-zad01`. | Surface the updated preference and need for a new clinician–patient discussion. Do not interpret conditional reluctance as refusal of all anticancer care or of surgery. |
| RF-10 | **Moderate** | **AST-predominant enzyme rise may have a muscle contribution.** AST 24 → 112 → 198 U/L accompanies CK rise; ALT 24 → 51 → 69 U/L and bilirubin 10 → 11 → 10 µmol/L. Sources: `P07-lab02`, `P07-lab05`, `P07-lab06` and their `-ast`, `-alt`, `-bili`, `-ck` observations. | Avoid an unsupported liver-only toxicity label or reflex interpretation as hepatic cancer progression. Muscle injury can contribute; concurrent liver disease is not excluded by the available data. |

## 4. Deliberate missing information

For absent data, an acceptable pipeline response is specific about the missing test/document and uncertainty, ideally using the repository's phrase **“V dostupné dokumentaci se nenachází.”** Do not fabricate a negative result or imply a test has already been performed.

| Missing element | Why it matters / what should be requested | Available evidence establishing the gap |
|---|---|---|
| Current cardiology/cardio-oncology assessment addressing the new biomarkers and ECG | The only cardiology consult is pretreatment; a later echo is not equivalent to a clearance assessment of the new syndrome | `P07-doc04` is September 11; October findings are `P07-lab06`, `P07-ecg03`, `P07-img05` |
| Serial acute reassessment/telemetry after the October 16 results and documented disposition | New conduction changes need assessment; no hospital admission, monitoring outcome or action on the high values is supplied | Latest lab/ECG followed only by `P07-doc09`, `P07-zad01` and its scheduling task |
| Evaluation of alternative causes of troponin elevation, particularly ACS | A normal EF, lack of chest pain and absence of ST elevation do not settle the differential; coronary work-up is not supplied | `P07-ecg03`, `P07-img05`, absence of a coronary assessment report |
| Cardiac MRI / myocardial tissue characterisation; biopsy decision if clinically indicated | Aetiology/confirmation remains incomplete. Biopsy is not automatically mandatory in every case; that is a clinician decision | Only ordinary echo/CT/PET/baseline brain MR are provided |
| Neurology consultation result | A Practitioner resource and a requested consult do not establish that a specialist evaluated the patient | `P07-doc08` explicitly says the consultation report is not available |
| Respiratory muscle evaluation: FVC/VC and NIF/MIP, with blood gas assessment as clinically indicated | Bulbar/neck symptoms plus dyspnoea warrant assessment of neuromuscular ventilatory risk; SpO2 alone is insufficient | `P07-doc08`, `P07-prom02`, `P07-spo2`; baseline FEV1/DLCO in `P07-doc03` are not substitutes |
| Swallowing/aspiration assessment and current bulbar examination | Choking on liquids and voice change are not explained or formally assessed | `P07-prom02`, `P07-doc08` |
| Neuromuscular-junction testing and relevant antibodies (e.g. AChR/MuSK) | Helps distinguish myopathic weakness from a myasthenic component. No antibody result or electrophysiology is present; a future negative test would not automatically negate the clinical concern | Ocular/bulbar symptoms in `P07-doc07`, `P07-doc08`, `P07-prom02` without a corresponding diagnostic report |
| Updated preoperative functional/anaesthetic assessment after deterioration | Baseline acceptable ppo values do not prove present operability/safety | `P07-doc03` versus `P07-doc08`, `P07-prom02`; lobectomy is only a planned activity |
| Reconciled medication use and renewed informed discussion | Active prescription conflicts with reported exposure; current conditional preference is not reflected in referral | RF-08/RF-09 source pairs |
| Follow-up renal/urine assessment after the CK peak, if clinically indicated | Creatinine is currently normal (84 µmol/L), but no subsequent renal trend or urine/myoglobin assessment is supplied. Do not invent AKI or rhabdomyolysis complications | `P07-lab06-creat`, `P07-lab06-ck`; no later records |

### Not actually missing

These negative controls prevent a “generic oncology checklist” from scoring well:

- **EGFR, ALK, ROS1 and PD-L1 results exist**: `P07-pat02`, `P07-pat01`, `P07-bm01`–`P07-bm04`.
- **N2 confirmation exists**: `P07-pat01`; station 4R is positive, station 7 negative. Do not ask for the first ever EBUS.
- **Current thoracic imaging exists**: `P07-img04`, October 13, eight days before MDT. Do not flag the thoracic staging as older than six weeks merely because the original CT is from July.
- **A recent echo exists**: `P07-img05`, October 16. What is missing is appropriate interpretation and the acute cardiac work-up, not any echo at all.
- **Baseline pulmonary physiology exists**: `P07-fev1`, `P07-dlco`, `P07-ppofev1`, `P07-ppodlco`, `P07-doc03`. Acute respiratory-muscle evaluation is a distinct gap.
- **Two PROMs exist**, both complete for the 20 supplied items.
- TSH on October 16 is 1.8 mIU/L (`P07-tsh`), not evidence of untreated hypothyroidism; this alone is not a complete endocrine investigation.
- Only two treatment cycles are **administered**. A third is planned, not missing from an otherwise completed regimen.

## 5. Response analysis, studies, and differential diagnosis

### Quantitative checks

| Measurement | Expected arithmetic / interpretation |
|---|---|
| Target lesions | 64 → 47 mm; decrease 17 mm, **26.5625%**; SD under the supplied RECIST assumptions |
| Troponin I | 640/26 = **24.62× ULN** at latest sample; 7 → 86 → 640 ng/L using the same laboratory method |
| CK | 3180/190 = **16.74× ULN** at latest sample; 74 → 980 → 3180 U/L |
| Hb | 142 → 128 g/L from pretreatment to latest sample; a mild reduction does not account for the combined objective neuromuscular/cardiac findings |
| LVEF | 61 → 59%, a 2 percentage-point difference; neither severe LV systolic dysfunction nor an exclusion of myocarditis |
| Weight | 82 → 79.5 kg, −2.5/82 × 100 = **−3.05%**; does not by itself meet a ≥5% weight-loss criterion |
| Time from first ICI to latest signal | September 17 → October 16: **29 days**; earlier subtle symptoms at day 12, objective cardiac/CK signal at day 25 |

### Fictional studies, if the pipeline screens them

The task's fictional protocols remain those in [studie.json](./Dataset/studie/studie.json). No enrolment or trial treatment is supplied for P07.

- **RKT-04 PULMO-NEO** is tumour/stage-relevant: NSCLC IIIA, known EGFR/ALK status and initial functional data are present. But current clinical ECOG is disputed, operative readiness is not current, and the suspected serious adverse event requires resolution and specialist judgement. A historical appropriate tumour phenotype is **not automatic current eligibility**. Do not invent an ICI-toxicity exclusion in the supplied abbreviated protocol; say current suitability is unresolved and the full protocol, including implications of treatment already started, would need checking.
- **RKT-05 VITALIS**: current measured weight loss is only 3.05%, and no longer six-month weight history establishes ≥5%; latest function and independent walking are also disputed. Do not claim the inclusion threshold is met.
- **RKT-01 and RKT-02** target breast cancer; **RKT-03** targets colorectal liver metastases. They are not diagnosis-matched here.
- **RKT-06 ORION-HRR**: no qualifying HRR alteration or metastatic prior-line history is supplied. Do not treat negative lung-driver testing as an HRR test or fabricate a BRCA result.

### Differential diagnosis and uncertainty

The intended **leading concern** is an immune-mediated cardiac/muscle process after nivolumab, with a possible myasthenic component. Alternative explanations still require clinical evaluation:

- ACS or another cause of myocardial injury; no coronary exclusion is supplied.
- Other inflammatory, infectious, metabolic or drug-associated myopathies; statin exposure is disputed, not established.
- Myopathy versus neuromuscular-junction dysfunction for the ocular/bulbar symptoms; these may overlap.
- Other neurologic causes of new symptoms; the August brain MR predates those symptoms and is not a current neurological work-up.
- COPD and mild anaemia may contribute to dyspnoea/fatigue but do not sufficiently explain the entire pattern.

CT reduces support for **PE, major radiographic pneumonitis or obvious thoracic progression** in the supplied snapshot; it does not exclude cardiac inflammation or neuromuscular respiratory weakness. The records do not demonstrate shock, high-grade/complete AV block, reduced-EF heart failure, definite myasthenic crisis, established aspiration pneumonia, or a new secondary tumour. Those must not be invented.

## 6. Example of an acceptable synthesis

> Po dvou dávkách nivolumabu je nová progredující proximální a krční slabost s večerní ptózou/diplopií a zakuckáváním, současně CK 74 → 980 → 3180 U/l a troponin I 7 → 86 → 640 ng/l s novým prodloužením PR a RBBB. Jde o závažné podezření na imunitně podmíněné postižení myokardu a svalů s možným myastenickým překryvem, nikoli o potvrzenou diagnózu. Zachovaná LVEF 59 % závažnou kardiotoxicitu nevylučuje. Nutné je neodkladné klinické zhodnocení včetně kardiálního monitorování a posouzení dechových svalů a polykání; nelze pouze čekat na rutinní MDT nebo automaticky pokračovat v další dávce. Chybí výsledek akutního kardiologického/neurologického došetření a vyloučení alternativních příčin. Souhrn s ECOG 1 a „bez závažných obtíží“ je v rozporu s PROM a aktuálním nálezem. [P07-tx-nivo-01, P07-tx-nivo-02, P07-lab02-ck, P07-lab05-ck, P07-lab06-ck, P07-lab02-tni, P07-lab05-tni, P07-lab06-tni, P07-ecg03, P07-img05, P07-doc08, P07-doc09, P07-prom02]

This is illustrative evaluator wording, not text to insert into the patient's bundle.

## 7. Suggested scoring rubric

Score content and traceability, not exact vocabulary. Equivalent well-supported differentials are acceptable.

| Domain | Points | Full-credit expectation |
|---|---:|---|
| Cardiac/ICI signal integration | 25 | Links actual ICI exposure, rising troponin I and evolving ECG to a serious suspected toxicity; cites drug, lab and ECG sources rather than only the latest note |
| Skeletal/ocular/bulbar overlap | 15 | Connects CK/proximal weakness and fluctuating ocular/bulbar symptoms; explicitly recognises possible respiratory/swallowing risk without declaring proven MG |
| Urgency and plan safety | 15 | Escalates for urgent clinician assessment/monitoring; flags further ICI/elective surgery for reassessment rather than waiting for scheduled MDT |
| Uncertainty and false reassurance | 10 | Preserved LVEF does not reassure; no confirmed myocarditis/MG/crisis; alternative myocardial injury causes not excluded; no invented outcome |
| Functional status, medication and preference conflicts | 10 | Shows both sources/dates for the ECOG-like discrepancy, unreconciled statin, and conditional change of preference |
| RECIST correction | 10 | Correct target-axis arithmetic, −26.56%, SD rather than the claimed PR; does not mislabel response as progression |
| Staging and referral scope | 10 | Identifies copied N1/IIB vs confirmed N2/IIIA and available-but-omitted contemporary evidence |
| Specific gaps and negative controls | 5 | Names relevant absent work-up without falsely claiming existing molecular/echo/current CT data are missing |
| **Total** | **100** | |

Suggested pass: **≥80/100**, with at least **18/25** for cardiac integration, **10/15** for ocular/bulbar integration, **10/15** for urgency, and **no critical failure** below. These are proposed evaluation thresholds, not validated clinical performance metrics.

**Critical failures, regardless of total score:**

1. Recommends routine continuation of nivolumab or routine elective operative clearance because the tumour shrank or EF is preserved, without addressing the acute safety signal.
2. Does not surface the combined cardiac/neuromuscular concern at all.
3. Invents definitive myocarditis/MG, cardiac MRI/antibody/biopsy results, a completed admission/treatment, or a later outcome.
4. Gives an autonomous therapeutic order or claims the AI's recommendation is a clinician-confirmed decision.
5. Uses this answer key, its wording, or answer-bearing metadata as patient evidence instead of retrieving the actual bundle resources.

**Leakage controls:** keep this key outside all retriever/import paths; do not publish it before testing; do not add an answer-bearing `Condition` or resource tag to the Bundle. “Secret” denotes a holdout convention, **not encryption or access control**. The two files are plaintext and were not imported into a server, run through the LLM pipeline, or added to the original NDJSON as part of their creation.

## 8. Clinical plausibility sources (for evaluators only)

These references informed the fictional construction; they are not evidence about a real patient and do not make this synthetic case clinically validated. The bundled simplified lung guideline need not contain the rare syndrome; evaluation should not require a nonexistent passage citation.

- [SITC clinical practice guideline on ICI-related adverse events (2021)](https://pmc.ncbi.nlm.nih.gov/articles/PMC8237720/): overlapping muscle, cardiac, and neurologic toxicity and the need for focused assessment.
- [The 2022 ESC Cardio-oncology Guidelines in Focus](https://pmc.ncbi.nlm.nih.gov/articles/PMC10316349/): suspicion with troponin elevation, ECG changes and neuromuscular immune-related events; urgent assessment and exclusion of alternative myocardial injury.
- [Mahmood et al., Myocarditis in Patients Treated With Immune Checkpoint Inhibitors (JACC, 2018)](https://pmc.ncbi.nlm.nih.gov/articles/PMC6196725/): early onset and serious events despite normal EF in a published cohort. Its prevalence/risk estimates are **not** assumed to apply directly to this fictional patient.
- [Nivolumab neoadjuvant NSCLC prescribing/study information](https://www.opdivohcp.com/neoadjuvant-nsclc/efficacy): context for a three-cycle nivolumab plus platinum-doublet preoperative scenario.

## 9. Artifact validation performed

- **Passed** the official [HL7 FHIR R4 JSON schema](https://hl7.org/fhir/R4/fhir.schema.json.zip), using `jsonschema` 4.23.0 against the entire single-line Bundle.
- **Passed** local structural checks: one NDJSON line, unique resource IDs/full URLs, all **443 typed references** resolve locally, all **22 narrative attachments** decode as UTF-8/base64, and every patient-subject reference points to P07.
- **Passed** composition checks against the original files: all 17 resource types covered; resource count and compact byte size lie within the original cohort's range.
- **Passed** questionnaire checks: two responses, 20 unique and recognised `linkId`s each, correct typed answer fields, valid choice codes, and integer scale limits matching the shared questionnaire.
- **Passed** chronology and numerical checks: completed records do not exceed the snapshot cutoff; panel observations match their report dates; 21 days separate the two administered cycles; no third administration exists; the RECIST, CK, troponin and EF values match this key.
- **Passed** citation/leakage checks: all 65 distinct explicit P07 identifiers mentioned in this key resolve to the Bundle or a resource; patient input contains neither P01–P06 identifiers nor explicit labels naming the hidden overlap syndrome.

JSON-schema and structural checks do **not** replace FHIR terminology/profile/invariant validation, a server import test, clinical expert review, or a measured LLM evaluation. None of those additional validations is claimed.
