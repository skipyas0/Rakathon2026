import { SPECIALTIES } from '../../layout'
import { ROLES, setRole } from './role'

/** #/role: one tile per role; a click picks it and returns to Přehled. */
export function RolePicker({ current }: { current: string }) {
  return (
    <div className="page journey">
      <h1>Vaše role</h1>
      <div className="tiles">
        {['', ...ROLES].map((r) => (
          <button key={r} className={`tile ${r === current ? 'on' : ''}`} aria-pressed={r === current} onClick={() => (setRole(r), (location.hash = '#/'))}>
            {r ? SPECIALTIES[r] : 'Koordinátor'}
          </button>
        ))}
      </div>
    </div>
  )
}
