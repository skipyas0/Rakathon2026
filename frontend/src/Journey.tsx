import { useEffect, useState } from 'react'
import { api, type CaseRecord, type Decision, type Intent, type Recommendation } from './api'
import type { Case } from './briefing'
import { TrendChart } from './Charts'
import { Alert, Check, Doc, IntentIcon } from './icons'
import { fmtDate, fmtDateTime, INTENTS, MIN_SPECIALTIES, SPECIALTIES, type Step, STEPS, TUMOURS } from './layout'
import { now, renderer } from './render'
import { Steps } from './Steps'

type Data = { c: Case; record: CaseRecord; rec: Recommendation }

/** The coordinator's journey through one case, one screen per step (docs/workflow-plan.md). */
export function Journey({ id, step, user }: { id: string; step: Step; user: string }) {
  const [data, setData] = useState<Data | null>(null)
  const [error, setError] = useState('')
  useEffect(() => {
    Promise.all([api.case(id), api.record(id), api.recommendation(id)]).then(
      ([c, record, rec]) => setData({ c, record, rec }),
      (e: Error) => setError(e.message),
    )
  }, [id])

  if (error) return <div className="banner bad page">{error}</div>
  if (!data || data.c.id !== id) return <p className="muted page">Načítám…</p>
  const { c, record, rec } = data
  const save = async (r: CaseRecord) => {
    try {
      setData({ ...data, record: await api.saveRecord(id, r) })
      setError('')
      return true
    } catch (e) {
      setError((e as Error).message)
      return false
    }
  }
  const next = () => {
    const i = STEPS.findIndex((s) => s.id === step)
    location.hash = `#/case/${encodeURIComponent(id)}/${STEPS[i + 1].id}`
  }
  const props = { c, record, rec, save, next, user }

  return (
    <div className="page journey">
      <Steps current={step} caseId={id} />
      {step === 'board' && <BoardStep {...props} />}
      {step === 'patient' && <PatientStep {...props} />}
      {step === 'facts' && <FactsStep {...props} />}
      {step === 'trends' && <TrendsStep {...props} />}
      {step === 'intent' && <IntentStep {...props} />}
      {step === 'plan' && <PlanStep {...props} />}
      {step === 'confirm' && <ConfirmStep {...props} />}
    </div>
  )
}

type StepProps = Data & { save: (r: CaseRecord) => Promise<boolean>; next: () => void; user: string }

const Next = ({ onClick, disabled }: { onClick: () => void; disabled?: boolean }) => (
  <button className="primary next" onClick={onClick} disabled={disabled}>
    Další
  </button>
)

function BoardStep({ record, save, next }: StepProps) {
  const [chosen, setChosen] = useState(() => record.board.map((m) => m.specialty))
  const toggle = (s: string) => setChosen(chosen.includes(s) ? chosen.filter((x) => x !== s) : [...chosen, s])
  const submit = async () => {
    const board = chosen.map((s) => record.board.find((m) => m.specialty === s) ?? { name: '', specialty: s, chair: false })
    if (await save({ ...record, board })) next()
  }
  return (
    <>
      <h1>Komise</h1>
      <div className="bubbles">
        {Object.entries(SPECIALTIES).map(([id, label]) => (
          <button key={id} className={`bubble ${chosen.includes(id) ? 'on' : ''}`} aria-pressed={chosen.includes(id)} onClick={() => toggle(id)}>
            {chosen.includes(id) && <Check />} {label}
          </button>
        ))}
      </div>
      <Next onClick={submit} disabled={chosen.length < MIN_SPECIALTIES} />
    </>
  )
}

function PatientStep({ c, record, next }: StepProps) {
  const S = renderer(record)
  const question = record.prep.question || c.question?.text
  return (
    <>
      <h1 className="huge">{c.label}</h1>
      <p className="big">{c.summary[0] ? S('summary.0', c.summary[0], 'inline') : TUMOURS[c.tumour]}</p>
      <p className="muted">{[c.board, c.mdt_date && `MDT ${fmtDate(c.mdt_date)}`].filter(Boolean).join(' · ')}</p>
      <p className="eyebrow">Otázka pro komisi</p>
      {question ? <p className="huge question">{question}</p> : <p className="huge missing-q">Chybí otázka pro komisi</p>}
      <Next onClick={next} />
    </>
  )
}

