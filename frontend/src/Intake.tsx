import { useState } from 'react'
import { api, type IntakeKind } from './api'
import { Doc } from './icons'

const KINDS: Record<IntakeKind, { label: string; desc: string; accept: string; soon?: boolean }> = {
  fhir: { label: 'FHIR soubor', desc: 'Kompletní záznam pacienta jako FHIR Bundle (.json).', accept: '.json,application/json' },
  // ponytail: enable once the backend extracts PDFs (POST /api/intake answers 501 until then)
  pdf: {
    label: 'Dokumenty PDF',
    desc: 'Zprávy, nálezy a dotazníky od externího lékaře, jeden soubor na záznam.',
    accept: '.pdf,application/pdf',
    soon: true,
  },
}

const toBase64 = (f: File) =>
  new Promise<string>((resolve, reject) => {
    const r = new FileReader()
    r.onload = () => resolve(String(r.result).split(',')[1] ?? '')
    r.onerror = () => reject(r.error)
    r.readAsDataURL(f)
  })

/** Coordinator: add a case from a FHIR file, then continue with its preparation. */
export function Intake() {
  const [kind, setKind] = useState<IntakeKind>('fhir')
  const [files, setFiles] = useState<File[]>([])
  const [error, setError] = useState('')
  const [busy, setBusy] = useState(false)
  const [over, setOver] = useState(false)

  const pick = (list: FileList | null) => {
    if (!list) return
    setFiles(kind === 'fhir' ? [...list].slice(0, 1) : [...list])
    setError('')
  }
  const submit = async () => {
    setBusy(true)
    setError('')
    try {
      const { case_id } = await api.intake(kind, await Promise.all(files.map(async (f) => ({ name: f.name, data: await toBase64(f) }))))
      location.hash = `#/case/${encodeURIComponent(case_id)}/prep`
    } catch (e) {
      setError((e as Error).message)
      setBusy(false)
    }
  }

  return (
    <div className="page intake">
      <header className="home-head">
        <p className="eyebrow">Koordinátor</p>
        <h1>Nový případ</h1>
        <p className="muted">Nahrajte podklady pacienta. Případ se přidá do programu a otevře se jeho příprava.</p>
      </header>

      <section className="card">
        <fieldset className="kind-choice">
          <legend>Zdroj podkladů</legend>
          {(Object.keys(KINDS) as IntakeKind[]).map((k) => (
            <label key={k} className={kind === k ? 'on' : KINDS[k].soon ? 'soon' : ''}>
              <input
                type="radio"
                name="kind"
                disabled={KINDS[k].soon}
                checked={kind === k}
                onChange={() => {
                  setKind(k)
                  setFiles([])
                }}
              />
              <strong>
                {KINDS[k].label} {KINDS[k].soon && <span className="chip muted-chip">Připravujeme</span>}
              </strong>
              <span className="muted small">{KINDS[k].desc}</span>
            </label>
          ))}
        </fieldset>

        <label
          className={`dropzone${over ? ' over' : ''}`}
          onDragOver={(e) => {
            e.preventDefault()
            setOver(true)
          }}
          onDragLeave={() => setOver(false)}
          onDrop={(e) => {
            e.preventDefault()
            setOver(false)
            pick(e.dataTransfer.files)
          }}
        >
          <input type="file" accept={KINDS[kind].accept} multiple={kind === 'pdf'} onChange={(e) => pick(e.target.files)} />
          <strong>Přetáhněte soubory sem</strong>
          <span className="muted small">nebo klikněte pro výběr</span>
        </label>

        {files.length > 0 && (
          <ul className="file-list">
            {files.map((f) => (
              <li key={f.name}>
                <Doc /> {f.name}
              </li>
            ))}
          </ul>
        )}
        {error && <div className="banner bad">{error}</div>}
        <button className="primary" disabled={!files.length || busy} onClick={submit}>
          {busy ? 'Nahrávám…' : 'Nahrát a otevřít přípravu'}
        </button>
      </section>
    </div>
  )
}
