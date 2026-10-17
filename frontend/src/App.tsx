import { useEffect, useState } from 'react'
import { Intake } from './Intake'
import { Journey } from './Journey'
import { type Step, STEPS } from './layout'
import { Overview } from './Overview'
import { SourceDrawer } from './SourceDrawer'

/** #/ = Přehled, #/new = upload (step 1), #/case/<id>/<step> = the journey through one case. */
function parse(hash: string): { id: string; step: Step } | null {
  const [, kind, id, step] = hash.split('/')
  if (kind !== 'case' || !id) return null
  return { id: decodeURIComponent(id), step: STEPS.some((s) => s.id === step) ? (step as Step) : 'patient' }
}

export default function App() {
  const [hash, setHash] = useState(location.hash)
  const route = parse(hash)
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
          <a href="#/" className={hash === '#/new' || route ? '' : 'on'}>
            Přehled
          </a>
          <a href="#/new" className={hash === '#/new' ? 'on' : ''}>
            + Nový případ
          </a>
        </nav>
      </header>

      <main>
        {route ? (
          <Journey key={route.id} id={route.id} step={route.step} />
        ) : hash === '#/new' ? (
          <Intake />
        ) : (
          <Overview />
        )}
      </main>
    </SourceDrawer>
  )
}
