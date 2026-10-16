import type { ReactNode } from 'react'
import type { CaseRecord } from './api'
import type { Case, RedFlag } from './briefing'
import { Alert, Missing } from './icons'
import { fmtDate, fmtDateTime, KIND, orderedSections, SECTIONS, type Template } from './layout'
import type { Statement } from './provenance'
import type { Render } from './render'

const SEVERITY = { high: 'Vysoká závažnost', medium: 'Střední závažnost', low: 'Nízká závažnost' }

export function FlagItem({ f, i, S }: { f: RedFlag; i: number; S: Render }) {
  return (
    <div className={`flag sev-${f.severity}`}>
      <span className="sev">
        <Alert /> {SEVERITY[f.severity]}
      </span>
      {S(`red_flags.${i}`, f.statement)}
    </div>
  )
}

export function MissingItem({ k, s, S }: { k: string; s: Statement; S: Render }) {
  return (
    <div className="flag sev-missing">
      <span className="sev">
        <Missing /> Chybí údaj
      </span>
      {S(k, s)}
    </div>
  )
}

const VERDICT = { eligible: 'Potenciálně vhodný', ineligible: 'Nevhodný', missing_data: 'Chybí údaj' }

export function TrialList({ c, S, variant = 'card' }: { c: Case; S: Render; variant?: 'card' | 'inline' }) {
  return c.decision_support.trials.map((t, ti) => (
    <div key={t.trial} className="trial">
      <div className="trial-head">
        <strong>{t.trial}</strong>
        <span className={`chip verdict-${t.verdict}`}>{VERDICT[t.verdict]}</span>
      </div>
      {variant === 'card' && t.criteria.map((s, i) => S(`trials.${ti}.${i}`, s))}
    </div>
  ))
}

const Block = ({ title, children }: { title: string; children: ReactNode }) => (
  <section className="card">
    <h3>{title}</h3>
    {children}
  </section>
)

/** Everything in the briefing, for the after-meeting overview and the printed record. */
export function CaseDetail({ c, record, template, S }: { c: Case; record: CaseRecord; template: Template; S: Render }) {
  const empty = <p className="muted">Bez položek.</p>
  return (
    <div className="detail">
      <Block title="Souhrn">{c.summary.map((s, i) => S(`summary.${i}`, s))}</Block>
      <Block title="Upozornění">
        {c.red_flags.length ? c.red_flags.map((f, i) => <FlagItem key={i} f={f} i={i} S={S} />) : empty}
      </Block>
      <Block title="Časová osa">
        <ol className="tl-list">
          {c.timeline.map((e, i) => (
            <li key={i}>
              <time>{fmtDate(e.date)}</time>
              <span className="muted">{KIND[e.kind]}</span>
              {S(`timeline.${i}`, e.statement, 'inline')}
            </li>
          ))}
        </ol>
      </Block>
      {orderedSections(c, template).map((sec) => {
        const note = record.notes[sec.id]
        return (
          <Block key={sec.id} title={SECTIONS[sec.id] ?? sec.title}>
            {sec.items.map((s, i) => S(`sections.${sec.id}.${i}`, s))}
            {note && (
              <div className="note">
                <span className="eyebrow">Stanovisko odbornosti</span>
                <p>{note.text}</p>
                <small className="muted">
                  {note.by}, {fmtDateTime(note.at)}
                </small>
              </div>
            )}
          </Block>
        )
      })}
      <Block title="Možnosti léčby dle doporučených postupů">
        {c.decision_support.options.length ? c.decision_support.options.map((s, i) => S(`options.${i}`, s)) : empty}
      </Block>
      <Block title="Klinické studie">{c.decision_support.trials.length ? <TrialList c={c} S={S} /> : empty}</Block>
    </div>
  )
}
