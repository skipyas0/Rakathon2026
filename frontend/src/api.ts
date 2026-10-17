// Backend calls + the record types (mirror of backend/src/mdt_backend/features/records.py).
import type { Case } from './briefing'
import type { Statement } from './provenance'

export type Status = 'prep' | 'meeting' | 'followup' | 'closed'
export type Intent = 'curative' | 'palliative' | 'supportive' | 'surveillance' | 'deferred'
export type AgendaItem = {
  id: string
  label: string
  tumour: string
  board: string | null
  mdt_date: string | null
  question: string
  flags: number
  intent: Intent | null
  status: Status
  specialties: string[] // on the board; a specialist sees only these cases
  ai: AiStatus
}

/** The agent's briefing: being written now, written, or never run for the patient. */
export type AiStatus = 'running' | 'done' | null

export type Confirmation = { by: string; at: string }
export type Note = { text: string; by: string; at: string }
export type Prep = { question: string; questions: string[]; prepared_by: string | null; prepared_at: string | null }
export type Attendee = { name: string; specialty: string }
export type Decision = {
  attendees: Attendee[]
  intent: Intent | null
  options_considered: string
  plan: string
  rationale: string
  guideline_compliant: boolean | null
  deviation_reason: string
  dissent: string
  trial: string
  reevaluation: string | null
  confirmed_by: string | null // who confirmed the board's consensus
  confirmed_at: string | null
}
export type Task = { what: string; who: string; due: string | null; done: boolean }
export type Member = { name: string; specialty: string; chair: boolean; supports: boolean } // specialty = section id
export type Triage = {
  action: 'meeting' | 'before' | 'dismissed'
  assignee: string | null // specialty resolving it before the meeting
  reason: string // why dismissed
  resolution: string
  by: string
  at: string
}
export type PatientStance = { stance: 'accepts' | 'refuses' | 'discuss'; note: string; by: string; at: string }
export type Layout = { order: string[]; hidden: string[]; detail: 'bullets' | 'narrative' }
export type CaseRecord = {
  confirmations: Record<string, Confirmation>
  prep: Prep
  notes: Record<string, Note>
  decision: Decision
  tasks: Task[]
  board: Member[]
  triage: Record<string, Triage> // key = statement path of the finding, e.g. "red_flags.0"
  layout: Layout
  visibility: Record<string, string[]> // specialty → section ids; absent = own + patient
  patient_stance: PatientStance | null // the patient's decision; never changes the recommendation
  agreed_plan: string
  stanoviska: Record<string, Statement> // specialty → its specialist's stanovisko (features/roles)
}

export type IntakeKind = 'fhir' | 'pdf'

export type Recommendation = { intent: Intent; statement: Statement } | null

export type History = {
  documents: { reference: string; title: string; date: string | null; author: string | null; sections: { title: string; text: string }[] }[]
  meetings: { id: string; mdt_date: string | null; status: Status; decision: Decision }[]
}

async function call<T>(url: string, init?: RequestInit): Promise<T> {
  const r = await fetch(url, init)
  // a crash answers plain text, not JSON: say "server error" instead of a JSON parse error
  const body = await r.json().catch(() => {
    throw new Error(`Chyba serveru (HTTP ${r.status})`)
  })
  if (!r.ok) {
    const d = body.detail
    throw new Error(typeof d === 'string' ? d : (d?.[0]?.msg?.replace(/^Value error, /, '') ?? r.statusText))
  }
  return body
}

export const AI_POLL_MS = 10_000 // how often a page re-checks a running agent

const caseUrl = (id: string) => `/api/cases/${encodeURIComponent(id)}`

export const api = {
  agenda: () => call<AgendaItem[]>('/api/cases'),
  case: (id: string) => call<Case>(caseUrl(id)),
  record: (id: string) => call<CaseRecord>(`${caseUrl(id)}/record`),
  saveRecord: (id: string, record: CaseRecord) =>
    call<CaseRecord>(`${caseUrl(id)}/record`, {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(record),
    }),
  resetRecord: (id: string) => fetch(`${caseUrl(id)}/record`, { method: 'DELETE' }),
  history: (id: string) => call<History>(`${caseUrl(id)}/history`),
  recommendation: (id: string) => call<Recommendation>(`${caseUrl(id)}/recommendation`),
  ai: (id: string) => call<{ status: AiStatus }>(`${caseUrl(id)}/ai`),
  /** The AI's draft of the template's history fields: made on first call (~30 s), then cached. */
  zaverDraft: (id: string) => call<{ created: string }>(`${caseUrl(id)}/zaver/draft`, { method: 'POST' }),
  /** The specialist's step of the agent (~45 s); the AI draft replaces their stored stanovisko. */
  generateStanovisko: (id: string, specialty: string) =>
    call<CaseRecord>(`${caseUrl(id)}/stanovisko/${specialty}/generate`, { method: 'POST' }),
  /** Fields left out stay as they are. */
  updateStanovisko: (id: string, specialty: string, u: { supports?: boolean; statement?: Statement }) =>
    call<CaseRecord>(`${caseUrl(id)}/stanovisko/${specialty}`, {
      method: 'PATCH',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(u),
    }),
  intake: (kind: IntakeKind, files: { name: string; data: string }[]) =>
    call<{ case_id: string }>('/api/intake', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ kind, files }),
    }),
}
