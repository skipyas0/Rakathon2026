import { useEffect, useState } from 'react'
import { api, type CaseRecord, type History as HistoryData } from './api'
import { type Case, statements } from './briefing'
import { Doc } from './icons'
import { fmtDate, fmtDateTime, INTENTS, SECTIONS, STATUS_LABEL } from './layout'
import { useSources } from './sources'

/** The patient's MDTs, read-only: previous MDT records from the health record, meetings recorded
 * here, and who signed what in this meeting (governance; nothing here can be edited). */
export function History({ c, record }: { c: Case; record: CaseRecord }) {
  const show = useSources()
  const [h, setH] = useState<HistoryData | null>(null)
  const [error, setError] = useState('')
  useEffect(() => {
    api.history(c.id).then(setH, (e: Error) => setError(e.message))
  }, [c.id])

  if (error) return <div className="banner bad">{error}</div>
  if (!h) return <p className="muted">Načítám…</p>
  return (
    <div className="history">
      <section className="card">
        <h3>Zasedání v aplikaci</h3>
        <ul className="history-list">
          {h.meetings.map((m) => (
            <li key={m.id}>
              <a href={`#/case/${encodeURIComponent(m.id)}/followup`}>
                <strong>MDT {m.mdt_date ? fmtDate(m.mdt_date) : '(bez termínu)'}</strong>
              </a>{' '}
              <span className="muted">· {STATUS_LABEL[m.status]}</span>
              {m.id === c.id && <span className="chip muted-chip">toto zasedání</span>}
              {m.decision.confirmed_by ? (
                <p>
                  {m.decision.intent && <strong>{INTENTS[m.decision.intent].label}: </strong>}
                  {m.decision.plan}
                  <br />
                  <small className="muted">
                    Konsenzus: {m.decision.consent.join(', ')} · zapsal {m.decision.confirmed_by}
                    {m.decision.confirmed_at && `, ${fmtDateTime(m.decision.confirmed_at)}`} · uzamčeno
                  </small>
                </p>
              ) : (
                <p className="muted small">Závěr zatím není uzamčen.</p>
              )}
            </li>
          ))}
        </ul>
      </section>

      <section className="card">
        <h3>Předchozí MDT ve zdravotní dokumentaci</h3>
        {h.documents.length ? (
          h.documents.map((d) => (
            <details key={d.reference} className="history-doc">
              <summary>
                <strong>{d.title}</strong> <span className="muted">· {d.date && fmtDate(d.date)}{d.author && ` · ${d.author}`}</span>
              </summary>
              <dl>
                {d.sections.map((s) => (
                  <div key={s.title}>
                    <dt>{s.title}</dt>
                    <dd>{s.text}</dd>
                  </div>
                ))}
              </dl>
              <button className="link" onClick={() => show({ title: d.title, sources: [{ reference: d.reference, title: d.title, date: d.date }] })}>
                <Doc /> Zdrojový záznam
              </button>
            </details>
          ))
        ) : (
          <p className="muted">Ve zdravotní dokumentaci není záznam o předchozím MDT.</p>
        )}
      </section>

      <section className="card">
        <h3>Auditní stopa tohoto zasedání</h3>
        <ol className="audit">
          {audit(c, record).map((e, i) => (
            <li key={i}>
              <time>{fmtDateTime(e.at)}</time> <strong>{e.by}</strong> <span>{e.what}</span>
            </li>
          ))}
        </ol>
      </section>
    </div>
  )
}

/** Every signed step in the record, newest first. Built from the signatures the record already
 * carries. ponytail: no edit history of drafts; add a server-side log if that's ever needed. */
function audit(c: Case, r: CaseRecord) {
  const text = new Map(statements(c))
  const events: { at: string; by: string; what: string }[] = [
    ...Object.entries(r.confirmations).map(([k, x]) => ({ ...x, what: `potvrdil(a): ${text.get(k)?.text ?? k}` })),
    ...Object.entries(r.triage).map(([k, t]) => ({ at: t.at, by: t.by, what: `roztřídil(a) nález: ${text.get(k)?.text ?? k}` })),
    ...Object.entries(r.notes).map(([spec, n]) => ({ at: n.at, by: n.by, what: `stanovisko za ${SECTIONS[spec] ?? spec}` })),
  ]
  if (r.prep.prepared_by && r.prep.prepared_at) events.push({ at: r.prep.prepared_at, by: r.prep.prepared_by, what: 'připravil(a) k projednání' })
  if (r.decision.confirmed_by && r.decision.confirmed_at)
    events.push({ at: r.decision.confirmed_at, by: r.decision.confirmed_by, what: 'uzamkl(a) závěr (konsenzus všech přítomných)' })
  if (r.patient_stance) events.push({ ...r.patient_stance, what: 'zaznamenal(a) stanovisko pacienta' })
  return events.sort((a, b) => b.at.localeCompare(a.at))
}
