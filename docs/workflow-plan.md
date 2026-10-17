# MDT workflow: the simple journey

**Audience:** the team and their coding agents. Agreed target for the frontend (decision #20).
One linear journey for the coordinator, bare essentials only:
no descriptions, no extra buttons, **Další** per screen and a grey **Předchozí** to the previous
tab (Vývoj: previous chart page first; screens with input save first, either way, and say so:
**Uložit a další** on Komise, Záměr and Závěr until the conclusion is locked). Leaving a screen
with unsaved input any other way (chevrons, top bar, role pick, closing the tab) asks first:
"Máte neuložené změny. Odejít bez uložení?"; cancelling keeps the screen and its input.

| # | Screen | What's on it |
|---|--------|--------------|
| 1 | Nahrání | Two rectangles with "nebo" between: FHIR (pick or drop a file → uploads at once) and PDF (greyed out, "Připravujeme") |
| 2 | Komise | Specialty bubbles; a tap adds it (green outline). At least 3 |
| 3 | Pacient | Labelled facts (patient, diagnosis, board, MDT date), up to 2 critical findings (else the 2 most important) as red/amber cards, the MDT question in a highlighted card (red when missing), the patient's wishes right under it (AI, when the agent briefed the case; 2 shown) |
| 4 | Průběh | Diagnoses (4 facts shown) + výkonnostní stav (ECOG), course of the disease (4 latest events); the rest of each one click away |
| 5 | Klíčové informace | Critical (high) and important (medium) red flags unrolled as red / amber cards; the rest in collapsible groups (minor warnings, missing data, each specialty's facts) |
| 6 | Vývoj | Four charts per screen (2×2) when the window is at least 981 × 820 px, else two; no scrolling; Další and Předchozí page through the series first, then leave the tab |
| 7 | Otázky k diskusi | The agent's 2–3 questions for the board, numbered, each with its source (AI); "not available" until the agent has briefed the case |
| 8 | Léčebný záměr | Square tiles: kurativní / paliativní / podpůrná péče / sledování / odloženo |
| 9 | Závěr | Zvolený postup, Zdůvodnění; stanovisko bubbles per specialty: green = supports, red = doesn't (click → stanovisko, stance switchable) |
| 10 | Potvrzení | Chosen vs recommended postup side by side; soulad s doporučenými postupy is automatic (léčebný záměr chosen = recommended); on a difference, Potvrdit opens a required Důvod odchylky field ("Potvrdit s odchylkou"); Potvrdit signs as "Koordinátor/ka", no name (decision #27). Stanovisko bubbles as on Závěr; anyone against blocks Potvrdit (no consensus). Potvrdit leads on to Export |
| 11 | Export | The conclusion as `template_zaver_zasedani` (header: board + patient; history: AI-drafted from the record, blue with sources; question; Závěr MDT: the decision) in a PDF preview, beside PDF and DOCX ("k úpravám") downloads and FHIR (greyed out, "Připravujeme"). "AI doplňuje podklady…" while the draft is made (~20 s, once); the format boxes carry a download icon; dark grey Zavřít (next to Předchozí) returns to Přehled |

**Specialists** (decision #27): the role button at the top right opens the **Vaše role** pop-up, one
bubble per role as on Komise (Koordinátor, Chirurgie, Klinická onkologie, Radiologie, Patologie;
the current one green); a tap picks it and leads to that role's Přehled.
A specialist's Přehled lists only the cases the coordinator put their specialty on the board of (a
case may show for no specialist), without the reset button or Nový případ. Their journey has three
screens:

| # | Screen | What's on it |
|---|--------|--------------|
| 1 | Pacient | As the coordinator's, with the red flags for their area |
| 2 | Klíčové informace | As the coordinator's, narrowed to their section, the patient's and their red flags |
| 3 | Stanovisko | Navržený postup (when written); Podporuje / Nepodporuje; their stanovisko: empty, then Vygenerovat (AI, blue, ~20 s, Potvrdit signs it) or Napsat / Upravit (their own); both signed with the specialty (one person per specialty, decision #27); while the text is open, Zavřít is **Uložit a zavřít** |

The coordinator's stanovisko bubbles show the specialist's stanovisko and stance (refreshed every
10 s on Závěr and Potvrzení); empty until the specialist adds one; other specialties keep the
"ukázka" text with a warning.

Plus **Přehled** (`#/`): one tidy line per case with a coloured status (Potvrzeno / Rozpracováno /
Nový); on narrower windows the board name, then the tumour, then the date fold away. A confirmed
case opens Export; a started case has a reset button (confirm dialog) that clears its record. While the agent briefs a patient (`mdt-agent`, a batch step), its card
says "AI připravuje…" and every screen of the case shows a blue banner; both check every 10 s and
the case reloads itself when the briefing is ready.

Progress: green chevrons above every screen (the current one solid; every step up to the furthest
one reached in the case links, so after going back the later steps are one click away; remembered
per browser, forgotten on reset). Below 980 px only the current step ("3 / 10 · Pacient") between
back and forward arrows, which link the same way.
Narrow screens (≤ 640 px): compact top bar and type, a smaller question, and Předchozí / Další fixed at the bottom edge, in the same place on
every screen, reachable even when the content has to scroll.

Rules that still hold: every statement opens its source; AI output is blue; examples standing in
where there's no AI output (recommended postup and stanoviska of cases the agent hasn't briefed, the
pathology stanovisko) carry a visible "ukázka" label; Potvrdit records
who confirmed and when, and means the board agreed (consensus). After that, Léčebný záměr and Závěr are read-only
and say so with a lock note (reset the case in Přehled to change them).

Known gaps (mandatory items in `problem_statement.md` left out for simplicity): section order and
detail level, trial screening. The backend keeps triage, visibility, notes, tasks and the patient's
stance in the record for later screens. Against `MDT_ZASEDANI_PROCES.md`: no per-member sign-off;
the stanovisko bubbles stand in (anyone against blocks Potvrdit); roles are picked, not logged in.
