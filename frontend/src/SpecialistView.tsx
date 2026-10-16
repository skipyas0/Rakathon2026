import { useState } from 'react'
import type { CaseRecord } from './api'
import type { Case } from './briefing'
import { FlagItem, MissingItem, SectionItems } from './CaseView'
import { Check } from './icons'
import { fmtDateTime, orderedSections, SECTIONS } from './layout'
import { confirmer, missing, now, renderer, visibleSections } from './render'

type Props = { c: Case; record: CaseRecord; save: (r: CaseRecord) => void; user: string; role: string }

/** Phase 1 for a specialist: the shared header, the sections the coordinator lets them see, the
 * findings assigned to them, and their opinion for the board. They confirm AI claims only in their
 * own section. CasePage only shows it to specialties on the board. */
export function SpecialistView({ c, record, save, user, role }: Props) {
  const S = renderer(record)
  const own = renderer(record, confirmer(record, save, user))
  const seen = visibleSections(record, role)
  const sections = orderedSections(c, { order: record.layout.order, hidden: [] }).filter((s) => seen.includes(s.id))
  const gaps = new Map(missing(c))
  const assigned = Object.entries(record.triage).filter(([, t]) => t.action === 'before' && t.assignee === role)
  const question = record.prep.question || c.question?.text

  return (
    <div className="phase-grid">
      <div className="phase-main">
        <section className="card">
          <p className="eyebrow">Otázka pro komisi</p>
          <h3>{question ?? 'Chybí otázka pro komisi'}</h3>
          {c.summary.map((s, i) => S(`summary.${i}`, s))}
        </section>

        {sections.map((sec) => (
          <section key={sec.id} className="card">
            <h3>
              {SECTIONS[sec.id] ?? sec.title}
              {sec.id === role && <span className="chip muted-chip">vaše odbornost</span>}
            </h3>
            <SectionItems sec={sec} detail={record.layout.detail} S={sec.id === role ? own : S} />
          </section>
        ))}
        {!sections.some((s) => s.id === role) && (
          <p className="muted small">Pro {SECTIONS[role] ?? role} podklad zatím nemá vlastní sekci.</p>
        )}
      </div>

      <aside className="phase-aside">
        <section className="card">
          <h3>Přiřazeno vám ({assigned.length})</h3>
          {assigned.length ? (
            assigned.map(([k, t]) => {
              const i = Number(k.split('.')[1])
              return (
                <div key={k} className="finding">
                  {k.startsWith('red_flags.') ? <FlagItem f={c.red_flags[i]} i={i} S={S} /> : <MissingItem k={k} s={gaps.get(k)!} S={S} />}
                  <Resolution
                    value={t.resolution}
                    disabled={!user}
                    onSave={(resolution) => save({ ...record, triage: { ...record.triage, [k]: { ...t, resolution } } })}
                  />
                </div>
              )
            })
          ) : (
            <p className="muted">Koordinátor vám nepřiřadil žádný nález.</p>
          )}
        </section>
        <Opinion record={record} role={role} user={user} save={save} />
      </aside>
    </div>
  )
}

function Resolution({ value, disabled, onSave }: { value: string; disabled: boolean; onSave: (v: string) => void }) {
  const [text, setText] = useState(value)
  return (
    <form
      className="row"
      onSubmit={(e) => {
        e.preventDefault()
        onSave(text.trim())
      }}
    >
      <input className="grow" value={text} onChange={(e) => setText(e.target.value)} placeholder="Jak byl nález vyřešen" aria-label="Vyřešení" />
      <button type="submit" disabled={disabled || text.trim() === value}>
        {value ? 'Upravit' : 'Vyřešeno'}
      </button>
    </form>
  )
}

function Opinion({ record, role, user, save }: { record: CaseRecord; role: string; user: string; save: (r: CaseRecord) => void }) {
  const note = record.notes[role]
  const [text, setText] = useState(note?.text ?? '')
  return (
    <section className="card">
      <h3>Stanovisko pro komisi</h3>
      <form
        className="note-form"
        onSubmit={(e) => {
          e.preventDefault()
          if (text.trim()) save({ ...record, notes: { ...record.notes, [role]: { text: text.trim(), by: user, at: now() } } })
        }}
      >
        <textarea value={text} onChange={(e) => setText(e.target.value)} placeholder="Co z pohledu vaší odbornosti doporučujete?" />
        <button type="submit" className="primary" disabled={!text.trim() || !user}>
          Uložit stanovisko
        </button>
        {note && (
          <small className="muted">
            <Check /> {note.by}, {fmtDateTime(note.at)}
          </small>
        )}
      </form>
    </section>
  )
}
