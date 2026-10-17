import { useEffect, useState } from 'react'
import { AI_POLL_MS, type AgendaItem, api } from './api'
import { Check, Reset, Robot } from './icons'
import { fmtDate, forgetReached, TUMOURS } from './layout'

/** Přehled: every case and whether its conclusion is confirmed; opens where the work continues.
 * A specialist (`role`) sees only the cases the coordinator put their specialty on the board of. */
export function Overview({ role }: { role: string }) {
  const [items, setItems] = useState<AgendaItem[] | null>(null)
  const [error, setError] = useState('')
  const [reloads, setReloads] = useState(0)
  useEffect(() => {
    let timer = 0
    const load = () =>
      api.agenda().then(
        (items) => {
          setItems(items)
          if (items.some((it) => it.ai === 'running')) timer = window.setTimeout(load, AI_POLL_MS)
        },
        (e: Error) => setError(e.message),
      )
    void load()
    return () => window.clearTimeout(timer)
  }, [reloads])

  const reset = async (it: AgendaItem) => {
    if (!window.confirm(`Smazat záznam případu ${it.label}? Komise, potvrzení a závěr se odstraní; data pacienta zůstanou.`)) return
    const r = await api.resetRecord(it.id)
    if (r.ok) {
      forgetReached(it.id)
      setReloads((n) => n + 1)
    }
    else setError(`Případ se nepodařilo vymazat (HTTP ${r.status})`)
  }

  const shown = role ? items?.filter((it) => it.specialties.includes(role)) : items
  return (
    <div className="page journey overview">
      <h1>Případy</h1>
      {error && <div className="banner bad">{error}</div>}
      {shown?.length === 0 && role && <p className="muted big">Koordinátor vám zatím nepřidělil žádný případ.</p>}
      <ul className="case-list">
        {shown?.map((it) => {
          const confirmed = it.status === 'followup' || it.status === 'closed'
          const state = confirmed ? 'done' : it.specialties.length ? 'progress' : 'new'
          const step = role ? 'patient' : confirmed ? 'export' : it.specialties.length ? 'patient' : 'board'
          return (
            <li key={it.id} className={`case-card ${state}`}>
              <a href={`#/case/${encodeURIComponent(it.id)}/${step}`}>
                <span className="case-name">
                  {it.label}{' '}
                  {it.ai === 'running' && (
                    <span className="chip ai-chip">
                      <Robot /> AI připravuje…
                    </span>
                  )}
                </span>
                <span className="chip case-tumour">{TUMOURS[it.tumour] ?? it.tumour}</span>
                <span className="case-meta case-board" title={it.board ?? ''}>{it.board}</span>
                <span className="case-meta case-date">{it.mdt_date && `MDT ${fmtDate(it.mdt_date)}`}</span>
                <span className="pill">{confirmed ? <><Check /> Potvrzeno</> : state === 'progress' ? 'Rozpracováno' : 'Nový'}</span>
              </a>
              {state !== 'new' && !role && (
                <button className="icon-btn case-reset" title="Vymazat záznam případu" aria-label={`Vymazat záznam případu ${it.label}`} onClick={() => void reset(it)}>
                  <Reset />
                </button>
              )}
            </li>
          )
        })}
      </ul>
    </div>
  )
}
