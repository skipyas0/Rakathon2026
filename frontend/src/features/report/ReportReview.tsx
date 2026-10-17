import { type ReactNode, useEffect, useRef, useState } from 'react'
import { api, type CaseRecord, type ReviewReport } from '../../api'
import { StatementView } from '../../StatementView'
import { fmtDate, fmtDateTime, SPECIALTIES } from '../../layout'
import { SourcesContext, type Shown } from '../../sources'

type Props = {
  id: string
  record: CaseRecord
  onReady: (revision: string | null, key: string) => void
  children?: ReactNode // shown at the end of the row (Potvrzení's "I've read it" checkbox)
}

export function ReportReview({ id, record, onReady, children }: Props) {
  const dialog = useRef<HTMLDialogElement>(null)
  const sourceDialog = useRef<HTMLDialogElement>(null)
  const [sources, setSources] = useState<Shown | null>(null)
  const [report, setReport] = useState<ReviewReport | null>(null)
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')
  const locked = !!record.decision.confirmed_by
  const approved = locked && !!record.decision.report_revision
  const key = JSON.stringify(record)
  const [shownKey, setShownKey] = useState('')
  const current = shownKey === key
  const callback = useRef(onReady)
  useEffect(() => { callback.current = onReady }, [onReady])
  useEffect(() => {
    callback.current(null, key)
  }, [key])

  const open = async () => {
    dialog.current?.showModal()
    if (current && report) {
      callback.current(report.revision, key)
      return
    }
    setBusy(true)
    setError('')
    try {
      const prepared = locked && record.decision.report_revision
        ? await api.approvedReport(id) : await api.prepareReport(id, record)
      setReport(prepared)
      setShownKey(key)
      if (dialog.current?.open) callback.current(prepared.revision, key)
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Zprávu nelze připravit')
      callback.current(null, key)
    } finally {
      setBusy(false)
    }
  }

  return (
    <>
      <div className="report-review-row">
        <span className="eyebrow">Zpráva ke kontrole</span>
        <button className="back" onClick={() => void open()} disabled={busy}>
          {busy ? 'Připravuji zprávu…' : 'Zobrazit zprávu'}
        </button>
        <span className="muted">
          {locked && record.decision.report_revision ? 'Schválena potvrzením závěru.' : 'Potvrzením závěru schvalujete i tuto zprávu včetně AI podkladů.'}
        </span>
        {children}
      </div>
      <dialog ref={dialog} className="dialog report-dialog" aria-label="Zpráva ke kontrole"
        onClick={(e) => e.target === dialog.current && dialog.current.close()}>
        <SourcesContext.Provider value={(shown) => {
          setSources(shown)
          sourceDialog.current?.showModal()
        }}>
        <div className="dialog-body">
          <header>
            <h2>Zpráva ke kontrole</h2>
            <button className="icon-btn" onClick={() => dialog.current?.close()} aria-label="Zavřít zprávu">×</button>
          </header>
          {busy && <p role="status">Připravuji podklady a existující AI souhrny, bez nového generování…</p>}
          {error && <p className="banner bad" role="alert">{error}</p>}
          {report && current && (
            <>
              <p>{report.label} · {report.board} · {report.mdt_date && fmtDate(report.mdt_date)}</p>
              <p className="muted">Připraveno {fmtDateTime(report.created)} · Revize {report.revision.slice(0, 12)}</p>
              <p className="banner">
                {approved ? 'Tato revize byla schválena s rozhodnutím komise.' :
                  'Zkontrolujte údaje a zdroje. Zpráva bude schválena až tlačítkem Potvrdit na obrazovce Potvrzení.'}
                {' '}Jde o demo potvrzení rolí Koordinátor/ka, nikoli ověření identity lékaře.
              </p>
              <details open>
                <summary>Úplnost a omezení ({report.warnings.length})</summary>
                <ul>{report.warnings.map((warning, i) => <li key={i}>{warning}</li>)}</ul>
              </details>
              <section>
                <h3>Komise</h3>
                <ul>{report.record.board.map((m) => (
                  <li key={m.specialty}>{m.name || 'Jméno neuvedeno'} · {SPECIALTIES[m.specialty] ?? m.specialty} · {m.supports ? 'podporuje' : 'nepodporuje'}</li>
                ))}</ul>
              </section>
              {report.sections.map((section, i) => (
                <section key={i}>
                  <h3>{section.title}</h3>
                  {section.items.length ? section.items.map((statement, j) => (
                    <StatementView key={j} s={statement} />
                  )) : <p className="muted">Neuvedeno; žádný údaj se nedoplňuje odhadem.</p>}
                </section>
              ))}
              <details>
                <summary>Původní strukturované zdroje ({report.resources.length})</summary>
                <pre>{JSON.stringify(report.resources, null, 2)}</pre>
              </details>
            </>
          )}
          <button className="back" onClick={() => dialog.current?.close()}>Zpět na potvrzení</button>
        </div>
        </SourcesContext.Provider>
      </dialog>
      <dialog ref={sourceDialog} className="dialog report-dialog" aria-label="Zdroje schvalované zprávy"
        onClick={(e) => e.target === sourceDialog.current && sourceDialog.current.close()}>
        <div className="dialog-body">
          <header>
            <h3>Zdroje schvalované zprávy</h3>
            <button className="icon-btn" onClick={() => sourceDialog.current?.close()} aria-label="Zavřít zdroje">×</button>
          </header>
          <p>{sources?.title}</p>
          <p className="muted">Zdroje z připravené revize; aktuální data se znovu nenačítají.</p>
          {sources?.sources.map((source, i) => {
            const original = report?.resources.find((resource) =>
              `${resource.resourceType}/${resource.id}` === source.reference.split('#')[0])
            return (
              <section key={i}>
                <h4>{source.title ?? source.reference}</h4>
                <code>{source.reference}</code>
                {source.excerpt && <blockquote>{source.excerpt}</blockquote>}
                {original ? <pre>{JSON.stringify(original, null, 2)}</pre> :
                  <p className="muted">Uložená citace; plný zdroj není součástí této revize.</p>}
              </section>
            )
          })}
          {!sources?.sources.length && <p className="muted">Údaj nebyl v dostupné dokumentaci nalezen.</p>}
        </div>
      </dialog>
    </>
  )
}
