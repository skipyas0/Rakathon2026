import { useEffect, useState } from 'react'
import { api, type CaseRecord } from './api'
import type { Case } from './briefing'
import { FollowupPhase } from './FollowupPhase'
import { Back, Check, IntentChip } from './icons'
import { History } from './History'
import { fmtDate, type Phase, PHASES, TUMOURS, type View } from './layout'
import { MeetingPhase } from './MeetingPhase'
import { PrepPhase } from './PrepPhase'
import { SpecialistView } from './SpecialistView'

type Props = { id: string; phase: View; user: string; role: string }

const go = (id: string, p: Phase) => (location.hash = `#/case/${encodeURIComponent(id)}/${p}`)

export function CasePage({ id, phase, user, role }: Props) {
  const [data, setData] = useState<{ c: Case; record: CaseRecord } | null>(null)
  const [error, setError] = useState('')

  useEffect(() => {
    Promise.all([api.case(id), api.record(id)]).then(
      ([c, record]) => setData({ c, record }),
      (e) => setError(e.message),
    )
  }, [id])

  const shown = data?.c.id === id ? data : null // stale case hidden while the next loads
  if (error) return <div className="banner bad page">{error}</div>
  if (!shown) return <p className="muted page">Načítám…</p>
  const { c, record } = shown
  // governance: a specialist sees only cases whose board includes their specialty (coordinator: all)
  if (role !== 'coordinator' && !record.board.some((m) => m.specialty === role))
    return <p className="banner page">Nejste v komisi tohoto případu. Komisi sestavuje koordinátor v přípravě.</p>

  // ponytail: last write wins; fine with one chair at the screen, needs per-field merge for concurrent editors
  const save = async (next: CaseRecord) => {
    setData({ c, record: next }) // optimistic
    try {
      setData({ c, record: await api.saveRecord(c.id, next) })
      setError('')
    } catch (e) {
      setData({ c, record: await api.record(c.id) }) // roll back to what the server has
      setError((e as Error).message)
      throw e
    }
  }
  const persist = (next: CaseRecord) => void save(next).catch(() => {})
  const doneSteps = [!!record.prep.prepared_by, !!record.decision.confirmed_by, record.tasks.length > 0 && record.tasks.every((t) => t.done)]

  return (
    <div className="page">
      <header className="case-head">
        <a href="#/" className="back">
          <Back /> Program zasedání
        </a>
        <div className="case-title">
          <h1>{c.label}</h1>
          <span className="chip">{TUMOURS[c.tumour] ?? c.tumour}</span>
          <IntentChip intent={record.decision.intent} />
        </div>
        {(c.board || c.mdt_date) && (
          <p className="muted case-board">{[c.board, c.mdt_date && `MDT ${fmtDate(c.mdt_date)}`].filter(Boolean).join(' · ')}</p>
        )}
        <ol className="stepper">
          {PHASES.map((p, i) => (
            <li key={p.id}>
              <a href={`#/case/${encodeURIComponent(c.id)}/${p.id}`} aria-current={p.id === phase ? 'step' : undefined} className={doneSteps[i] ? 'done' : ''}>
                <span className="step-num">{doneSteps[i] ? <Check /> : i + 1}</span>
                <span>
                  <strong>{p.id === 'prep' && role !== 'coordinator' ? 'Můj pohled' : p.label}</strong>
                  <small>{p.id === 'prep' && role !== 'coordinator' ? 'Moje sekce a stanovisko' : p.hint}</small>
                </span>
              </a>
            </li>
          ))}
        </ol>
        <a href={`#/case/${encodeURIComponent(c.id)}/history`} className={`history-link ${phase === 'history' ? 'on' : ''}`}>
          Historie pacienta
        </a>
      </header>
      {error && (
        <div className="banner bad" role="alert">
          {error} <button className="icon-btn" onClick={() => setError('')} aria-label="Zavřít">×</button>
        </div>
      )}
      {!user && <div className="banner">Zadejte své jméno vpravo nahoře – potvrzení a záznamy se podepisují vaším jménem.</div>}
      {phase === 'prep' &&
        (role === 'coordinator' ? (
          <PrepPhase c={c} record={record} save={persist} user={user} go={(p) => go(c.id, p)} />
        ) : (
          <SpecialistView c={c} record={record} save={persist} user={user} role={role} />
        ))}
      {phase === 'meeting' && <MeetingPhase c={c} record={record} save={persist} user={user} go={(p) => go(c.id, p)} />}
      {phase === 'followup' && <FollowupPhase c={c} record={record} save={save} user={user} />}
      {phase === 'history' && <History c={c} record={record} />}
    </div>
  )
}
