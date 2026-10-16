import { useState } from 'react'
import type { CaseRecord } from './api'
import type { Case } from './briefing'
import { SectionItems, Soon, TrialList } from './CaseView'
import { confirmer, findingKeys, isPending, missing, now, renderer } from './render'
import { TimelineStrip, TrendChart } from './Charts'
import { Alert, Arrow, Back, Check, IntentChip, Missing as MissingIcon, Quote, Robot } from './icons'
import { fmtDateTime, orderedSections, type Phase, SECTIONS, TUMOURS } from './layout'

type Props = {
  c: Case
  record: CaseRecord
  save: (r: CaseRecord) => void
  user: string
  go: (p: Phase) => void
}

/** Phase 2: the board's dashboard, projected while the coordinator keeps the minutes. One calm
 * screen: question, key facts, only urgent warnings; every statement opens its sources on click,
 * specialist sections expand on demand. */
export function MeetingPhase({ c, record, save, user, go }: Props) {
  const S = renderer(record)
  const [open, setOpen] = useState<string | null>(null)
  const question = record.prep.question || c.question?.text
  const sections = orderedSections(c, record.layout)
  const patient = c.sections.find((s) => s.id === 'patient')
  const [more, setMore] = useState(false)
  const ecog = c.summary.findIndex((s) => s.text.startsWith('ECOG'))
  // findings the coordinator didn't dismiss; urgent = high severity or routed to the meeting
  const gaps = new Map(missing(c))
  const live = findingKeys(c).filter((k) => record.triage[k]?.action !== 'dismissed')
  const urgent = (k: string) =>
    record.triage[k]?.action === 'meeting' || (k.startsWith('red_flags.') && c.red_flags[Number(k.split('.')[1])].severity === 'high')
  const shown = more ? live : live.filter(urgent)
  const dismissed = findingKeys(c).length - live.length
  const unresolved = (spec: string) =>
    Object.values(record.triage).filter((t) => t.action === 'before' && t.assignee === spec && !t.resolution.trim()).length

  return (
    <div className="meeting">
      <div className="slide">
        <header className="slide-head">
          <div className="slide-meta">
            <span className="chip">{TUMOURS[c.tumour] ?? c.tumour}</span>
            <IntentChip intent={record.decision.intent} />
            {ecog >= 0 && <span className="ecog">{S(`summary.${ecog}`, c.summary[ecog], 'inline')}</span>}
          </div>
          <p className="eyebrow">
            Otázka pro komisi{c.question?.confirmed_by && ` · z nominace, ${c.question.confirmed_by}`}
          </p>
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
              {c.summary.map((s, i) => i !== ecog && <li key={i}>{S(`summary.${i}`, s, 'inline')}</li>)}
            </ul>
            {live.length > 0 && (
              <>
                <h3>
                  {more ? 'Všechna upozornění' : 'Urgentní upozornění'} ({shown.length})
                </h3>
                <ul className="facts flags-inline">
                  {shown.map((k) => {
                    const f = k.startsWith('red_flags.') ? c.red_flags[Number(k.split('.')[1])] : null
                    return (
                      <li key={k} className={f ? `sev-${f.severity}` : 'sev-missing'}>
                        {f ? <Alert /> : <MissingIcon />} {S(k, f ? f.statement : gaps.get(k)!, 'inline')}
                      </li>
                    )
                  })}
                </ul>
                {live.length > live.filter(urgent).length && (
                  <button className="link" onClick={() => setMore(!more)}>
                    {more ? 'Jen urgentní' : `+ ${live.length - live.filter(urgent).length} dalších`}
                  </button>
                )}
                {dismissed > 0 && <small className="muted"> · {dismissed} zamítnuto koordinátorem</small>}
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
            {c.decision_support.options.length ? (
              <ol className="options">
                {c.decision_support.options.map((s, i) => (
                  <li key={i}>{S(`options.${i}`, s, 'inline')}</li>
                ))}
              </ol>
            ) : (
              <Soon>Možnosti léčby s citací doporučených postupů doplní AI.</Soon>
            )}
            <h3>Klinické studie</h3>
            {c.decision_support.trials.length ? (
              <div className="trials-inline">
                <TrialList c={c} S={S} variant="inline" />
              </div>
            ) : (
              <Soon>Předběžný screening otevřených studií doplní AI.</Soon>
            )}
            {patient && patient.items.length > 0 && (
              <div className="patient-voice">
                <span className="eyebrow">
                  <Quote /> Pacient
                </span>
                {patient.items.slice(0, 2).map((s, i) => ( // the rest is in the Pacient panel
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
                {unresolved(sec.id) > 0 && <Alert />}
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
}: Omit<Props, 'go'> & { id: string; close: () => void }) {
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
        <div>
          <SectionItems sec={sec} detail={record.layout.detail} S={S} />
        </div>
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
