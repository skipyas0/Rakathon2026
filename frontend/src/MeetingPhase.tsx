import { useState } from 'react'
import type { CaseRecord } from './api'
import type { Case } from './briefing'
import { TrialList } from './CaseView'
import { confirmer, isPending, now, renderer } from './render'
import { TimelineStrip, TrendChart } from './Charts'
import { Alert, Arrow, Back, Check, IntentChip, Quote, Robot } from './icons'
import { fmtDateTime, orderedSections, type Phase, SECTIONS, type Template, TUMOURS } from './layout'

type Props = {
  c: Case
  record: CaseRecord
  save: (r: CaseRecord) => void
  user: string
  template: Template
  go: (p: Phase) => void
}

/** Phase 2: one calm screen for the whole board (the chair drives it). Statements are inline and
 * open their sources on click; specialist sections expand on demand for detail and the
 * specialist's view. */
export function MeetingPhase({ c, record, save, user, template, go }: Props) {
  const S = renderer(record)
  const [open, setOpen] = useState<string | null>(null)
  const question = record.prep.question || c.question?.text
  const sections = orderedSections(c, template)
  const patient = c.sections.find((s) => s.id === 'patient')
  const rank = { high: 0, medium: 1, low: 2 }
  const flags = [...c.red_flags.entries()].sort(([, a], [, b]) => rank[a.severity] - rank[b.severity])

  return (
    <div className="meeting">
      <div className="slide">
        <header className="slide-head">
          <div className="slide-meta">
            <span className="chip">{TUMOURS[c.tumour] ?? c.tumour}</span>
            <IntentChip intent={record.decision.intent} />
          </div>
          <p className="eyebrow">Otázka pro komisi</p>
          <h2 className="slide-question">{question ?? 'Chybí otázka pro komisi'}</h2>
          {(record.prep.questions.length > 0 || c.decision_support.questions.length > 0) && (
            <ul className="discuss">
              {c.decision_support.questions.map((s, i) => (
                <li key={`q${i}`}>{S(`questions.${i}`, s, 'inline')}</li>
              ))}
              {record.prep.questions.map((q, i) => (
                <li key={`h${i}`}>{q}</li>
              ))}
            </ul>
          )}
        </header>

        <div className="slide-grid">
          <section>
            <h3>Klíčová fakta</h3>
            <ul className="facts">
              {c.summary.map((s, i) => (
                <li key={i}>{S(`summary.${i}`, s, 'inline')}</li>
              ))}
            </ul>
            {flags.length > 0 && (
              <>
                <h3>Upozornění</h3>
                <ul className="facts flags-inline">
                  {flags.map(([i, f]) => (
                    <li key={i} className={`sev-${f.severity}`}>
                      <Alert /> {S(`red_flags.${i}`, f.statement, 'inline')}
                    </li>
                  ))}
                </ul>
              </>
            )}
          </section>

          <section>
            <h3>Vývoj</h3>
            <div className="trends">
              {c.trends.map((t) => (
                <TrendChart key={t.id} trend={t} />
              ))}
              {!c.trends.length && <p className="muted">Bez měřených hodnot.</p>}
            </div>
          </section>

          <section>
            <h3>Možnosti dle doporučených postupů</h3>
            <ol className="options">
              {c.decision_support.options.map((s, i) => (
                <li key={i}>{S(`options.${i}`, s, 'inline')}</li>
              ))}
            </ol>
            {c.decision_support.trials.length > 0 && (
              <>
                <h3>Klinické studie</h3>
                <div className="trials-inline">
                  <TrialList c={c} S={S} variant="inline" />
                </div>
              </>
            )}
            {patient && patient.items.length > 0 && (
              <div className="patient-voice">
                <span className="eyebrow">
                  <Quote /> Pacient
                </span>
                {patient.items.map((s, i) => (
                  <p key={i}>{S(`sections.patient.${i}`, s, 'inline')}</p>
                ))}
              </div>
            )}
          </section>
        </div>

        <TimelineStrip events={c.timeline} />

        <nav className="specialists" aria-label="Pohledy odborností">
          {sections.map((sec) => {
            const pending = sec.items.filter((s, i) => isPending(record, `sections.${sec.id}.${i}`, s)).length
            return (
              <button
                key={sec.id}
                className={`spec ${open === sec.id ? 'active' : ''}`}
                aria-expanded={open === sec.id}
                onClick={() => setOpen(open === sec.id ? null : sec.id)}
              >
                {SECTIONS[sec.id] ?? sec.title}
                {record.notes[sec.id] ? <Check /> : pending > 0 && <Robot label={`${pending} návrhů AI`} />}
              </button>
            )
          })}
        </nav>
      </div>

      {open && (
        <SpecialistPanel
          key={open}
          id={open}
          c={c}
          record={record}
          save={save}
          user={user}
          close={() => setOpen(null)}
        />
      )}

      <footer className="phase-nav">
        <button onClick={() => go('prep')}>
          <Back /> Příprava
        </button>
        <button className="primary" onClick={() => go('followup')}>
          Zapsat závěr <Arrow />
        </button>
      </footer>
    </div>
  )
}

function SpecialistPanel({
  id,
  c,
  record,
  save,
  user,
  close,
}: Omit<Props, 'template' | 'go'> & { id: string; close: () => void }) {
  const sec = c.sections.find((s) => s.id === id)!
  const note = record.notes[id]
  const [text, setText] = useState(note?.text ?? '')
  const [by, setBy] = useState(note?.by ?? '')
  const S = renderer(record, confirmer(record, save, user))
  const submit = () =>
    text.trim() &&
    save({ ...record, notes: { ...record.notes, [id]: { text: text.trim(), by: by.trim() || user, at: now() } } })

  return (
    <section className="card panel">
      <header className="panel-head">
        <h3>{SECTIONS[id] ?? sec.title}</h3>
        <button className="icon-btn" onClick={close} aria-label="Zavřít">
          ×
        </button>
      </header>
      <div className="panel-grid">
        <div>{sec.items.map((s, i) => S(`sections.${id}.${i}`, s))}</div>
        <form
          className="note-form"
          onSubmit={(e) => {
            e.preventDefault()
            submit()
          }}
        >
          <label>
            Stanovisko odbornosti
            <textarea value={text} onChange={(e) => setText(e.target.value)} placeholder="Co z pohledu odbornosti doporučujete?" />
          </label>
          <label>
            Za odbornost
            <input value={by} onChange={(e) => setBy(e.target.value)} placeholder="MUDr. …" />
          </label>
          <button type="submit" className="primary" disabled={!text.trim() || !(by.trim() || user)}>
            Uložit stanovisko
          </button>
          {note && (
            <small className="muted">
              Uloženo: {note.by}, {fmtDateTime(note.at)}
            </small>
          )}
        </form>
      </div>
    </section>
  )
}
