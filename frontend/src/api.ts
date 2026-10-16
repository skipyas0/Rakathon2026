// Backend calls + the record types (mirror of backend/src/mdt_backend/features/records.py).
import type { Case } from './briefing'

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
}

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
  confirmed_by: string | null
  confirmed_at: string | null
}
export type Task = { what: string; who: string; due: string | null; done: boolean }
export type CaseRecord = {
  confirmations: Record<string, Confirmation>
  prep: Prep
  notes: Record<string, Note>
  decision: Decision
  tasks: Task[]
}

export type IntakeKind = 'fhir' | 'pdf'

async function call<T>(url: string, init?: RequestInit): Promise<T> {
  const r = await fetch(url, init)
  const body = await r.json()
  if (!r.ok) {
    const d = body.detail
    throw new Error(typeof d === 'string' ? d : (d?.[0]?.msg?.replace(/^Value error, /, '') ?? r.statusText))
  }
  return body
}

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
  intake: (kind: IntakeKind, files: { name: string; data: string }[]) =>
    call<{ case_id: string }>('/api/intake', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ kind, files }),
    }),
}
