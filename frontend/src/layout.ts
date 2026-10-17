// Labels, the journey's steps, formatting and per-browser settings.
import type { Intent } from './api'
import type { TimelineEvent } from './briefing'

/** Specialties that can sit on the board (the dataset's board members plus the brief's extra
 * roles); the id is also the briefing's section id (the converter fills only the first four). */
export const SPECIALTIES: Record<string, string> = {
  surgery: 'Chirurgie',
  oncology: 'Klinická onkologie',
  radiology: 'Radiologie',
  pathology: 'Patologie',
  radiotherapy: 'Radiační onkologie',
  nuclear: 'Nukleární medicína',
  pneumology: 'Pneumologie',
  gastroenterology: 'Gastroenterologie',
  urology: 'Urologie',
  cardiology: 'Kardiologie',
  genetics: 'Klinická genetika',
  pharmacy: 'Klinická farmacie',
  palliative: 'Paliativní péče',
  geriatric: 'Geriatrie',
}

export const MIN_SPECIALTIES = 3 // brief: at least 3 specialist roles (the backend enforces it too)


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
  deferred: { label: 'Odloženo', desc: 'Rozhodnutí po doplnění vyšetření' },
}

export const KIND: Record<TimelineEvent['kind'], string> = {
  diagnosis: 'Diagnóza',
  staging: 'Staging',
  pathology: 'Patologie',
  surgery: 'Operace',
  systemic: 'Systémová léčba',
  radiotherapy: 'Radioterapie',
  imaging: 'Zobrazení',
  progression: 'Progrese',
  mdt: 'MDT',
}

/** The coordinator's journey (docs/workflow-plan.md); `upload` lives at #/new, the rest at #/case/<id>/<id>. */
export const STEPS = [
  { id: 'upload', label: 'Nahrání' },
  { id: 'board', label: 'Komise' },
  { id: 'patient', label: 'Pacient' },
  { id: 'course', label: 'Průběh' },
  { id: 'facts', label: 'Klíčové informace' },
  { id: 'questions', label: 'Otázky' }, // short labels: all 10 chevrons fit the journey column
  { id: 'intent', label: 'Plán' }, // léčebný záměr + the specialties' quick picks
  { id: 'plan', label: 'Závěr' },
  { id: 'confirm', label: 'Potvrzení' },
  { id: 'export', label: 'Export' },
] as const
export type Step = (typeof STEPS)[number]['id']

export const fmtDate = (d: string) => new Date(d).toLocaleDateString('cs-CZ')
export const fmtDateTime = (d: string) => new Date(d).toLocaleString('cs-CZ', { dateStyle: 'short', timeStyle: 'short' })

export function load<T>(key: string, fallback: T): T {
  try {
    const v = localStorage.getItem(key)
    const parsed: unknown = v ? JSON.parse(v) : fallback
    // storage outlives app versions: a value of another type (e.g. an old object) is ignored
    return typeof parsed === typeof fallback ? (parsed as T) : fallback
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

/** Where Steps remembers the furthest step reached in one case's journey. */
export const reachedKey = (journey: string, caseId: string) => `mdt.reached.${journey}.${caseId}`

/** A reset case starts over: its chevrons link only back again. */
export function forgetReached(caseId: string) {
  try {
    for (const k of Object.keys(localStorage)) if (k.startsWith('mdt.reached.') && k.endsWith(`.${caseId}`)) localStorage.removeItem(k)
  } catch {
    // storage unavailable: nothing was remembered
  }
}
