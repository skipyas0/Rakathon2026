import { useState } from 'react'
import type { CaseRecord, Decision, PatientStance, Task } from './api'
import type { Case } from './briefing'
import { CaseDetail } from './CaseView'
import { confirmer, now, renderer } from './render'
import { DecisionForm } from './DecisionForm'
import { Check, Doc } from './icons'
import { fmtDateTime, INTENTS } from './layout'

type Props = {
  c: Case
  record: CaseRecord
  save: (r: CaseRecord) => Promise<void>
  user: string
}

const STANDARD_TASKS = (d: Decision): Task[] => [
  { what: 'Sdělit závěr komise pacientovi', who: 'Ošetřující lékař', due: null, done: false },
  { what: 'Odeslat zprávu praktickému lékaři', who: 'Koordinátor', due: null, done: false },
  { what: 'Odeslat zprávu odesílajícímu lékaři', who: 'Koordinátor', due: null, done: false },
  ...(d.reevaluation ? [{ what: 'Re-evaluace na MDT', who: 'Koordinátor', due: d.reevaluation, done: false }] : []),
]

/** Phase 3: record the decision, assign follow-up, export; full briefing alongside for reference. */
export function FollowupPhase({ c, record, save, user }: Props) {
  const S = renderer(record, confirmer(record, (r) => void save(r).catch(() => {}), user))
  const setTasks = (tasks: Task[]) => save({ ...record, tasks }).catch(() => {})
  const exportPdf = () => {
    document.querySelectorAll('details').forEach((d) => (d.open = true))
    print()
  }

  return (
    <div className="phase-grid followup">
      <div className="phase-main">
        <section className="card">
          <h3>Závěr komise</h3>
          <DecisionForm key={record.decision.confirmed_at ?? 'draft'} saved={record.decision} board={record.board} user={user} onSave={(decision) => save({ ...record, decision })} />
        </section>

        <AfterMeeting record={record} save={(r) => save(r).catch(() => {})} user={user} />

        <section className="card">
          <h3>Akční plán a komunikace</h3>
          <TaskList tasks={record.tasks} onChange={setTasks} />
          <div className="actions">
            {!record.tasks.length && (
              <button onClick={() => setTasks(STANDARD_TASKS(record.decision))}>Navrhnout standardní úkoly</button>
            )}
            <button className="primary" onClick={exportPdf}>
              <Doc /> Exportovat zápis (PDF)
            </button>
            <button disabled title="Připravujeme">
              <Doc /> Export do FHIR (připravujeme)
            </button>
          </div>
        </section>
      </div>

      <aside className="phase-aside wide-aside">
        <h3 className="aside-title">Podklady</h3>
        <CaseDetail c={c} record={record} S={S} />
      </aside>
    </div>
  )
}

function TaskList({ tasks, onChange }: { tasks: Task[]; onChange: (t: Task[]) => void }) {
  const [draft, setDraft] = useState<Task>({ what: '', who: '', due: null, done: false })
  const patch = (i: number, p: Partial<Task>) => onChange(tasks.map((t, j) => (j === i ? { ...t, ...p } : t)))
  return (
    <>
      <ul className="tasks">
        {tasks.map((t, i) => (
          <li key={i} className={t.done ? 'done' : ''}>
            <input type="checkbox" checked={t.done} onChange={() => patch(i, { done: !t.done })} aria-label="Splněno" />
            <span className="task-what">{t.what}</span>
            <span className="muted">{t.who}</span>
            <input type="date" value={t.due ?? ''} onChange={(e) => patch(i, { due: e.target.value || null })} aria-label="Termín" />
            <button className="link" onClick={() => onChange(tasks.filter((_, j) => j !== i))}>
              Odebrat
            </button>
          </li>
        ))}
      </ul>
      <form
        className="row"
        onSubmit={(e) => {
          e.preventDefault()
          if (!draft.what.trim()) return
          onChange([...tasks, { ...draft, what: draft.what.trim() }])
          setDraft({ what: '', who: '', due: null, done: false })
        }}
      >
        <input className="grow" value={draft.what} onChange={(e) => setDraft({ ...draft, what: e.target.value })} placeholder="Úkol, např. Objednat MR jater" />
        <input value={draft.who} onChange={(e) => setDraft({ ...draft, who: e.target.value })} placeholder="Odpovídá" />
        <input type="date" value={draft.due ?? ''} onChange={(e) => setDraft({ ...draft, due: e.target.value || null })} aria-label="Termín" />
        <button type="submit">Přidat</button>
      </form>
    </>
  )
}

const STANCES: Record<PatientStance['stance'], string> = {
  accepts: 'Souhlasí s doporučením',
  refuses: 'Odmítá doporučený postup',
  discuss: 'Chce dále prodiskutovat',
}

/** The four states after the meeting, kept apart (MDT_ZASEDANI_PROCES.md §6): what the board
 * recommended (locked), what the patient decided, the plan agreed with them, the care delivered. */
function AfterMeeting({ record, save, user }: { record: CaseRecord; save: (r: CaseRecord) => void; user: string }) {
  const d = record.decision
  const st = record.patient_stance
  const [stance, setStance] = useState<PatientStance['stance'] | undefined>(st?.stance)
  const [note, setNote] = useState(st?.note ?? '')
  const [plan, setPlan] = useState(record.agreed_plan)
  const done = record.tasks.filter((t) => t.done).length
  if (!d.confirmed_by) return null

  return (
    <section className="card after">
      <h3>Po zasedání</h3>
      <div className="after-grid">
        <div>
          <span className="eyebrow">1 · Doporučení MDT (uzamčeno)</span>
          <p>
            {d.intent && <strong>{INTENTS[d.intent].label}: </strong>}
            {d.plan}
          </p>
        </div>
        <form
          onSubmit={(e) => {
            e.preventDefault()
            if (stance) save({ ...record, patient_stance: { stance, note: note.trim(), by: user, at: now() } })
          }}
        >
          <span className="eyebrow">2 · Stanovisko pacienta</span>
          {(Object.keys(STANCES) as PatientStance['stance'][]).map((k) => (
            <label key={k} className="inline">
              <input type="radio" name="stance" checked={stance === k} onChange={() => setStance(k)} /> {STANCES[k]}
            </label>
          ))}
          <input value={note} onChange={(e) => setNote(e.target.value)} placeholder="Poznámka (např. co odmítá a proč)" aria-label="Poznámka" />
          <button type="submit" disabled={!stance || !user}>
            Zaznamenat
          </button>
          {st && (
            <small className="muted">
              <Check /> {st.by}, {fmtDateTime(st.at)}
            </small>
          )}
        </form>
        <form
          onSubmit={(e) => {
            e.preventDefault()
            save({ ...record, agreed_plan: plan.trim() })
          }}
        >
          <span className="eyebrow">3 · Dohodnutý léčebný plán</span>
          <textarea value={plan} onChange={(e) => setPlan(e.target.value)} placeholder="Postup po zohlednění doporučení a přání pacienta" />
          <button type="submit" disabled={plan.trim() === record.agreed_plan}>
            Uložit plán
          </button>
        </form>
        <div>
          <span className="eyebrow">4 · Realizovaná péče</span>
          <p>{record.tasks.length ? `Splněno ${done} z ${record.tasks.length} úkolů akčního plánu` : 'Akční plán zatím nemá úkoly.'}</p>
        </div>
      </div>
    </section>
  )
}
