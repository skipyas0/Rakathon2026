import { useState } from 'react'
import type { CaseRecord, Triage } from './api'
import type { Case } from './briefing'
import { FlagItem, MissingItem } from './CaseView'
import { fmtDateTime, SPECIALTIES } from './layout'
import { findingKeys, missing, now, renderer } from './render'

type Props = { c: Case; record: CaseRecord; save: (r: CaseRecord) => void; user: string }

const ACTIONS: Record<Triage['action'], string> = { meeting: 'Na zasedání', before: 'Vyřešit předem', dismissed: 'Zamítnout' }

/** Coordinator: route each finding to the meeting, to a specialist beforehand, or dismiss it. */
export function Findings({ c, record, save, user }: Props) {
  const S = renderer(record) // routing only: clinicians confirm the findings themselves
  const gaps = new Map(missing(c))
  const onBoard = [...new Set(record.board.map((m) => m.specialty))]
  const specialties = onBoard.length ? onBoard : Object.keys(SPECIALTIES)
  const set = (key: string, t: Pick<Triage, 'action' | 'assignee' | 'reason'>) =>
    save({
      ...record,
      triage: { ...record.triage, [key]: { ...t, resolution: record.triage[key]?.resolution ?? '', by: user, at: now() } },
    })

  const keys = findingKeys(c)
  if (!keys.length) return <p className="muted">Žádné rozpory ani chybějící údaje nenalezeny.</p>
  return (
    <div className="findings">
      <p className="muted small">
        Rozpory mezi zdroji a chybějící údaje. Rozhodněte, kde se vyřeší: na zasedání, předem u odbornosti, nebo nález
        zamítněte s důvodem. Věcně je potvrzuje lékař.
      </p>
      {keys.map((k) => {
        const i = Number(k.split('.')[1])
        return (
          <div key={k} className="finding">
            {k.startsWith('red_flags.') ? <FlagItem f={c.red_flags[i]} i={i} S={S} /> : <MissingItem k={k} s={gaps.get(k)!} S={S} />}
            <TriageControls t={record.triage[k]} specialties={specialties} user={user} onSet={(t) => set(k, t)} />
          </div>
        )
      })}
    </div>
  )
}

function TriageControls({
  t,
  specialties,
  user,
  onSet,
}: {
  t?: Triage
  specialties: string[]
  user: string
  onSet: (t: Pick<Triage, 'action' | 'assignee' | 'reason'>) => void
}) {
  const [action, setAction] = useState(t?.action)
  const [assignee, setAssignee] = useState(t?.assignee ?? specialties[0])
  const [reason, setReason] = useState(t?.reason ?? '')
  const pick = (a: Triage['action']) => {
    setAction(a)
    if (a === 'meeting') onSet({ action: a, assignee: null, reason: '' })
    if (a === 'before') onSet({ action: a, assignee, reason: '' })
  }

  return (
    <div className="triage">
      <div className="segmented" role="group" aria-label="Kde se nález vyřeší">
        {(Object.keys(ACTIONS) as Triage['action'][]).map((a) => (
          <button key={a} type="button" className={action === a ? 'on' : ''} aria-pressed={action === a} disabled={!user} onClick={() => pick(a)}>
            {ACTIONS[a]}
          </button>
        ))}
      </div>
      {action === 'before' && (
        <select
          aria-label="Odbornost"
          value={assignee}
          onChange={(e) => {
            setAssignee(e.target.value)
            onSet({ action: 'before', assignee: e.target.value, reason: '' })
          }}
        >
          {specialties.map((s) => (
            <option key={s} value={s}>
              {SPECIALTIES[s] ?? s}
            </option>
          ))}
        </select>
      )}
      {action === 'dismissed' && (
        <form
          className="row"
          onSubmit={(e) => {
            e.preventDefault()
            if (reason.trim()) onSet({ action: 'dismissed', assignee: null, reason: reason.trim() })
          }}
        >
          <input value={reason} onChange={(e) => setReason(e.target.value)} placeholder="Důvod zamítnutí" aria-label="Důvod zamítnutí" />
          <button type="submit" disabled={!reason.trim()}>
            Uložit
          </button>
        </form>
      )}
      <small className="muted">
        {t ? `${ACTIONS[t.action]}${t.assignee ? ` → ${SPECIALTIES[t.assignee] ?? t.assignee}` : ''} · ${t.by}, ${fmtDateTime(t.at)}` : 'Netříděno'}
      </small>
    </div>
  )
}
