import type { Confirmation } from './api'
import { Check, Robot } from './icons'
import { fmtDateTime } from './layout'
import type { Statement } from './provenance'
import { useSources } from './sources'

type Props = {
  s: Statement
  confirmation?: Confirmation
  onConfirm?: () => void // omitted = no confirm button
  variant?: 'card' | 'inline'
}

// The one way to render clinical content. Unconfirmed AI output is always marked blue with a robot;
// everything else (records, clinician input, confirmed AI) reads as plain fact. Sources are one
// click away in both variants. Don't render Statement.text anywhere without this component.
export function StatementView({ s, confirmation, onConfirm, variant = 'card' }: Props) {
  const show = useSources()
  const by = s.confirmed_by ?? confirmation?.by
  const at = s.confirmed_at ?? confirmation?.at
  const pending = s.origin === 'ai' && !by
  const open = () => show({ title: s.text, sources: s.sources, ai: pending ? s.model : null })

  if (variant === 'inline')
    return (
      // a span, not a <button>: buttons can't wrap inline with list bullets
      <span
        role="button"
        tabIndex={0}
        className={`stmt-inline ${pending ? 'ai' : ''}`}
        onClick={open}
        onKeyDown={(e) => (e.key === 'Enter' || e.key === ' ') && (e.preventDefault(), open())}
        title="Zobrazit zdroje"
      >
        {s.text}
        {pending && <Robot label="Návrh AI, nepotvrzeno" />}
      </span>
    )

  return (
    <div className={`stmt ${pending ? 'ai' : ''}`}>
      {pending && (
        <span className="ai-chip">
          <Robot /> AI návrh
        </span>
      )}
      <p>{s.text}</p>
      <div className="stmt-foot">
        {s.sources.length > 0 && (
          <button className="link" onClick={open}>
            Zdroje ({s.sources.length})
          </button>
        )}
        {by && (
          <span className="confirmed">
            <Check /> {by}
            {at && `, ${fmtDateTime(at)}`}
          </span>
        )}
        {pending && onConfirm && (
          <button className="confirm" onClick={onConfirm}>
            <Check /> Potvrdit
          </button>
        )}
      </div>
    </div>
  )
}
