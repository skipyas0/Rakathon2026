import { useEffect, useState } from 'react'
import { type AgendaItem, api } from './api'
import { Alert, Check, IntentChip } from './icons'
import { fmtDate, PHASES, STATUS_LABEL, STATUS_STEP, TUMOURS } from './layout'

const TODAY = new Date().toLocaleDateString('cs-CZ', { weekday: 'long', day: 'numeric', month: 'long' })

/** The meeting agenda: one card per patient; each phase can be (re)opened from the card. */
export function Home() {
  const [items, setItems] = useState<AgendaItem[] | null>(null)
  const [error, setError] = useState('')
  useEffect(() => {
    api.agenda().then(
      (items) => setItems(items.sort((a, b) => (a.mdt_date ?? '9').localeCompare(b.mdt_date ?? '9'))),
      (e) => setError(e.message),
    )
  }, [])

  return (
    <div className="page">
      <header className="home-head">
        <p className="eyebrow">{TODAY}</p>
        <h1>Program zasedání</h1>
        {items && <p className="muted">{items.length} pacientů k projednání</p>}
      </header>
      {error && <div className="banner bad">{error}</div>}
      <ul className="cards">
        {items?.map((it) => {
          const step = STATUS_STEP[it.status]
          const href = (p: string) => `#/case/${encodeURIComponent(it.id)}/${p}`
          return (
            <li key={it.id} className={`patient-card status-${it.status}`}>
              <a className="card-main" href={href(PHASES[Math.min(step, 2)].id)}>
                <div className="card-top">
                  <h2>{it.label}</h2>
                  <span className="chip">{TUMOURS[it.tumour] ?? it.tumour}</span>
                </div>
                {(it.board || it.mdt_date) && (
                  <p className="card-board">
                    {[it.board, it.mdt_date && `MDT ${fmtDate(it.mdt_date)}`].filter(Boolean).join(' · ')}
                  </p>
                )}
                <p className={it.question ? 'card-q' : 'card-q missing'}>{it.question || 'Chybí otázka pro komisi'}</p>
                <div className="card-chips">
                  <IntentChip intent={it.intent} />
                  {it.flags > 0 && (
                    <span className="chip chip-bad">
                      <Alert /> {it.flags} závažné upozornění
                    </span>
                  )}
                </div>
              </a>
              <div className="card-foot">
                <span className="status-label">{STATUS_LABEL[it.status]}</span>
                <ol className="mini-steps" aria-label="Fáze">
                  {PHASES.map((p, i) => (
                    <li key={p.id}>
                      <a href={href(p.id)} className={i < step ? 'done' : i === step ? 'current' : ''} title={p.label}>
                        {i < step ? <Check /> : i + 1}
                        <span>{p.label}</span>
                      </a>
                    </li>
                  ))}
                </ol>
              </div>
            </li>
          )
        })}
      </ul>
    </div>
  )
}
