# MDT workflow: the simple journey

**Audience:** the team and their coding agents. Agreed target for the frontend (decision #20,
replacing the role-based plan of #16). One linear journey for the coordinator, bare essentials only:
no descriptions, no extra buttons, one **Další** per screen.

| # | Screen | What's on it |
|---|--------|--------------|
| 1 | Nahrání | Two rectangles with "nebo" between: FHIR (pick or drop a file → uploads at once) and PDF (greyed out, "Připravujeme") |
| 2 | Komise | Specialty bubbles; a tap adds it (green outline). At least 3 |
| 3 | Pacient | Patient and board, up to 2 critical findings (else the 2 most important) as red/amber cards, the MDT question in a highlighted card (red when missing), the patient's wishes right under it (AI, when the agent briefed the case; 2 shown), diagnoses (4 facts shown) + ECOG, course of the disease (4 latest events); the rest of each one click away |
| 4 | Klíčové informace | Critical (high) and important (medium) red flags unrolled as red / amber cards; the rest in collapsible groups (minor warnings, missing data, each specialty's facts) |
| 5 | Vývoj | Two charts per screen, no scrolling; Další pages through further series |
| 6 | Otázky k diskusi | The agent's 2–3 questions for the board, numbered, each with its source (AI); "not available" until the agent has briefed the case |
| 7 | Léčebný záměr | Square tiles: kurativní / paliativní / podpůrná péče / sledování / odloženo |
| 8 | Závěr | Zvolený postup, Zdůvodnění; stanovisko bubbles per specialty: green = supports, red = doesn't (click → stanovisko, stance switchable) |
| 9 | Potvrzení | Chosen vs recommended postup side by side; soulad s doporučenými postupy is automatic (léčebný záměr chosen = recommended); on a difference, Potvrdit opens a required Důvod odchylky field ("Potvrdit s odchylkou"); a name field appears when none is set. Stanovisko bubbles as on Závěr; anyone against blocks Potvrdit (no consensus). Potvrdit leads on to Export |
| 10 | Export | Two rectangles: PDF (downloads the official record, rendered by the backend: question, board, záměr, postup, zdůvodnění, soulad, who confirmed) or FHIR (greyed out, "Připravujeme") |

Plus **Přehled** (`#/`): case cards with a coloured status (Potvrzeno / Rozpracováno / Nový); a
confirmed case opens Export. While the agent briefs a patient (`mdt-agent`, a batch step), its card
says "AI připravuje…" and every screen of the case shows a blue banner; both check every 10 s and
the case reloads itself when the briefing is ready.

Narrow screens (≤ 640 px): one-line progress ("3 / 10 · Pacient"), compact top bar and type, the
disease course only as a collapsible list, so no screen scrolls.

Rules that still hold: every statement opens its source; AI output is blue; examples standing in
where there's no AI output (recommended postup and stanoviska of cases the agent hasn't briefed, the
pathology stanovisko) carry a visible "ukázka" label; Potvrdit records
who confirmed and when, and means the board agreed (consensus).

Known gaps (mandatory items in `problem_statement.md` left out for simplicity): section order and
detail level, trial screening. The backend keeps the board, finding
triage, visibility and history data for a later access-control / admin view. Against
`MDT_ZASEDANI_PROCES.md`: no per-member sign-off; the stanovisko bubbles stand in (anyone against
blocks Potvrdit).
