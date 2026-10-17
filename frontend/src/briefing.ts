// Mirror of backend/src/mdt_backend/briefing.py. Keep both in sync (see AGENTS.md).
// GET /api/cases/:id → Case (the agenda list lives in api.ts)
import type { Intent } from './api'
import type { Source, Statement } from './provenance'

export type TimelineEvent = {
  date: string
  kind: 'diagnosis' | 'staging' | 'pathology' | 'surgery' | 'systemic' | 'radiotherapy' | 'imaging' | 'progression' | 'mdt'
  statement: Statement
}

export type RedFlag = { severity: 'high' | 'medium' | 'low'; statement: Statement }

export type Section = { id: string; title: string; items: Statement[] }

export type TrialMatch = {
  trial: string
  verdict: 'eligible' | 'ineligible' | 'missing_data'
  criteria: Statement[]
}

export type DecisionSupport = {
  options: Statement[]
  trials: TrialMatch[]
  questions: Statement[]
  intent?: Intent | null // léčebný záměr of the first option, compared with the conclusion
}

export type Case = {
  id: string
  patient: string
  label: string
  tumour: string
  board?: string | null
  mdt_date?: string | null
  question: Statement | null
  summary: Statement[]
  timeline: TimelineEvent[]
  red_flags: RedFlag[]
  sections: Section[]
  decision_support: DecisionSupport
  trends: Trend[]
  previous_board: BoardMember[] // who sat on the patient's last MDT (record's CareTeam)
  preference?: Statement[] // the patient's treatment wishes and goals (agent); empty = not briefed
}

/** name = practitioner id, '' when the record names only the role. */
export type BoardMember = { name: string; role: string; chair: boolean }

export type TrendPoint = { date: string; value: number; source: Source }
export type Trend = {
  id: string
  label: string
  unit: string
  ref_low?: number | null
  ref_high?: number | null
  axis?: [number, number] | null
  points: TrendPoint[]
}

export const NOT_FOUND = 'V dostupné dokumentaci se nenachází.'

/** Every statement in a case with its stable key (used for confirmations), e.g. "sections.surgery.2". */
export function statements(c: Case): [string, Statement][] {
  const out: [string, Statement][] = []
  c.summary.forEach((s, i) => out.push([`summary.${i}`, s]))
  c.red_flags.forEach((f, i) => out.push([`red_flags.${i}`, f.statement]))
  c.timeline.forEach((e, i) => out.push([`timeline.${i}`, e.statement]))
  c.sections.forEach((sec) => sec.items.forEach((s, i) => out.push([`sections.${sec.id}.${i}`, s])))
  c.decision_support.options.forEach((s, i) => out.push([`options.${i}`, s]))
  c.decision_support.trials.forEach((t, ti) => t.criteria.forEach((s, i) => out.push([`trials.${ti}.${i}`, s])))
  c.decision_support.questions.forEach((s, i) => out.push([`questions.${i}`, s]))
  return out
}
