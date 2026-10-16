import { useState } from 'react'
import type { CaseRecord, Decision, Task } from './api'
import type { Case } from './briefing'
import { CaseDetail } from './CaseView'
import { confirmer, renderer } from './render'
import { DecisionForm } from './DecisionForm'
import { Doc } from './icons'
import type { Template } from './layout'

type Props = {
  c: Case
  record: CaseRecord
  save: (r: CaseRecord) => Promise<void>
  user: string
  template: Template
}

const STANDARD_TASKS = (d: Decision): Task[] => [
  { what: 'Sdělit závěr komise pacientovi', who: 'Ošetřující lékař', due: null, done: false },
  { what: 'Odeslat zprávu praktickému lékaři', who: 'Koordinátor', due: null, done: false },
  { what: 'Odeslat zprávu odesílajícímu lékaři', who: 'Koordinátor', due: null, done: false },
  ...(d.reevaluation ? [{ what: 'Re-evaluace na MDT', who: 'Koordinátor', due: d.reevaluation, done: false }] : []),
]

/** Phase 3: record the decision, assign follow-up, export; full briefing alongside for reference. */
export function FollowupPhase({ c, record, save, user, template }: Props) {
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
          <DecisionForm key={record.decision.confirmed_at ?? 'draft'} saved={record.decision} user={user} onSave={(decision) => save({ ...record, decision })} />
        </section>

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
          </div>
        </section>
      </div>

      <aside className="phase-aside wide-aside">
        <h3 className="aside-title">Podklady</h3>
        <CaseDetail c={c} record={record} template={template} S={S} />
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
