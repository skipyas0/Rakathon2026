// Plán's quick-pick rows (options and rules in choices.ts).
import { Fragment } from 'react'
import type { Choice } from '../../api'
import { Check } from '../../icons'
import { CHOICE_ROWS, type Option, type Picks } from './choices'

/** One row per specialty; each scrolls sideways when its chips don't fit. */
export function ChoiceRows({ value, onChange, disabled }: { value: Picks; onChange: (v: Picks) => void; disabled: boolean }) {
  return (
    <div className="choice-rows">
      {CHOICE_ROWS.map((row) => {
        const picks = value[row.id] ?? []
        const set = (next: Choice[]) => onChange({ ...value, [row.id]: next })
        // kept in the row's order, so the record reads the same whichever was picked first
        const toggle = (o: Option) =>
          set(
            picks.some((p) => p.option === o.label)
              ? picks.filter((p) => p.option !== o.label)
              : row.options.flatMap((x) =>
                  x === o ? [{ option: o.label, sub: [], text: '' }] : picks.filter((p) => p.option === x.label && !(o.group && x.group === o.group)),
                ),
          )
        const update = (o: Option, u: Partial<Choice>) => set(picks.map((p) => (p.option === o.label ? { ...p, ...u } : p)))
        return (
          <div key={row.id} className="choice-row">
            <span className="eyebrow">{row.label}</span>
            <div className="choice-scroll small-bubbles" role="group" aria-label={row.label}>
              {row.options.map((o) => {
                const pick = picks.find((p) => p.option === o.label)
                return (
                  <Fragment key={o.label}>
                    <button className={`bubble ${pick ? 'on' : ''}`} aria-pressed={!!pick} disabled={disabled} onClick={() => toggle(o)}>
                      {pick && <Check />} {o.label}
                    </button>
                    {pick &&
                      o.sub?.map((s) => {
                        const on = pick.sub.includes(s)
                        const sub = on ? pick.sub.filter((x) => x !== s) : o.sub!.filter((x) => x === s || pick.sub.includes(x))
                        return (
                          <button key={s} className={`bubble sub ${on ? 'on' : ''}`} aria-pressed={on} disabled={disabled} onClick={() => update(o, { sub })}>
                            {on && <Check />} {s}
                          </button>
                        )
                      })}
                    {pick && o.text && (
                      <input
                        className="choice-text"
                        value={pick.text}
                        placeholder={o.text}
                        disabled={disabled}
                        aria-label={`${row.label}, ${o.label}`}
                        onChange={(e) => update(o, { text: e.target.value })}
                      />
                    )}
                  </Fragment>
                )
              })}
            </div>
          </div>
        )
      })}
    </div>
  )
}
