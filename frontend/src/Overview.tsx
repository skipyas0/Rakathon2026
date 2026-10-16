import { useEffect, useState } from 'react'
import { type AgendaItem, api } from './api'
import { Check } from './icons'
import { fmtDate, TUMOURS } from './layout'

/** Přehled: every case and whether its conclusion is confirmed; opens where the work continues. */
export function Overview() {
  const [items, setItems] = useState<AgendaItem[] | null>(null)
  const [error, setError] = useState('')
  useEffect(() => {
    api.agenda().then(setItems, (e: Error) => setError(e.message))
  }, [])

  return (
    <div className="page journey">
      <h1>Případy</h1>
      {error && <div className="banner bad">{error}</div>}
      <ul className="case-list">
        {items?.map((it) => {
          const confirmed = it.status === 'followup' || it.status === 'closed'
          const state = confirmed ? 'done' : it.specialties.length ? 'progress' : 'new'
          const step = confirmed ? 'confirm' : it.specialties.length ? 'patient' : 'board'
          return (
            <li key={it.id} className={`case-card ${state}`}>
              <a href={`#/case/${encodeURIComponent(it.id)}/${step}`}>
                <span className="case-name">{it.label}</span>
                <span className="chip">{TUMOURS[it.tumour] ?? it.tumour}</span>
                <span className="case-meta">{it.board}</span>
                <span className="case-meta">{it.mdt_date && `MDT ${fmtDate(it.mdt_date)}`}</span>
                <span className="pill">{confirmed ? <><Check /> Potvrzeno</> : state === 'progress' ? 'Rozpracováno' : 'Nový'}</span>
              </a>
            </li>
          )
        })}
      </ul>
    </div>
  )
}
