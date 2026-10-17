# MDT workflow: the simple journey

**Audience:** the team and their coding agents. Agreed target for the frontend (decision #18,
replacing the role-based plan of #16). One linear journey for the coordinator, bare essentials only:
no descriptions, no extra buttons, one **Další** per screen.

| # | Screen | What's on it |
|---|--------|--------------|
| 1 | Nahrání | Two rectangles with "nebo" between: FHIR (pick or drop a file → uploads at once) and PDF (greyed out, "Připravujeme") |
| 2 | Komise | Specialty bubbles; a tap adds it (green outline). At least 3 |
| 3 | Pacient | Patient and board, the MDT question in a highlighted card (red when missing), diagnoses + ECOG, course of the disease |
| 4 | Klíčové informace | Critical (high) and important (medium) red flags unrolled; the rest in collapsible groups (minor warnings, missing data, each specialty's facts) |
| 5 | Vývoj | Two charts per screen, no scrolling; Další pages through further series |
| 6 | Léčebný záměr | Square tiles: kurativní / paliativní / podpůrná péče / sledování / odloženo |
| 7 | Závěr | Zvolený postup, Zdůvodnění |
| 8 | Potvrzení | Chosen vs recommended postup side by side; soulad s doporučenými postupy is automatic (léčebný záměr chosen = recommended); on a difference, Potvrdit opens a required Důvod odchylky field ("Potvrdit s odchylkou"); a name field appears when none is set. Stanoviska per role open in a pop-up (that role's facts + opinion). Potvrdit leads on to Export |
| 9 | Export | Two rectangles: PDF (downloads the official record, rendered by the backend: question, board, záměr, postup, zdůvodnění, soulad, who confirmed) or FHIR (greyed out, "Připravujeme") |

Plus **Přehled** (`#/`): case cards with a coloured status (Potvrzeno / Rozpracováno / Nový); a
confirmed case opens Export.

Rules that still hold: every statement opens its source; AI output is blue; examples that aren't
real AI output yet (recommended postup, stanoviska) carry a visible "ukázka" label; Potvrdit records
who confirmed and when, and means the board agreed (consensus).

Known gaps (mandatory items in `problem_statement.md` left out for simplicity): section order and
detail level, trial screening, AI questions for discussion. The backend keeps the board, finding
triage, visibility and history data for a later access-control / admin view.
