# MDT workflow: the simple journey

**Audience:** the team and their coding agents. Agreed target for the frontend (decision #18,
replacing the role-based plan of #16). One linear journey for the coordinator, bare essentials only:
no descriptions, no extra buttons, one **Další** per screen.

| # | Screen | What's on it |
|---|--------|--------------|
| 1 | Nahrání | Two bubbles: FHIR (pick or drop a file → uploads at once) and PDF (greyed out, "Připravujeme") |
| 2 | Komise | Specialty bubbles; a tap adds it (green outline). At least 3 |
| 3 | Pacient | Patient, diagnosis and the MDT question in big letters; a missing question shows in red |
| 4 | Klíčové informace | 3–4 statements: the most urgent red flags first, then key facts (ECOG doctor vs patient) |
| 5 | Vývoj | 2–3 trend charts |
| 6 | Léčebný záměr | Bubbles: kurativní / paliativní / podpůrná péče / sledování / odloženo |
| 7 | Závěr | Zvolený postup, Zdůvodnění |
| 8 | Potvrzení | Chosen vs recommended postup side by side; soulad s doporučenými postupy is automatic (léčebný záměr chosen = recommended); on a difference, Potvrdit first asks for Důvod odchylky. Stanoviska per role (bubble → that role's facts + opinion). After Potvrdit: Stáhnout PDF |

Plus **Přehled** (`#/`): the cases and whether their conclusion is confirmed; a confirmed case opens
its record.

Rules that still hold: every statement opens its source; AI output is blue; examples that aren't
real AI output yet (recommended postup, stanoviska) carry a visible "ukázka" label; Potvrdit records
who confirmed and when, and means the board agreed (consensus).

Known gaps (mandatory items in `problem_statement.md` left out for simplicity): section order and
detail level, trial screening, AI questions for discussion. The backend keeps the board, finding
triage, visibility and history data for a later access-control / admin view.
