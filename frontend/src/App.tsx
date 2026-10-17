import { useEffect, useState } from 'react'
import { getRole, SPECIALIST_STEPS } from './features/roles/role'
import { RolePicker } from './features/roles/RolePicker'
import { SpecialistJourney } from './features/roles/SpecialistJourney'
import { Person } from './icons'
import { Intake } from './Intake'
import { Journey } from './Journey'
import { SPECIALTIES, STEPS } from './layout'
import { Overview } from './Overview'
import { SourceDrawer } from './SourceDrawer'

/** #/ = Přehled, #/new = upload (step 1), #/role = the role picker, #/case/<id>/<step> = the
 * journey through one case (the coordinator's, or the specialist's when a specialist role is set). */
function parse(hash: string): { id: string; step: string } | null {
  const [, kind, id, step = ''] = hash.split('/')
  if (kind !== 'case' || !id) return null
  return { id: decodeURIComponent(id), step }
}

/** The step if the journey has it, else its first screen with content (Pacient). */
const stepIn = <T extends string>(steps: readonly { id: T }[], step: string) => steps.find((s) => s.id === step)?.id ?? ('patient' as T)

export default function App() {
  const [hash, setHash] = useState(location.hash)
  const route = parse(hash)
  const role = getRole() // read on every render: the picker saves it and changes the hash
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
          <span className="logo">MDT</span> <span className="brand-name">Copilot</span>
        </a>
        <nav className="topnav">
          <a href="#/" className={hash === '#/new' || hash === '#/role' || route ? '' : 'on'}>
            Přehled
          </a>
          {!role && (
            <a href="#/new" className={hash === '#/new' ? 'on' : ''}>
              + Nový případ
            </a>
          )}
        </nav>
        <a href="#/role" className={`role-btn ${hash === '#/role' ? 'on' : ''}`} title="Změnit roli">
          <Person /> {role ? SPECIALTIES[role] : 'Koordinátor'}
        </a>
      </header>

      <main>
        {route ? (
          role ? (
            <SpecialistJourney key={route.id} id={route.id} step={stepIn(SPECIALIST_STEPS, route.step)} role={role} />
          ) : (
            <Journey key={route.id} id={route.id} step={stepIn(STEPS, route.step)} />
          )
        ) : hash === '#/role' ? (
          <RolePicker current={role} />
        ) : hash === '#/new' && !role ? (
          <Intake />
        ) : (
          <Overview role={role} />
        )}
      </main>
    </SourceDrawer>
  )
}
