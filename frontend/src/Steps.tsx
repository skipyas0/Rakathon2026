import { type Step, STEPS } from './layout'

/** Progress through the journey; finished steps link back (case id known after the upload). */
export function Steps({ current, caseId }: { current: Step; caseId?: string }) {
  const at = STEPS.findIndex((s) => s.id === current)
  return (
    <>
      <p className="steps-compact">
        {at + 1} / {STEPS.length} · <strong>{STEPS[at].label}</strong>
      </p>
      <ol className="steps" aria-label="Postup">
      {STEPS.map((s, i) => (
        <li key={s.id} className={i < at ? 'done' : i === at ? 'now' : ''} aria-current={i === at ? 'step' : undefined}>
          {caseId && i > 0 && i < at ? <a href={`#/case/${encodeURIComponent(caseId)}/${s.id}`}>{s.label}</a> : <span>{s.label}</span>}
        </li>
      ))}
      </ol>
    </>
  )
}
