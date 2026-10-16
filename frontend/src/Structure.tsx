import { useState } from 'react'
import type { CaseRecord, Layout } from './api'
import type { Case } from './briefing'
import { orderedSections, SECTIONS } from './layout'

type Props = { c: Case; record: CaseRecord; save: (r: CaseRecord) => void }

const DETAIL: Record<Layout['detail'], string> = { bullets: 'Odrážky (jednotlivá tvrzení)', narrative: 'Souvislý text' }

/** Coordinator: order of the specialist sections (drag & drop or ↑↓), which are shown, detail level. */
export function Structure({ c, record, save }: Props) {
  const layout = record.layout
  const order = orderedSections(c, { order: layout.order, hidden: [] }).map((s) => s.id)
  const [dragged, setDragged] = useState<string | null>(null)
  const onBoard = new Set(record.board.map((m) => m.specialty))
  const set = (l: Partial<Layout>) => save({ ...record, layout: { ...layout, ...l } })
  const moveTo = (id: string, index: number) => {
    const rest = order.filter((x) => x !== id)
    set({ order: [...rest.slice(0, index), id, ...rest.slice(index)] })
  }

  return (
    <section className="card">
      <h3>Struktura podkladu</h3>
      <p className="muted small">Pořadí a zobrazení sekcí odborností (příprava, zasedání i záznam). Přetáhněte nebo použijte šipky.</p>
      <ol className="structure">
        {order.map((id, i) => {
          const hidden = layout.hidden.includes(id)
          return (
            <li
              key={id}
              draggable
              className={`${dragged === id ? 'dragging' : ''} ${hidden ? 'off' : ''}`}
              onDragStart={() => setDragged(id)}
              onDragOver={(e) => e.preventDefault()}
              onDrop={() => dragged && dragged !== id && moveTo(dragged, i)}
              onDragEnd={() => setDragged(null)}
            >
              <span className="handle" aria-hidden>
                ⠿
              </span>
              <label className="inline">
                <input
                  type="checkbox"
                  checked={!hidden}
                  onChange={() => set({ hidden: hidden ? layout.hidden.filter((x) => x !== id) : [...layout.hidden, id] })}
                />{' '}
                {SECTIONS[id] ?? id}
              </label>
              {id !== 'patient' && record.board.length > 0 && !onBoard.has(id) && <small className="muted">není v komisi</small>}
              <button className="icon-btn" onClick={() => moveTo(id, i - 1)} disabled={i === 0} aria-label={`${SECTIONS[id] ?? id} výš`}>
                ↑
              </button>
              <button
                className="icon-btn"
                onClick={() => moveTo(id, i + 1)}
                disabled={i === order.length - 1}
                aria-label={`${SECTIONS[id] ?? id} níž`}
              >
                ↓
              </button>
            </li>
          )
        })}
      </ol>
      <fieldset>
        <legend>Míra detailu</legend>
        {(Object.keys(DETAIL) as Layout['detail'][]).map((d) => (
          <label key={d} className="inline">
            <input type="radio" name="detail" checked={layout.detail === d} onChange={() => set({ detail: d })} /> {DETAIL[d]}
          </label>
        ))}
      </fieldset>
    </section>
  )
}