function FactsStep({ c, record, next }: StepProps) {
  const S = renderer(record)
  const flags = [...c.red_flags.entries()].filter(([, f]) => f.severity === 'high').slice(0, 2)
  const ecog = c.summary.findIndex((s) => s.text.startsWith('ECOG'))
  const facts = [...c.summary.entries()].filter(([i]) => i > 0 && i !== ecog)
  const items = [
    ...flags.map(([i, f]) => ({ key: `red_flags.${i}`, s: f.statement, flag: true })),
    ...(ecog >= 0 ? [{ key: `summary.${ecog}`, s: c.summary[ecog], flag: false }] : []),
    ...facts.map(([i, s]) => ({ key: `summary.${i}`, s, flag: false })),
  ].slice(0, 4)
  return (
    <>
      <h1>Klíčové informace</h1>
      <ul className="key-facts">
        {items.map((it) => (
          <li key={it.key} className={it.flag ? 'flag' : ''}>
            {it.flag && <Alert />} {S(it.key, it.s, 'inline')}
          </li>
        ))}
      </ul>
      <Next onClick={next} />
    </>
  )
}

function TrendsStep({ c, next }: StepProps) {
  return (
    <>
      <h1>Vývoj</h1>
      <div className="journey-trends">
        {c.trends.slice(0, 3).map((t) => (
          <TrendChart key={t.id} trend={t} />
        ))}
        {!c.trends.length && <p className="muted">Bez měřených hodnot.</p>}
      </div>
      <Next onClick={next} />
    </>
  )
}

function IntentStep({ record, save, next }: StepProps) {
  const locked = !!record.decision.confirmed_by
  const [intent, setIntent] = useState(record.decision.intent)
  const submit = async () => {
    if (locked || (await save({ ...record, decision: { ...record.decision, intent } }))) next()
  }
  return (
    <>
      <h1>Léčebný záměr</h1>
      <div className="bubbles">
        {(Object.keys(INTENTS) as Intent[]).map((k) => (
          <button key={k} className={`bubble intent-${k} ${intent === k ? 'on' : ''}`} aria-pressed={intent === k} disabled={locked} onClick={() => setIntent(k)}>
            <IntentIcon intent={k} /> {INTENTS[k].label}
          </button>
        ))}
      </div>
      <Next onClick={submit} disabled={!intent} />
    </>
  )
}

function PlanStep({ record, save, next }: StepProps) {
  const locked = !!record.decision.confirmed_by
  const [plan, setPlan] = useState(record.decision.plan)
  const [rationale, setRationale] = useState(record.decision.rationale)
  const submit = async () => {
    if (locked || (await save({ ...record, decision: { ...record.decision, plan: plan.trim(), rationale: rationale.trim() } }))) next()
  }
  return (
    <>
      <h1>Závěr</h1>
      <label className="big-field">
        Zvolený postup
        <textarea value={plan} disabled={locked} onChange={(e) => setPlan(e.target.value)} />
      </label>
      <label className="big-field">
        Zdůvodnění
        <textarea value={rationale} disabled={locked} onChange={(e) => setRationale(e.target.value)} />
      </label>
      <Next onClick={submit} disabled={!plan.trim() || !rationale.trim()} />
    </>
  )
}

