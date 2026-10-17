import { useRef } from 'react'
import { Check, Person } from '../../icons'
import { SPECIALTIES } from '../../layout'
import { ROLES } from './role'

const label = (role: string) => (role ? SPECIALTIES[role] : 'Koordinátor')

/** The current role, top right; a click opens a pop-up with one bubble per role (as on Komise).
 * Picking one closes it and `onPick` leads to that role's Přehled. */
export function RolePicker({ role, onPick }: { role: string; onPick: (role: string) => void }) {
  const dialog = useRef<HTMLDialogElement>(null)
  return (
    <>
      <button className="role-btn" title="Změnit roli" onClick={() => dialog.current?.showModal()}>
        <Person /> {label(role)}
      </button>
      <dialog ref={dialog} className="dialog" onClick={(e) => e.target === dialog.current && dialog.current.close()}>
        <div className="dialog-body">
          <header>
            <h3>Vaše role</h3>
            <button className="icon-btn" onClick={() => dialog.current?.close()} aria-label="Zavřít">
              ×
            </button>
          </header>
          <div className="bubbles role-bubbles">
            {['', ...ROLES].map((r) => (
              <button
                key={r}
                className={`bubble ${r === role ? 'on' : ''}`}
                aria-pressed={r === role}
                onClick={() => {
                  dialog.current?.close()
                  onPick(r)
                }}
              >
                {r === role && <Check />} {label(r)}
              </button>
            ))}
          </div>
        </div>
      </dialog>
    </>
  )
}
