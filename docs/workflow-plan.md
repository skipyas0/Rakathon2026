# MDT workflow: frontend plan

**Audience:** the team and their coding agents. This is the agreed target for the frontend (decision
#16). It describes what we are building; [architecture.md](architecture.md) describes what exists.
Scope = items marked **POVINNÉ** in [problem_statement.md](problem_statement.md); BONUS items wait.
Process rules come from [MDT_ZASEDANI_PROCES.md](MDT_ZASEDANI_PROCES.md), which wins over the brief.

## Roles (role switcher, no login)

| Role | Does |
|------|------|
| **Koordinátor** | Admin of the case: intake, triage of AI findings, picks the board, orders sections, sets who sees what, tracks specialists, writes the minutes during the meeting, ticks each member's consent, locks and exports. Not a clinician: does not confirm AI clinical claims and does not write the MDT question. |
| **Specialista** (Chirurgie, Klinická onkologie, Radiologie, Patologie) | Sees the shared header plus their own section and assigned findings; confirms or corrects AI claims in it; writes a short opinion for the board. |
| **Předsedající** | One of the specialists, marked on the board list. Leads the discussion; no extra rights (the conclusion needs everyone's consent). |
| **Komise** | Watches the projected dashboard. |

Who-sees-what is a per-patient table (role × section), edited by the coordinator and applied in the
UI only. ponytail: UI-side visibility, real access control needs logins.

## Flow

1. **Intake.** The coordinator uploads either one FHIR Bundle (`.json`) or several PDFs, one per
   record, from different dates (simulating documents from an external doctor). AI processing runs in
   the background and its progress is shown; the coordinator can continue meanwhile.
   *Mock until the backend pipeline is ready.* PDFs keep the record ids (`[P03-img02]`) from
   `Pxx_pacient.md`, so citations point to page + record.
2. **AI findings.** Red flags (severity + both sources) and missing data appear as they are found.
   Each gets a triage action: *na zasedání* / *vyřešit předem → assign to a specialist* / *zamítnout
   s důvodem*. A missing MDT question marks the case **neúplný**; the coordinator asks the
   nominating doctor and records the answer as theirs.
3. **Board.** The coordinator picks the specialists present (≥ 3 roles) and marks the chair.
4. **Structure.** Drag-and-drop the section order (↑↓ buttons for keyboard), show/hide sections,
   detail level: bullet points vs narrative text.
5. **Specialists prepare.** Each confirms/corrects the AI claims in their section and writes an
   opinion; the coordinator sees progress per specialist. → *Připraveno k projednání*.
6. **Meeting.** Projected dashboard for the board; the coordinator writes the minutes on their own
   device. No shared live session.
7. **Conclusion.** Structured record (template [form.md](template_zaver_zasedani/form.md) + brief
   block C), AI guideline-compliance check (warns, asks for a reason, never blocks), coordinator
   ticks each member's consent, then locks. Export PDF / FHIR.
8. **After the meeting.** Four separate states: MDT recommendation (locked) · patient's stance ·
   agreed plan · care delivered.
9. **History.** Every past MDT of the patient, read-only: question, conclusion, who consented, when,
   version; audit log of changes and confirmations. A new MDT never overwrites an old one.

## Screens

```
Top bar: MDT Copilot  [Program] [Nový případ]                      Role: [Koordinátor ▾]
Program (agenda by meeting date) → Případ (one patient, one meeting):
  Příprava (coordinator) │ Můj pohled (specialist) │ Zasedání │ Po zasedání │ Historie
```

**Nový případ**
```
 Zdroj: (•) FHIR soubor (.json)  ( ) Dokumenty PDF od externího lékaře
 [ Přetáhněte soubory sem / vybrat ]
 🤖 Zpracování: ✓ Načteno 9 dokumentů  ✓ Extrakce údajů  ◌ Hledání nesrovnalostí…
 Mezitím můžete pokračovat → [Sestavit komisi]
```

**Příprava** (coordinator; steps in any order)
```
 P03 · Karcinom sigmatu · MDT 21. 10.   ⚠ Neúplné: chybí otázka pro MDT   [Připraveno k projednání]
 [Podklady ✓] [Nálezy AI 5] [Komise 4] [Struktura] [Viditelnost] [Odborníci 2/4]
 Nálezy AI:  VYSOKÁ │ 🤖 Hb ↓ + únava 8/10 │ [lab][PROMs] │ (•) Na zasedání ( ) Předem → [Patolog ▾] ( ) Zamítnout
 Komise:     ☑ Chirurgie [MUDr. A]  ☑ Onkologie [MUDr. B, předsedající]  ☑ Radiologie  ☐ Patologie
 Struktura:  ≡ Souhrn ≡ Onkologie ≡ Chirurgie ≡ Radiologie ≡ Pacient    Detail: (•) odrážky ( ) text
 Odborníci:  Chirurg MUDr. A — potvrzeno 4/6 tvrzení AI, stanovisko ✓
```

**Můj pohled** (specialist)
```
 Otázka pro MDT · souhrn (3 řádky)
 Chirurgie   🤖 Resekabilní 3 ložiska v S6–S7 [CT]   [Potvrdit] [Opravit]
             📄 Chůze 500 m bez zastávky [dotazník]
 Přiřazeno vám: ⚠ TNM se liší ve dvou zprávách → [Vyřešeno: …]
 Stanovisko pro komisi: [ … ]
```

**Zasedání** (board dashboard: minimal, only urgent flags, everything clicks through to its source)
```
 P03 · 61 let · karcinom sigmatu, MTS jater       ECOG lékař 1 · pacient 2 ⚠      [Zápis ▸]
 OTÁZKA (MUDr. X, nominace): Resekabilita jaterních MTS po konverzní CHT?
 Souhrn (30 s)                     │ ⚠ Urgentní (2)                         + 3 další ▸
 Časová osa ──●Dg──●Op──●CHT──●CT──●MDT──●dnes
 Podpora rozhodování 🤖: možnosti [KRC-2.3] · studie (vhodný / nevhodný / chybí údaj) · 2–3 otázky
 [Chirurgie ✓] [Onkologie ✓] [Radiologie ⚠1] [Patologie –] [Pacient]   ← expand for detail
```

**Zápis** (coordinator, own device)
```
 Přítomní (z komise) · Zvažované možnosti (předvyplněno) · Doporučený postup · Záměr · Zdůvodnění
 Odlišná stanoviska · Studie · Re-evaluace [datum]
 🤖 Kontrola souladu: odchylka od KRC-2.3 → Důvod: [ … ]   (neblokuje)
 Souhlas: ☑ MUDr. A ☑ MUDr. B ☐ MUDr. C        [Uzamknout závěr] → [PDF] [FHIR]
```

## POVINNÉ items → where

| problem_statement.md | Screen |
|---|---|
| A: diagnosis, reason, ECOG doctor vs patient | Zasedání header |
| A: MDT question, missing → incomplete | Příprava, Zasedání |
| A: timeline | Zasedání |
| B: ≥ 3 specialist roles | Můj pohled, Zasedání tiles |
| B2: guideline options (RAG), trial screening, 2–3 questions | Zasedání (backend mock until ready) |
| B2: guideline-compliance check on the conclusion | Zápis |
| C: editable record during the meeting, structured record, export | Zápis |
| Config: sections, order, specialties present, detail level | Příprava |
| Red flags with severity + both sources | Příprava, Zasedání |
| Click-through to the exact source, missing data stated | everywhere (SourceDrawer) |

## Backend needs (coordinate with the backend owner)

New code goes in `features/<name>.py` to avoid conflicts; shared files (`app.py`, `briefing.py`)
get minimal edits.

- Records keyed per meeting (`<patient>-<date>`), not per patient; history = dataset
  `Composition` "Záznam MDT" + "Rozhodnutí o léčbě" + our locked records.
- `POST` intake (FHIR or PDFs) → case id + processing status. Mock: FHIR via `from_fhir.py`
  (already real); PDFs matched to the patient by the record ids inside.
- Record additions: finding triage, board (members, chair), per-member consent, visibility table,
  layout (order, hidden, detail), specialist opinions (existing notes), the four post-MDT states.
- Guideline-compliance check endpoint (mock).
- The `Case` shape (`briefing.py`) stays the contract with the AI pipeline (decision #5).

## Build order

1. Records per meeting + role switcher
2. Intake (mock processing)
3. Příprava: findings triage, board, structure, visibility, specialist progress
4. Zasedání dashboard
5. Zápis, consent, lock, export
6. Můj pohled
7. Po zasedání + Historie
