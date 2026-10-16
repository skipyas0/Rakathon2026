// Mirror of backend/src/mdt_backend/briefing.py. Keep both in sync (see AGENTS.md).
// GET /api/cases → CaseSummary[], GET /api/cases/:id → Case
import type { Statement } from './provenance'

export type TimelineEvent = {
  date: string
  kind: 'diagnosis' | 'staging' | 'surgery' | 'systemic' | 'radiotherapy' | 'imaging' | 'progression' | 'mdt'
  statement: Statement
}

export type RedFlag = { severity: 'high' | 'medium' | 'low'; statement: Statement }

export type Section = { id: string; title: string; items: Statement[] }

export type TrialMatch = {
  trial: string
  verdict: 'eligible' | 'ineligible' | 'missing_data'
  criteria: Statement[]
}

export type DecisionSupport = { options: Statement[]; trials: TrialMatch[]; questions: Statement[] }

export type Case = {
  id: string
  patient: string
  label: string
  tumour: string
  question: Statement | null
  summary: Statement[]
  timeline: TimelineEvent[]
  red_flags: RedFlag[]
  sections: Section[]
  decision_support: DecisionSupport
}

export type CaseSummary = Pick<Case, 'id' | 'label' | 'tumour'>
