import { STEPS } from './layout'

/** Progress through the journey as chevrons: finished steps (green) link back, the current one is
 * solid green. Narrow windows show only the current step, with a back arrow; forward goes through
 * the screen's own Další, which saves it, so the forward arrow stays disabled. */
type Props = { current: string; caseId?: string; steps?: readonly { id: string; label: string }[] }

export function Steps({ current, caseId, steps = STEPS }: Props) {
  const at = steps.findIndex((s) => s.id === current)
  // the upload step has no page for an existing case, so the coordinator's first link is the board
  const href = (i: number) =>
    caseId && i >= 0 && i < at && steps[i].id !== 'upload' ? `#/case/${encodeURIComponent(caseId)}/${steps[i].id}` : undefined
  const back = href(at - 1)
  return (
    <nav aria-label="Postup">
      <div className="steps-compact">
        {back ? (
          <a className="step-arrow" href={back} aria-label={`Zpět: ${steps[at - 1].label}`}>
            ‹
          </a>
        ) : (
          <span className="step-arrow off" aria-hidden>
            ‹
          </span>
        )}
        <span className="chevron now" aria-current="step">
          {at + 1} / {steps.length} · {steps[at].label}
        </span>
        <span className="step-arrow off" title="Dál přes tlačítko Další na stránce" aria-hidden>
          ›
        </span>
      </div>
      <ol className="steps">
        {steps.map((s, i) => {
          const cls = `chevron ${i < at ? 'done' : i === at ? 'now' : ''}`
          const link = href(i)
          return (
            <li key={s.id} aria-current={i === at ? 'step' : undefined}>
              {link ? <a className={cls} href={link}>{s.label}</a> : <span className={cls}>{s.label}</span>}
            </li>
          )
        })}
      </ol>
    </nav>
  )
}
