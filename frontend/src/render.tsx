// Helpers shared by the phases (kept out of component files so fast refresh works).
import type { CaseRecord } from './api'
import { type Case, NOT_FOUND, statements } from './briefing'
import type { Statement } from './provenance'
import { StatementView } from './StatementView'

export type Render = (key: string, s: Statement, variant?: 'card' | 'inline') => React.ReactNode

export const now = () => new Date().toISOString()

/** Renders statements with their confirmation state from the record; `onConfirm` adds confirm buttons. */
export const renderer =
  (record: CaseRecord, onConfirm?: (key: string) => void): Render =>
  (key, s, variant = 'card') => (
    <StatementView
      key={key}
      s={s}
      variant={variant}
      confirmation={record.confirmations[key]}
      onConfirm={onConfirm && (() => onConfirm(key))}
    />
  )

/** Confirm handler that signs a statement with the user's name; undefined without a name. */
export const confirmer = (record: CaseRecord, save: (r: CaseRecord) => void, user: string) =>
  user
    ? (key: string) => save({ ...record, confirmations: { ...record.confirmations, [key]: { by: user, at: now() } } })
    : undefined

export const isPending = (record: CaseRecord, key: string, s: Statement) =>
  s.origin === 'ai' && !s.confirmed_by && !record.confirmations[key]

/** Statements that say data is missing (no source, ends with the required wording). */
export const missing = (c: Case) => statements(c).filter(([, s]) => !s.sources.length && s.text.endsWith(NOT_FOUND))
