import type { CaseRecord } from './api'
import type { Case } from './briefing'
import { orderedSections, SECTIONS } from './layout'
import { visibleSections } from './render'

type Props = { c: Case; record: CaseRecord; save: (r: CaseRecord) => void }

/** Coordinator: which sections each specialty on the board sees in its own view. */
export function Visibility({ c, record, save }: Props) {
  const specialties = [...new Set(record.board.map((m) => m.specialty))]
  const sections = orderedSections(c, record.layout)
  const toggle = (spec: string, id: string) => {
    const seen = visibleSections(record, spec)
    const next = seen.includes(id) ? seen.filter((x) => x !== id) : [...seen, id]
    save({ ...record, visibility: { ...record.visibility, [spec]: next } })
  }

  return (
    <section className="card">
      <h3>Kdo co vidí</h3>
      <p className="muted small">
        Otázku, souhrn, upozornění a časovou osu vidí všichni. Sekce odborností vidí každý ve svém pohledu podle této tabulky
        (výchozí: vlastní sekce a pacient).
      </p>
      {specialties.length ? (
        <div className="table-scroll">
          <table className="matrix">
            <thead>
              <tr>
                <th />
                {sections.map((s) => (
                  <th key={s.id}>{SECTIONS[s.id] ?? s.title}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {specialties.map((spec) => (
                <tr key={spec}>
                  <th>{SECTIONS[spec] ?? spec}</th>
                  {sections.map((s) => (
                    <td key={s.id}>
                      <input
                        type="checkbox"
                        aria-label={`${SECTIONS[spec] ?? spec} vidí ${SECTIONS[s.id] ?? s.title}`}
                        checked={visibleSections(record, spec).includes(s.id)}
                        onChange={() => toggle(spec, s.id)}
                      />
                    </td>
                  ))}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      ) : (
        <p className="muted">Nejdřív sestavte komisi.</p>
      )}
    </section>
  )
}
