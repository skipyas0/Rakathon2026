import type { CaseRecord } from './api'
import type { Case } from './briefing'
import { Check } from './icons'
import { fmtDateTime, SECTIONS } from './layout'
import { isPending } from './render'

type Props = { c: Case; record: CaseRecord }

/** Coordinator: how far each board member is with their part of the preparation. */
export function Specialists({ c, record }: Props) {
  if (!record.board.length) return <p className="muted">Nejdřív sestavte komisi.</p>
  return (
    <section className="card">
      <h3>Příprava odborníků</h3>
      <div className="table-scroll">
        <table className="matrix progress">
          <thead>
            <tr>
              <th>Člen komise</th>
              <th>Návrhy AI ve vlastní sekci</th>
              <th>Přiřazené nálezy</th>
              <th>Stanovisko</th>
            </tr>
          </thead>
          <tbody>
            {record.board.map((m, i) => {
              const sec = c.sections.find((s) => s.id === m.specialty)
              const ai = sec?.items.map((s, j) => [`sections.${sec.id}.${j}`, s] as const).filter(([, s]) => s.origin === 'ai') ?? []
              const confirmed = ai.filter(([k, s]) => !isPending(record, k, s)).length
              const assigned = Object.values(record.triage).filter((t) => t.action === 'before' && t.assignee === m.specialty)
              const resolved = assigned.filter((t) => t.resolution.trim()).length
              const note = record.notes[m.specialty]
              return (
                <tr key={i}>
                  <th>
                    {m.name || '(bez jména)'} <span className="muted">· {SECTIONS[m.specialty] ?? m.specialty}</span>
                    {m.chair && <span className="chip muted-chip">předsedá</span>}
                  </th>
                  <td>{!sec ? <span className="muted">bez vlastní sekce</span> : ai.length ? `${confirmed} / ${ai.length}` : '–'}</td>
                  <td>{assigned.length ? `${resolved} / ${assigned.length} vyřešeno` : '–'}</td>
                  <td>
                    {note ? (
                      <span className="confirmed">
                        <Check /> {note.by}, {fmtDateTime(note.at)}
                      </span>
                    ) : (
                      <span className="muted">zatím ne</span>
                    )}
                  </td>
                </tr>
              )
            })}
          </tbody>
        </table>
      </div>
    </section>
  )
}
