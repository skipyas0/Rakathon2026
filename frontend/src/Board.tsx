import { useState } from 'react'
import type { CaseRecord, Member } from './api'
import type { Case } from './briefing'
import { MIN_SPECIALTIES, SPECIALTIES, specialtyOf } from './layout'

type Props = { c: Case; record: CaseRecord; save: (r: CaseRecord) => void }

/** Coordinator: who sits on the board for this meeting, and who chairs it. */
export function Board({ c, record, save }: Props) {
  const [draft, setDraft] = useState<Member[]>(record.board)
  const dirty = JSON.stringify(draft) !== JSON.stringify(record.board)
  const specialties = new Set(draft.map((m) => m.specialty).filter(Boolean)).size
  const set = (i: number, m: Partial<Member>) => setDraft(draft.map((x, j) => (j === i ? { ...x, ...m } : x)))
  const adopt = () =>
    setDraft(c.previous_board.map((m) => ({ name: m.name, specialty: specialtyOf(m.role), chair: m.chair })))

  return (
    <section className="card board">
      <h3>Komise pro toto zasedání</h3>
      {c.previous_board.length > 0 && (
        <p className="muted small">
          Minulé MDT: {c.previous_board.map((m) => `${m.name || '(neuvedeno)'} – ${m.role}${m.chair ? ', předseda' : ''}`).join(' · ')}{' '}
          <button className="link" onClick={adopt}>
            Převzít složení
          </button>
        </p>
      )}
      <table className="board-table">
        <thead>
          <tr>
            <th>Jméno</th>
            <th>Odbornost</th>
            <th>Předsedá</th>
            <th />
          </tr>
        </thead>
        <tbody>
          {draft.map((m, i) => (
            <tr key={i}>
              <td>
                <input aria-label="Jméno" value={m.name} placeholder="Doplňte jméno" onChange={(e) => set(i, { name: e.target.value })} />
              </td>
              <td>
                <select aria-label="Odbornost" value={m.specialty} onChange={(e) => set(i, { specialty: e.target.value })}>
                  {!m.specialty && <option value="">— vyberte —</option>}
                  {Object.entries(SPECIALTIES).map(([id, label]) => (
                    <option key={id} value={id}>
                      {label}
                    </option>
                  ))}
                </select>
              </td>
              <td>
                <input
                  type="radio"
                  name="chair"
                  aria-label="Předsedá"
                  checked={m.chair}
                  onChange={() => setDraft(draft.map((x, j) => ({ ...x, chair: j === i })))}
                />
              </td>
              <td>
                <button className="link" onClick={() => setDraft(draft.filter((_, j) => j !== i))}>
                  Odebrat
                </button>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
      <div className="row">
        <button onClick={() => setDraft([...draft, { name: '', specialty: '', chair: false }])}>+ Přidat člena</button>
        <span className={`small ${specialties >= MIN_SPECIALTIES ? 'muted' : 'warn-text'}`}>
          {specialties} odbornosti (minimum {MIN_SPECIALTIES})
        </span>
        <span className="spacer" />
        <button className="primary" disabled={!dirty || draft.some((m) => !m.specialty)} onClick={() => save({ ...record, board: draft })}>
          Uložit komisi
        </button>
      </div>
    </section>
  )
}
