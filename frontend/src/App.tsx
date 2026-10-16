import { useEffect, useState } from 'react'
import { CasePage } from './CasePage'
import { Home } from './Home'
import { Intake } from './Intake'
import { User } from './icons'
import { load, type Phase, PHASES, ROLES, save } from './layout'
import { SourceDrawer } from './SourceDrawer'

/** #/ = agenda, #/new = intake (coordinator), #/case/<id>/<phase> = a case in one of its phases. */
function parse(hash: string): { id: string; phase: Phase } | null {
  const [, kind, id, phase] = hash.split('/')
  if (kind !== 'case' || !id) return null
  return { id: decodeURIComponent(id), phase: PHASES.some((p) => p.id === phase) ? (phase as Phase) : 'prep' }
}

export default function App() {
  const [hash, setHash] = useState(location.hash)
  const route = parse(hash)
  const [name, setName] = useState(() => load('mdt.user', ''))
  const [role, setRole] = useState(() => load('mdt.role', 'coordinator'))
  // signature on confirmations, notes and the decision, e.g. "LEK-P03-04 (Radiologie)"
  const user = name.trim() && `${name.trim()} (${ROLES[role] ?? role})`

  useEffect(() => save('mdt.user', name), [name])
  useEffect(() => save('mdt.role', role), [role])
  useEffect(() => {
    const onHash = () => {
      setHash(location.hash)
      scrollTo(0, 0)
    }
    addEventListener('hashchange', onHash)
    return () => removeEventListener('hashchange', onHash)
  }, [])

  return (
    <SourceDrawer>
      <header className="topbar">
        <a href="#/" className="brand">
          <span className="logo">MDT</span> Copilot
        </a>
        <nav className="topnav">
          <a href="#/" className={hash === '#/new' || route ? '' : 'on'}>
            Program
          </a>
          {role === 'coordinator' && (
            <a href="#/new" className={hash === '#/new' ? 'on' : ''}>
              + Nový případ
            </a>
          )}
        </nav>
        <span className="spacer" />
        <label className="user">
          <User />
          <input value={name} placeholder="Vaše jméno" onChange={(e) => setName(e.target.value)} aria-label="Vaše jméno" />
        </label>
        <select className="role" value={role} onChange={(e) => setRole(e.target.value)} aria-label="Role">
          {Object.entries(ROLES).map(([id, label]) => (
            <option key={id} value={id}>
              {label}
            </option>
          ))}
        </select>
      </header>

      <main>
        {route ? (
          <CasePage key={route.id} id={route.id} phase={route.phase} user={user} role={role} />
        ) : hash === '#/new' && role === 'coordinator' ? (
          <Intake />
        ) : (
          <Home role={role} />
        )}
      </main>

    </SourceDrawer>
  )
}
