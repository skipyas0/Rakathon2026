// Helpers shared by the screens (kept out of component files so fast refresh works).
import type { CaseRecord } from './api'
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
