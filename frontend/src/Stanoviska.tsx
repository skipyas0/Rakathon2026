import { useRef, useState } from 'react'
import { api, type CaseRecord } from './api'
import type { Case } from './briefing'
import { ROLES } from './features/roles/role'
import { Alert, Check } from './icons'
import { fmtDateTime, SPECIALTIES } from './layout'
import { renderer } from './render'

type Props = { c: Case; record: CaseRecord; onChange: (r: CaseRecord) => void }

/** One bubble per board specialty: green = supports the proposed postup, red = doesn't. A click
 * opens that specialty's stanovisko, where the stance can be switched until the conclusion is
 * locked. The stanovisko is the specialist's own (features/roles: generated or written), empty until
 * then; ponytail: a specialty without a specialist journey (not in ROLES) shows an example ("ukázka"). */
export function Stanoviska({ c, record, onChange }: Props) {
  const S = renderer(record)
  const locked = !!record.decision.confirmed_by
  const [role, setRole] = useState<string | null>(null)
  const [error, setError] = useState('')
  const dialog = useRef<HTMLDialogElement>(null)
  const member = record.board.find((m) => m.specialty === role)
  const label = (s: string) => SPECIALTIES[s] ?? s
  const items = c.sections.find((s) => s.id === role)?.items ?? []
  const own = role ? record.stanoviska[role] : undefined
  // stances are written only through the specialist's endpoint, so the coordinator never overwrites one
  const setSupports = (supports: boolean) =>
    member &&
    api.updateStanovisko(c.id, member.specialty, { supports }).then(
      (r) => (onChange(r), setError('')),
      (e: Error) => setError(e.message),
    )

  return (
    <>
      <div className="bubbles small-bubbles stanoviska">
        <span className="eyebrow">Stanoviska</span>
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
            {error && <div className="banner bad">{error}</div>}
            <div className="segmented-stance" role="group" aria-label="Postoj k navrženému postupu">
              <button className={member.supports ? 'yes on' : 'yes'} disabled={locked} onClick={() => void setSupports(true)}>
                <Check /> Podporuje
              </button>
              <button className={member.supports ? 'no' : 'no on'} disabled={locked} onClick={() => void setSupports(false)}>
                <Alert /> Nepodporuje
              </button>
            </div>
            <section className="question-card stanovisko">
              <p className="eyebrow">Stanovisko</p>
              {own ? (
                <>
                  <p>{S(`stanoviska.${member.specialty}`, own, 'inline')}</p>
                  {own.confirmed_by && (
                    <p className="muted">
                      {own.confirmed_by}
                      {own.confirmed_at && `, ${fmtDateTime(own.confirmed_at)}`}
                    </p>
                  )}
                </>
              ) : ROLES.includes(member.specialty) ? (
                <p className="muted">Odborník zatím stanovisko nezadal.</p>
              ) : (
                <>
                  <p className="verdict warn">
                    <Alert /> Odbornost zatím nemá vlastní pohled, text je jen ukázka.
                  </p>
                  <p>
                    <span className="chip muted-chip">ukázka</span>{' '}
                    {member.supports
                      ? `Z pohledu odbornosti ${label(member.specialty)} bez námitek k navrženému postupu.`
                      : `Z pohledu odbornosti ${label(member.specialty)} navržený postup nepodporuje.`}
                  </p>
                </>
              )}
            </section>
            {items.length > 0 && (
              <>
                <h4 className="eyebrow">Podklady · {label(member.specialty)}</h4>
                <ul className="plain">
                  {items.map((s, i) => (
                    <li key={i}>{S(`sections.${member.specialty}.${i}`, s, 'inline')}</li>
                  ))}
                </ul>
              </>
            )}
          </div>
        )}
      </dialog>
    </>
  )
}