function ConfirmStep({ c, record, rec, save, user }: StepProps) {
  const S = renderer(record)
  const d = record.decision
  const locked = !!d.confirmed_by
  // soulad s doporučenými postupy: automatic when there's a recommendation, else the coordinator says
  const [manual, setManual] = useState<boolean | null>(null)
  const compliant = rec ? d.intent === rec.intent : manual
  const [asking, setAsking] = useState(false)
  const [reason, setReason] = useState(d.deviation_reason)
  const [role, setRole] = useState<string | null>(null)

  const confirm = () => {
    if (compliant === false && !reason.trim()) return setAsking(true)
    const decision: Decision = {
      ...d,
      attendees: record.board.map((m) => ({ name: m.name, specialty: SPECIALTIES[m.specialty] ?? m.specialty })),
      guideline_compliant: compliant,
      deviation_reason: compliant === false ? reason.trim() : '',
      confirmed_by: user,
      confirmed_at: now(),
    }
    void save({ ...record, decision })
  }

  return (
    <>
      <h1>Potvrzení</h1>
      <div className="compare">
        <section>
          <p className="eyebrow">Zvolený postup</p>
          {d.intent && <IntentLabel intent={d.intent} />}
          <p className="big">{d.plan}</p>
          <p>{d.rationale}</p>
        </section>
        <section className="recommended">
          <p className="eyebrow">
            Doporučený postup <span className="chip muted-chip">ukázka</span>
          </p>
          {rec ? (
            <>
              <IntentLabel intent={rec.intent} />
              {S('recommendation', rec.statement)}
            </>
          ) : (
            <p className="muted">Doporučení k porovnání není k dispozici.</p>
          )}
        </section>
      </div>

      {rec ? (
        <p className={`verdict ${compliant ? 'ok' : 'warn'}`}>
          {compliant ? <Check /> : <Alert />} {compliant ? 'V souladu s doporučeným postupem' : 'Odchylka od doporučeného postupu'}
        </p>
      ) : (
        <div className="bubbles small-bubbles" role="group" aria-label="Soulad s doporučenými postupy">
          {[true, false].map((v) => (
            <button key={String(v)} className={`bubble ${manual === v ? 'on' : ''}`} disabled={locked} onClick={() => setManual(v)}>
              {v ? 'V souladu s postupy' : 'Odchylka od postupů'}
            </button>
          ))}
        </div>
      )}

      <p className="eyebrow">Stanoviska</p>
      <div className="bubbles small-bubbles">
        {record.board.map((m) => (
          <button key={m.specialty} className={`bubble ${role === m.specialty ? 'on' : ''}`} onClick={() => setRole(role === m.specialty ? null : m.specialty)}>
            {SPECIALTIES[m.specialty] ?? m.specialty}
          </button>
        ))}
      </div>
      {role && (
        <section className="card opinion">
          <p>
            <span className="chip muted-chip">ukázka</span> Z pohledu odbornosti {SPECIALTIES[role] ?? role} bez námitek k navrženému
            postupu.
          </p>
          {c.sections.find((s) => s.id === role)?.items.map((s, i) => S(`sections.${role}.${i}`, s, 'inline'))}
        </section>
      )}

      {locked ? (
        <div className="confirmed-line">
          <p className="verdict ok">
            <Check /> Potvrzeno: {d.confirmed_by}, {d.confirmed_at && fmtDateTime(d.confirmed_at)}
            {d.guideline_compliant === false && ` · důvod odchylky: ${d.deviation_reason}`}
          </p>
          <button className="primary next" onClick={() => print()}>
            <Doc /> Stáhnout PDF
          </button>
        </div>
      ) : (
        <>
          {asking && (
            <label className="big-field">
              Důvod odchylky
              <textarea autoFocus value={reason} onChange={(e) => setReason(e.target.value)} />
            </label>
          )}
          <button
            className="primary next"
            onClick={confirm}
            disabled={!user || compliant === null || (asking && !reason.trim())}
            title={!user ? 'Zadejte své jméno vpravo nahoře' : ''}
          >
            Potvrdit
          </button>
        </>
      )}
    </>
  )
}

const IntentLabel = ({ intent }: { intent: Intent }) => (
  <p className={`intent-label intent-${intent}`}>
    <IntentIcon intent={intent} /> {INTENTS[intent].label}
  </p>
)
