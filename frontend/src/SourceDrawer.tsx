import { type ReactNode, useRef, useState } from 'react'
import { Doc, Robot } from './icons'
import { fmtDate } from './layout'
import { type Shown, SourcesContext, sourceType } from './sources'

/** The exact reference, and the whole source record on demand (the excerpt above is only the
 * cited passage). guideline:/trial: references have no record behind them. */
function SourceFoot({ reference }: { reference: string }) {
  const [text, setText] = useState<string | null>(null)
  const ref = reference.split('#')[0]
  const hasRecord = /^[A-Z][A-Za-z]+\/[\w.-]+$/.test(ref)
  const load = () =>
    fetch(`/api/sources/${ref}`)
      .then((r) => (r.ok ? r.json() : { text: 'Celý záznam není v dostupných datech.' }))
      .then((d) => setText(d.text))
  return (
    <>
      <div className="source-foot">
        <code>{reference}</code>
        {hasRecord && text === null && (
          <button className="link" onClick={load}>
            Zobrazit celý záznam
          </button>
        )}
      </div>
      {text !== null && <div className="full-text">{text}</div>}
    </>
  )
}

export function SourceDrawer({ children }: { children: ReactNode }) {
  const dialog = useRef<HTMLDialogElement>(null)
  const [shown, setShown] = useState<Shown | null>(null)
  const open = (s: Shown) => {
    setShown(s)
    dialog.current?.showModal()
  }
  return (
    <SourcesContext.Provider value={open}>
      {children}
      <dialog
        ref={dialog}
        className="drawer"
        onClick={(e) => e.target === dialog.current && dialog.current.close()} // click on backdrop
      >
        {shown && (
          <div className="drawer-body">
            <header>
              <span className="eyebrow">Zdroje tvrzení</span>
              <button className="icon-btn" onClick={() => dialog.current?.close()} aria-label="Zavřít">
                ×
              </button>
            </header>
            <h2>{shown.title}</h2>
            {shown.ai && (
              <p className="ai-note">
                <Robot /> Návrh AI ({shown.ai}). Ověřte proti zdrojům níže.
              </p>
            )}
            {shown.sources.length === 0 && <p className="muted">Údaj nebyl v dostupné dokumentaci nalezen.</p>}
            <ul className="source-list">
              {shown.sources.map((s, i) => (
                <li key={i}>
                  <div className="source-head">
                    <Doc /> <strong>{sourceType(s.reference)}</strong>
                    <span className="muted">{[s.date && fmtDate(s.date), s.author].filter(Boolean).join(' · ')}</span>
                  </div>
                  {s.title && <p className="source-title">{s.title}</p>}
                  {s.excerpt && (
                    <blockquote>
                      <mark>{s.excerpt}</mark>
                    </blockquote>
                  )}
                  <SourceFoot key={s.reference} reference={s.reference} />
                </li>
              ))}
            </ul>
          </div>
        )}
      </dialog>
    </SourcesContext.Provider>
  )
}
