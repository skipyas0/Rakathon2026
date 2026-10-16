import { useState } from 'react'
import { api } from './api'
import { Doc } from './icons'
import { Steps } from './Steps'

const toBase64 = (f: File) =>
  new Promise<string>((resolve, reject) => {
    const r = new FileReader()
    r.onload = () => resolve(String(r.result).split(',')[1] ?? '')
    r.onerror = () => reject(r.error)
    r.readAsDataURL(f)
  })

/** Step 1: a FHIR file (picked or dropped) is uploaded at once and the journey continues. */
export function Intake() {
  const [error, setError] = useState('')
  const [busy, setBusy] = useState(false)
  const [over, setOver] = useState(false)
  const upload = async (files: FileList | null) => {
    const f = files?.[0]
    if (!f) return
    setBusy(true)
    setError('')
    try {
      const { case_id } = await api.intake('fhir', [{ name: f.name, data: await toBase64(f) }])
      location.hash = `#/case/${encodeURIComponent(case_id)}/board`
    } catch (e) {
      setError((e as Error).message)
      setBusy(false)
    }
  }

  return (
    <div className="page journey">
      <Steps current="upload" />
      <h1>Nahrání</h1>
      <div className="upload">
        <label
          className={`upload-box ${over ? 'over' : ''}`}
          onDragOver={(e) => {
            e.preventDefault()
            setOver(true)
          }}
          onDragLeave={() => setOver(false)}
          onDrop={(e) => {
            e.preventDefault()
            setOver(false)
            void upload(e.dataTransfer.files)
          }}
        >
          <input type="file" accept=".json,application/json" disabled={busy} onChange={(e) => void upload(e.target.files)} />
          <Doc />
          <strong>{busy ? 'Nahrávám…' : 'FHIR'}</strong>
        </label>
        <span className="or">nebo</span>
        {/* ponytail: enable once the backend extracts PDFs (POST /api/intake answers 501 until then) */}
        <div className="upload-box soon" aria-disabled>
          <Doc />
          <strong>PDF</strong>
          <span className="chip muted-chip">Připravujeme</span>
        </div>
      </div>
      {error && <div className="banner bad">{error}</div>}
    </div>
  )
}
