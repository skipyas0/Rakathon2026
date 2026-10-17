import { useRef, useState } from 'react'
import type { CaseRecord } from './api'
import type { Case } from './briefing'
import { Alert, Check } from './icons'
import { SPECIALTIES } from './layout'
import { renderer } from './render'

type Props = { c: Case; record: CaseRecord; save: (r: CaseRecord) => Promise<boolean> }

/** One bubble per board specialty: green = supports the proposed postup, red = doesn't. A click
 * opens that specialty's stanovisko, where the stance can be switched until the conclusion is
 * locked. The opinion is the agent's verdict for that specialty (the section item agent.py writes as
 * "Stanovisko (…): …"); ponytail: without one, an example ("ukázka") stands in. */
export function Stanoviska({ c, record, save }: Props) {
  const S = renderer(record)
  const locked = !!record.decision.confirmed_by
  const [role, setRole] = useState<string | null>(null)
  const dialog = useRef<HTMLDialogElement>(null)
  const member = record.board.find((m) => m.specialty === role)
  const label = (s: string) => SPECIALTIES[s] ?? s
  const items = [...(c.sections.find((s) => s.id === role)?.items.entries() ?? [])]
  const verdict = items.find(([, s]) => s.text.startsWith('Stanovisko ('))
  const setSupports = (supports: boolean) =>
    void save({ ...record, board: record.board.map((m) => (m.specialty === role ? { ...m, supports } : m)) })

  return (
    <>
      <div className="bubbles small-bubbles stanoviska">
        <span className="muted">Stanoviska:</span>
        {record.board.map((m) => (
          <button
            key={m.specialty}
            className={`bubble ${m.supports ? 'yes' : 'no'}`}
            onClick={() => {
              setRole(m.specialty)
              dialog.current?.showModal()
            }}
          >
            {m.supports ? <Check /> : <Alert />} {label(m.specialty)}
          </button>
        ))}
      </div>
      <dialog ref={dialog} className="dialog" onClick={(e) => e.target === dialog.current && dialog.current.close()}>
        {member && (
          <div className="dialog-body">
            <header>
              <h3>Stanovisko · {label(member.specialty)}</h3>
              <button className="icon-btn" onClick={() => dialog.current?.close()} aria-label="Zavřít">
                ×
              </button>
            </header>
            <div className="segmented-stance" role="group" aria-label="Postoj k navrženému postupu">
              <button className={member.supports ? 'yes on' : 'yes'} disabled={locked} onClick={() => setSupports(true)}>
                <Check /> Podporuje
              </button>
              <button className={member.supports ? 'no' : 'no on'} disabled={locked} onClick={() => setSupports(false)}>
                <Alert /> Nepodporuje
              </button>
            </div>
            {verdict ? (
              <p>{S(`sections.${member.specialty}.${verdict[0]}`, verdict[1], 'inline')}</p>
            ) : (
              <p>
                <span className="chip muted-chip">ukázka</span>{' '}
                {member.supports
                  ? `Z pohledu odbornosti ${label(member.specialty)} bez námitek k navrženému postupu.`
                  : `Z pohledu odbornosti ${label(member.specialty)} navržený postup nepodporuje.`}
              </p>
            )}
            <ul className="plain">
              {items
                .filter(([i]) => i !== verdict?.[0])
                .map(([i, s]) => (
                  <li key={i}>{S(`sections.${member.specialty}.${i}`, s, 'inline')}</li>
                ))}
            </ul>
          </div>
        )}
      </dialog>
    </>
  )
}
