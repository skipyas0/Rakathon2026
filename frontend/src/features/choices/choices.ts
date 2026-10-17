// Plán's quick picks: common postupy per specialty, several at once; an option's sub-options show
// once it's picked, free text is last in every row (decision #32). The record keeps the labels
// (backend features/records.py: Choice, CHOICE_ROWS), so renaming one here changes new picks only.
import type { Choice, ChoiceRow, Decision } from '../../api'

/** `text`: the option takes free text (its placeholder); options sharing a `group` are either/or. */
export type Option = { label: string; sub?: string[]; text?: string; group?: string }
export type Picks = Decision['choices']

const FREE: Option = { label: 'Jiné', text: 'Upřesněte' }
const TREATMENT = ['Chemoterapie', 'Radioterapie', 'Chemoradioterapie']

export const CHOICE_ROWS: { id: ChoiceRow; label: string; options: Option[] }[] = [
  {
    id: 'oncology',
    label: 'Onkologie',
    options: [
      { label: 'Dispenzarizace' },
      { label: 'Systémová léčba' },
      { label: 'Neoadjuvantní léčba', sub: TREATMENT },
      { label: 'Adjuvantní léčba', sub: TREATMENT },
      { label: 'Symptomatická péče' },
      FREE,
    ],
  },
  {
    id: 'surgery',
    label: 'Chirurgie',
    options: [
      { label: 'Chirurgicky řešitelné', text: 'Rozsah výkonu', group: 'resectable' },
      { label: 'Chirurgicky neřešitelné', group: 'resectable' },
      FREE,
    ],
  },
  {
    id: 'radiology',
    label: 'Radiologie',
    options: [
      { label: 'Ve shodě s oficiálním popisem zobrazovacích vyšetření', group: 'report' },
      { label: 'Mimo shodu', text: 'V čem se liší', group: 'report' },
      FREE,
    ],
  },
  {
    id: 'pathology',
    label: 'Patologie',
    options: [{ label: 'Druhé čtení histologie' }, { label: 'Doplnění molekulární analýzy' }, FREE],
  },
  {
    id: 'other',
    label: 'Ostatní',
    options: [
      { label: 'Histologická verifikace', sub: ['Biopsie pod ultrazvukem', 'Biopsie pod CT', 'Otevřená biopsie'] },
      { label: 'Doplnění', sub: ['Chybějící dokumentace', 'CT', 'MRI', 'PET-CT', 'Endoskopie', 'Sonografie'] },
      FREE,
    ],
  },
]

/** As the export prints it: "Neoadjuvantní léčba (Chemoterapie)", "Mimo shodu: …". */
export const choiceText = (c: Choice) => (c.sub.length ? `${c.option} (${c.sub.join(', ')})` : c.option) + (c.text ? `: ${c.text}` : '')

/** What gets saved: texts trimmed, "Jiné" without text and empty rows dropped. */
export const cleanChoices = (picks: Picks): Picks =>
  Object.fromEntries(
    CHOICE_ROWS.flatMap(({ id }) => {
      const row = (picks[id] ?? []).map((c) => ({ ...c, text: c.text.trim() })).filter((c) => c.option !== FREE.label || c.text)
      return row.length ? [[id, row]] : []
    }),
  )
