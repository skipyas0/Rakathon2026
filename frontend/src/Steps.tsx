import { useEffect } from 'react'
import { load, reachedKey, save, STEPS } from './layout'

type Props = { current: string; caseId?: string; steps?: readonly { id: string; label: string }[] }

/** Progress through the journey as chevrons: steps up to the furthest one reached in this case
 * (remembered per browser) are light green and link, back or forward; the current one is solid
 * green. Narrow windows show only the current step between ‹ and ›, which work the same way. */
export function Steps({ current, caseId, steps = STEPS }: Props) {
  const at = steps.findIndex((s) => s.id === current)
  // the journey's last step names it: the coordinator's and a specialist's are kept apart
  const key = caseId && reachedKey(steps[steps.length - 1].id, caseId)
  const reached = Math.max(at, key ? load(key, -1) : -1)
  useEffect(() => {
    if (key) save(key, reached)
  }, [key, reached])
  // the upload step has no page for an existing case, so the coordinator's first link is the board
  const href = (i: number) =>
    caseId && i >= 0 && i <= reached && i !== at && steps[i].id !== 'upload'
      ? `#/case/${encodeURIComponent(caseId)}/${steps[i].id}`
      : undefined
  const back = href(at - 1)
  const forward = href(at + 1)
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
        {forward ? (
          <a className="step-arrow" href={forward} aria-label={`Dál: ${steps[at + 1].label}`}>
            ›
          </a>
        ) : (
          <span className="step-arrow off" title="Dál přes tlačítko Další na stránce" aria-hidden>
            ›
          </span>
        )}
      </div>
      <ol className="steps">
        {steps.map((s, i) => {
          const cls = `chevron ${i === at ? 'now' : i <= reached ? 'done' : ''}`
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
