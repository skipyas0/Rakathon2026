// Labels and the board template (which specialist sections show, in what order). The template is a
// per-browser setting in localStorage. ponytail: per-tumour-board templates (brief BONUS) can
// replace DEFAULT_TEMPLATE later.
import type { Intent, Status } from './api'
import type { Case, Section, TimelineEvent } from './briefing'

export const SECTIONS: Record<string, string> = {
  surgery: 'Chirurgie',
  oncology: 'Klinická onkologie',
  radiology: 'Radiologie',
  pathology: 'Patologie',
  patient: 'Pacient',
  nuclear: 'Nukleární medicína',
  palliative: 'Paliativní péče',
  geriatric: 'Geriatrie',
  genetics: 'Klinická genetika',
  coordinator: 'Koordinátor',
}

export const SPECIALTIES = [
  'Předseda komise',
  'Klinický onkolog',
  'Chirurg',
  'Radiační onkolog',
  'Radiolog',
  'Patolog',
  'Koordinátor / sestra',
  'Jiná odbornost',
]

export const TUMOURS: Record<string, string> = {
  colorectal: 'Kolorektální karcinom',
  breast: 'Karcinom prsu',
  lung: 'Karcinom plic',
  gi: 'GIT',
  uro: 'Uroonkologie',
}

export const INTENTS: Record<Intent, { label: string; desc: string }> = {
  curative: { label: 'Kurativní', desc: 'Cílem je vyléčení' },
  palliative: { label: 'Paliativní', desc: 'Kontrola nemoci, délka a kvalita života' },
  supportive: { label: 'Podpůrná péče', desc: 'Úleva od obtíží bez protinádorové léčby' },
  surveillance: { label: 'Sledování', desc: 'Aktivní sledování, léčba zatím ne' },
}

export const KIND: Record<TimelineEvent['kind'], string> = {
  diagnosis: 'Diagnóza',
  staging: 'Staging',
  surgery: 'Operace',
  systemic: 'Systémová léčba',
  radiotherapy: 'Radioterapie',
  imaging: 'Zobrazení',
  progression: 'Progrese',
  mdt: 'MDT',
}

export const PHASES = [
  { id: 'prep', label: 'Před zasedáním', hint: 'Podklady a otázky' },
  { id: 'meeting', label: 'Zasedání', hint: 'Přehled pro komisi' },
  { id: 'followup', label: 'Po zasedání', hint: 'Závěr a úkoly' },
] as const
export type Phase = (typeof PHASES)[number]['id']

/** Index of the phase a case is in; `closed` = all three done. */
export const STATUS_STEP: Record<Status, number> = { prep: 0, meeting: 1, followup: 2, closed: 3 }
export const STATUS_LABEL: Record<Status, string> = {
  prep: 'V přípravě',
  meeting: 'Připraveno k projednání',
  followup: 'Realizace závěru',
  closed: 'Uzavřeno',
}

export type Template = { order: string[]; hidden: string[] }
export const DEFAULT_TEMPLATE: Template = { order: Object.keys(SECTIONS), hidden: [] }

/** The case's sections in template order; sections the template doesn't know go last. */
export function orderedSections(c: Case, t: Template): Section[] {
  const rank = (id: string) => (t.order.includes(id) ? t.order.indexOf(id) : t.order.length)
  return c.sections.filter((s) => !t.hidden.includes(s.id)).sort((a, b) => rank(a.id) - rank(b.id))
}

export const fmtDate = (d: string) => new Date(d).toLocaleDateString('cs-CZ')
export const fmtDateTime = (d: string) => new Date(d).toLocaleString('cs-CZ', { dateStyle: 'short', timeStyle: 'short' })

export function load<T>(key: string, fallback: T): T {
  try {
    const v = localStorage.getItem(key)
    return v ? (JSON.parse(v) as T) : fallback
  } catch {
    return fallback
  }
}

export function save(key: string, value: unknown) {
  try {
    localStorage.setItem(key, JSON.stringify(value))
  } catch {
    // storage unavailable (private window): settings just won't persist
  }
}
