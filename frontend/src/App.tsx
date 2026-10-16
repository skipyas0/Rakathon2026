import { useEffect, useRef, useState } from 'react'
import { CasePage } from './CasePage'
import { Home } from './Home'
import { Settings, User } from './icons'
import { DEFAULT_TEMPLATE, load, type Phase, PHASES, save, SECTIONS, type Template } from './layout'
import { SourceDrawer } from './SourceDrawer'

/** #/ = agenda, #/case/<id>/<phase> = a case in one of its three phases. */
function parse(hash: string): { id: string; phase: Phase } | null {
  const [, kind, id, phase] = hash.split('/')
  if (kind !== 'case' || !id) return null
  return { id: decodeURIComponent(id), phase: PHASES.some((p) => p.id === phase) ? (phase as Phase) : 'prep' }
}

export default function App() {
  const [route, setRoute] = useState(() => parse(location.hash))
  const [user, setUser] = useState(() => load('mdt.user', ''))
  const [template, setTemplate] = useState<Template>(() => load('mdt.template', DEFAULT_TEMPLATE))
  const settings = useRef<HTMLDialogElement>(null)

  useEffect(() => save('mdt.user', user), [user])
  useEffect(() => save('mdt.template', template), [template])
  useEffect(() => {
    const onHash = () => {
      setRoute(parse(location.hash))
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
        <span className="spacer" />
        <label className="user">
          <User />
          <input value={user} placeholder="Vaše jméno (předseda)" onChange={(e) => setUser(e.target.value)} aria-label="Vaše jméno" />
        </label>
        <button className="icon-btn" onClick={() => settings.current?.showModal()} aria-label="Šablona komise" title="Šablona komise">
          <Settings />
        </button>
      </header>

      <main>{route ? <CasePage key={route.id} id={route.id} phase={route.phase} user={user} template={template} /> : <Home />}</main>

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
