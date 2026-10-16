import { useEffect, useState } from 'react'
import { type AgendaItem, api } from './api'
import { Check } from './icons'
import { fmtDate } from './layout'

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
          const step = confirmed ? 'confirm' : it.specialties.length ? 'patient' : 'board'
          return (
            <li key={it.id}>
              <a href={`#/case/${encodeURIComponent(it.id)}/${step}`}>
                <strong>{it.label}</strong>
                <span className="muted">{[it.board, it.mdt_date && `MDT ${fmtDate(it.mdt_date)}`].filter(Boolean).join(' · ')}</span>
                <span className={`state ${confirmed ? 'ok' : ''}`}>{confirmed ? <><Check /> Potvrzeno</> : 'Rozpracováno'}</span>
              </a>
            </li>
          )
        })}
      </ul>
    </div>
  )
}
