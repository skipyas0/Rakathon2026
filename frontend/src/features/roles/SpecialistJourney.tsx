import { useEffect, useState } from 'react'
import { api, type CaseRecord } from '../../api'
import type { Case } from '../../briefing'
import { Alert, Check, Robot } from '../../icons'
import { FactsStep, Locked, Nav, PatientStep, Working } from '../../Journey'
import { load, save as remember, SPECIALTIES } from '../../layout'
import type { Statement } from '../../provenance'
import { now, renderer } from '../../render'
import { Steps } from '../../Steps'
import { SPECIALIST_STEPS, type SpecialistStep } from './role'

type Data = { c: Case; record: CaseRecord }

/** A board specialist's journey through one case (docs/workflow-plan.md): the coordinator's Pacient
 * and Klíčové informace narrowed to what concerns the specialty, then their stanovisko and stance. */
export function SpecialistJourney({ id, step, role }: { id: string; step: SpecialistStep; role: string }) {
  const [data, setData] = useState<Data | null>(null)
  const [error, setError] = useState('')
  useEffect(() => {
    Promise.all([api.case(id), api.record(id)]).then(
      ([c, record]) => setData({ c, record }),
      (e: Error) => setError(e.message),
    )
  }, [id])

  if (error) return <div className="banner bad page">{error}</div>
  if (!data || data.c.id !== id) return <p className="muted page">Načítám…</p>
  const { record } = data
  if (!record.board.some((m) => m.specialty === role)) return <p className="big page">Tento případ vám koordinátor nepřidělil.</p>
  // its own section, the patient's, and the red flags raised for it (no area = for everyone)
  const c: Case = {
    ...data.c,
    red_flags: data.c.red_flags.filter((f) => !f.area || f.area === role || f.area === 'patient'),
    sections: data.c.sections.filter((s) => s.id === role || s.id === 'patient'),
  }
  const i = SPECIALIST_STEPS.findIndex((s) => s.id === step)
  const go = (to: number) => (location.hash = `#/case/${encodeURIComponent(id)}/${SPECIALIST_STEPS[to].id}`)
  const next = () => go(i + 1)
  const prev = i > 0 ? () => go(i - 1) : undefined
  const setRecord = (record: CaseRecord) => setData({ ...data, record })

  return (
    <div className="page journey">
      <Steps current={step} caseId={id} steps={SPECIALIST_STEPS} />
      {step === 'patient' && <PatientStep c={c} record={record} next={next} />}
      {step === 'facts' && <FactsStep c={c} record={record} next={next} prev={prev} />}
      {step === 'stanovisko' && <StanoviskoStep c={c} record={record} role={role} setRecord={setRecord} prev={prev} />}
    </div>
  )
}

type StepProps = Data & { role: string; setRecord: (r: CaseRecord) => void; prev?: () => void }

/** The specialist's stance on the proposed postup and their stanovisko: empty until they generate
 * it (AI, blue, to confirm) or write it; editing makes it theirs. Signed with the name typed here. */
function StanoviskoStep({ c, record, role, setRecord, prev }: StepProps) {
  const locked = !!record.decision.confirmed_by
  const member = record.board.find((m) => m.specialty === role)
  const own = record.stanoviska[role]
  const [name, setName] = useState(() => load('mdt.signer', ''))
  const [text, setText] = useState<string | null>(null) // null = not editing
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')

  const run = async (call: Promise<CaseRecord>) => {
    setError('')
    try {
      setRecord(await call)
      return true
    } catch (e) {
      setError((e as Error).message)
      return false
    }
  }
  const update = (u: { supports?: boolean; statement?: Statement }) => run(api.updateStanovisko(c.id, role, u))
  const sign = async (s: Statement) => {
    if (!name.trim()) {
      setError('Vyplňte své jméno')
      return false
    }
    remember('mdt.signer', name.trim())
    return update({ statement: { ...s, confirmed_by: name.trim(), confirmed_at: now() } })
  }
  const generate = async () => {
    if (own && !window.confirm('Nahradit stávající stanovisko návrhem AI?')) return
    setBusy(true)
    await run(api.generateStanovisko(c.id, role))
    setBusy(false)
  }
  const write = async () => {
    if (text !== null && (await sign({ text: text.trim(), origin: 'human', sources: [] }))) setText(null)
  }
  const S = renderer(record, () => own && void sign(own))

  return (
    <>
      <h1>Stanovisko · {SPECIALTIES[role]}</h1>
      {locked && <Locked />}
      {error && <div className="banner bad">{error}</div>}
      {record.decision.plan && (
        <section className="question-card">
          <p className="eyebrow">Navržený postup</p>
          <p>{record.decision.plan}</p>
        </section>
      )}
      <div className="segmented-stance" role="group" aria-label="Postoj k navrženému postupu">
        <button className={member?.supports ? 'yes on' : 'yes'} disabled={locked} onClick={() => void update({ supports: true })}>
          <Check /> Podporuje
        </button>
        <button className={member?.supports ? 'no' : 'no on'} disabled={locked} onClick={() => void update({ supports: false })}>
          <Alert /> Nepodporuje
        </button>
      </div>
      {busy ? (
        <Working label="AI připravuje stanovisko" typical={45} />
      ) : text !== null ? (
        <label className="big-field">
          Stanovisko
          <textarea autoFocus value={text} onChange={(e) => setText(e.target.value)} />
        </label>
      ) : own ? (
        S(`stanoviska.${role}`, own, 'card')
      ) : (
        <p className="muted big">Stanovisko zatím není zadáno.</p>
      )}
      {!locked && !busy && (
        <div className="stanovisko-actions">
          <input value={name} onChange={(e) => setName(e.target.value)} placeholder="Vaše jméno" aria-label="Vaše jméno" />
          {text !== null ? (
            <>
              <button onClick={() => setText(null)}>Zrušit</button>
              <button className="primary" disabled={!text.trim() || !name.trim()} onClick={() => void write()}>
                Uložit
              </button>
            </>
          ) : (
            <>
              <button onClick={() => setText(own?.text ?? '')}>{own ? 'Upravit' : 'Napsat'}</button>
              <button onClick={() => void generate()}>
                <Robot /> {own ? 'Vygenerovat znovu' : 'Vygenerovat'}
              </button>
            </>
          )}
        </div>
      )}
      <Nav prev={prev} close={() => (location.hash = '#/')} />
    </>
  )
}
