import { useEffect, useRef, useState } from 'react'
import { CasePage } from './CasePage'
import { Home } from './Home'
import { Intake } from './Intake'
import { Settings, User } from './icons'
import { DEFAULT_TEMPLATE, load, type Phase, PHASES, ROLES, save, SECTIONS, type Template } from './layout'
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
  const [template, setTemplate] = useState<Template>(() => load('mdt.template', DEFAULT_TEMPLATE))
  const settings = useRef<HTMLDialogElement>(null)
  // signature on confirmations, notes and the decision, e.g. "LEK-P03-04 (Radiologie)"
  const user = name.trim() && `${name.trim()} (${ROLES[role] ?? role})`

  useEffect(() => save('mdt.user', name), [name])
  useEffect(() => save('mdt.role', role), [role])
  useEffect(() => save('mdt.template', template), [template])
  useEffect(() => {
    const onHash = () => {
      setHash(location.hash)
      scrollTo(0, 0)
    }
    addEventListener('hashchange', onHash)
    return () => removeEventListener('hashchange', onHash)
  }, [])

  const move = (id: string, by: number) => {
    const order = [...template.order]
    const i = order.indexOf(id)
    if (i + by < 0 || i + by >= order.length) return
    ;[order[i], order[i + by]] = [order[i + by], order[i]]
    setTemplate({ ...template, order })
  }
  const toggle = (id: string) =>
    setTemplate({
      ...template,
      hidden: template.hidden.includes(id) ? template.hidden.filter((x) => x !== id) : [...template.hidden, id],
    })

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
        <button className="icon-btn" onClick={() => settings.current?.showModal()} aria-label="Šablona komise" title="Šablona komise">
          <Settings />
        </button>
      </header>

      <main>
        {route ? (
          <CasePage key={route.id} id={route.id} phase={route.phase} user={user} template={template} />
        ) : hash === '#/new' && role === 'coordinator' ? (
          <Intake />
        ) : (
          <Home />
        )}
      </main>

      <dialog ref={settings} className="modal" onClick={(e) => e.target === settings.current && settings.current.close()}>
        <div className="modal-body">
          <header className="panel-head">
            <h2>Šablona komise</h2>
            <button className="icon-btn" onClick={() => settings.current?.close()} aria-label="Zavřít">
              ×
            </button>
          </header>
          <p className="muted small">Které odbornosti se zobrazují a v jakém pořadí (na zasedání i v přehledu).</p>
          <ol className="template">
            {template.order.map((id, i) => (
              <li key={id}>
                <label className="inline">
                  <input type="checkbox" checked={!template.hidden.includes(id)} onChange={() => toggle(id)} /> {SECTIONS[id] ?? id}
                </label>
                <button className="icon-btn" onClick={() => move(id, -1)} disabled={i === 0} aria-label="Posunout nahoru">
                  ↑
                </button>
                <button className="icon-btn" onClick={() => move(id, 1)} disabled={i === template.order.length - 1} aria-label="Posunout dolů">
                  ↓
                </button>
              </li>
            ))}
          </ol>
          <button onClick={() => setTemplate(DEFAULT_TEMPLATE)}>Obnovit výchozí</button>
        </div>
      </dialog>
    </SourceDrawer>
  )
}
