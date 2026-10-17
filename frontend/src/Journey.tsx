import { useEffect, useRef, useState } from 'react'
import { AI_POLL_MS, api, type CaseRecord, type Decision, type GuidelineAssessment, type Intent, type Recommendation } from './api'
import { type Case, NOT_FOUND, type RedFlag } from './briefing'
import type { Statement } from './provenance'
import { ChartsDialog } from './Charts'
import { Alert, Check, Download, IntentIcon, Lock, Robot } from './icons'
import { fmtDate, fmtDateTime, INTENTS, KIND, MIN_SPECIALTIES, SPECIALTIES, type Step, STEPS, TUMOURS } from './layout'
import { now, renderer } from './render'
import { Stanoviska } from './Stanoviska'
import { Steps } from './Steps'
import { setUnsaved, useUnsaved } from './unsaved'
import { ReportReview } from './features/report/ReportReview'
import { ChoiceRows } from './features/choices/ChoiceRows'
import { CHOICE_ROWS, choiceText, cleanChoices } from './features/choices/choices'

type Data = { c: Case; record: CaseRecord; rec: Recommendation }

const SECTION_LABEL: Record<string, string> = { ...SPECIALTIES, patient: 'Pacient' }

/** The coordinator's journey through one case, one screen per step (docs/workflow-plan.md). */
export function Journey({ id, step }: { id: string; step: Step }) {
  const [data, setData] = useState<Data | null>(null)
  const [error, setError] = useState('')
  const [aiRunning, setAiRunning] = useState(false)
  useEffect(() => {
    let timer = 0
    const load = () =>
      Promise.all([api.case(id), api.record(id), api.recommendation(id)]).then(
        ([c, record, rec]) => setData({ c, record, rec }),
        (e: Error) => setError(e.message),
      )
    // while the agent briefs the patient, check back and reload the case once it's done
    const poll = (wasRunning: boolean) =>
      api.ai(id).then(
        ({ status }) => {
          setAiRunning(status === 'running')
          if (status === 'running') timer = window.setTimeout(() => poll(true), AI_POLL_MS)
          else if (wasRunning) void load()
        },
        () => setAiRunning(false),
      )
    void load()
    void poll(false)
    return () => window.clearTimeout(timer)
  }, [id])
  // specialists set their stances and stanoviska meanwhile (features/roles): a fresh record on
  // every step, and every AI_POLL_MS on the screens that show the stanoviska
  useEffect(() => {
    const refresh = () => api.record(id).then((record) => setData((d) => d && { ...d, record }), () => {})
    void refresh()
    if (step !== 'plan' && step !== 'confirm') return
    const t = window.setInterval(refresh, AI_POLL_MS)
    return () => window.clearInterval(t)
  }, [id, step])

  if (error) return <div className="banner bad page">{error}</div>
  if (!data || data.c.id !== id) return <p className="muted page">Načítám…</p>
  const { c, record, rec } = data
  const save = async (r: CaseRecord) => {
    try {
      setData({ ...data, record: await api.saveRecord(id, r) })
      setUnsaved(false) // a step saves all its input, so it may leave without asking
      setError('')
      return true
    } catch (e) {
      setError((e as Error).message)
      return false
    }
  }
  const i = STEPS.findIndex((s) => s.id === step)
  const go = (to: number) => (location.hash = `#/case/${encodeURIComponent(id)}/${STEPS[to].id}`)
  const next = () => go(i + 1)
  // the upload step has no page for an existing case, so the board has no Předchozí
  const prev = i > 1 ? () => go(i - 1) : undefined
  const setRecord = (record: CaseRecord) => setData({ ...data, record })
  const props = { c, record, rec, save, setRecord, next, prev }

  return (
    <div className="page journey">
      <Steps current={step} caseId={id} />
      {aiRunning && (
        <div className="banner ai">
          <Robot /> AI připravuje podklady… Stránka se po dokončení sama obnoví.
        </div>
      )}
      {step === 'board' && <BoardStep {...props} />}
      {step === 'patient' && <PatientStep {...props} />}
      {step === 'course' && <CourseStep {...props} />}
      {step === 'facts' && <FactsStep {...props} />}
      {step === 'questions' && <QuestionsStep {...props} />}
      {step === 'intent' && <IntentStep {...props} />}
      {step === 'plan' && <PlanStep {...props} />}
      {step === 'confirm' && <ConfirmStep {...props} />}
      {step === 'export' && <ExportStep {...props} />}
    </div>
  )
}

/** A wait on the AI: moving bar, elapsed seconds and the usual duration. ponytail: no stages, the
 * request is one LLM call the browser can't see into; add server-sent stages if waits get long. */
export function Working({ label, typical }: { label: string; typical: number }) {
  const [seconds, setSeconds] = useState(0)
  useEffect(() => {
    const t = window.setInterval(() => setSeconds((s) => s + 1), 1000)
    return () => window.clearInterval(t)
  }, [])
  return (
    <div className="working" role="status">
      <p>
        <Robot /> {label}…
      </p>
      <div className="working-bar" aria-hidden>
        <span />
      </div>
      <p className="working-time">
        {seconds} s · {seconds <= typical * 2 ? `obvykle kolem ${typical} s` : 'trvá déle než obvykle'}
      </p>
    </div>
  )
}

/** Shown where a confirmed conclusion makes the fields read-only, so they don't look broken. */
export const Locked = () => (
  <p className="locked-note">
    <Lock /> Rozhodnutí komise je potvrzeno a uzamčeno. Změnit ho lze po vymazání případu v Přehledu.
  </p>
)

type StepProps = Data & {
  save: (r: CaseRecord) => Promise<boolean>
  setRecord: (r: CaseRecord) => void
  next: () => void
  prev?: () => void
}
type ViewProps = Pick<StepProps, 'c' | 'record' | 'next' | 'prev'> // screens the specialists share

/** Předchozí (grey: the previous tab) and Další, or Zavřít (dark grey, back to
 * Přehled) on the last screen. Steps with input pass their own handlers, which save first, so
 * going either way never loses what was entered; `saves` says so on the button ("Uložit a další",
 * "Uložit a zavřít"), since a chevron click leaves without saving. */
type NavProps = { next?: () => void; prev?: () => void; close?: () => void; disabled?: boolean; saves?: boolean }
export const Nav = ({ next, prev, close, disabled, saves }: NavProps) => (
  <div className="nav-row">
    {prev && (
      <button className="back" onClick={prev}>
        Předchozí
      </button>
    )}
    {next && (
      <button className="primary next" onClick={next} disabled={disabled}>
        {saves ? 'Uložit a další' : 'Další'}
      </button>
    )}
    {close && (
      <button className="close" onClick={close} disabled={disabled}>
        {saves ? 'Uložit a zavřít' : 'Zavřít'}
      </button>
    )}
  </div>
)

function BoardStep({ record, save, next }: StepProps) {
  const [chosen, setChosen] = useState(() => record.board.map((m) => m.specialty))
  const toggle = (s: string) => setChosen(chosen.includes(s) ? chosen.filter((x) => x !== s) : [...chosen, s])
  useUnsaved([...chosen].sort().join() !== record.board.map((m) => m.specialty).sort().join())
  const submit = async () => {
    const board = chosen.map((s) => record.board.find((m) => m.specialty === s) ?? { name: '', specialty: s, chair: false, supports: true })
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
      <Nav next={submit} disabled={chosen.length < MIN_SPECIALTIES} saves />
    </>
  )
}

const RECENT = 4 // latest events shown; the whole course is one click away (no page scrolling)
const FACTS = 4 // diagnosis facts shown (the agent's key facts come first), the rest one click away
const WISHES = 2 // patient's wishes shown under the question, the rest one click away

/** Who the patient is, what must not be missed, the question and the patient's wishes. */
export function PatientStep({ c, record, next, prev }: ViewProps) {
  const S = renderer(record)
  const question = record.prep.question || c.question?.text
  const preference = [...(c.preference ?? []).entries()]
  const items = (list: [number, Statement][], path: string) =>
    list.map(([i, s]) => <li key={i}>{S(`${path}.${i}`, s, 'inline')}</li>)
  // what must not be missed: critical findings, else the most important ones
  const critical = [...c.red_flags.entries()].filter(([, f]) => f.severity === 'high')
  const alerts = (critical.length ? critical : [...c.red_flags.entries()].filter(([, f]) => f.severity === 'medium')).slice(0, 2)
  const facts: [string, string | null | undefined][] = [
    ['Pacient', c.label],
    ['Diagnóza', TUMOURS[c.tumour] ?? c.tumour],
    ['Komise', c.board],
    ['MDT', c.mdt_date && fmtDate(c.mdt_date)],
  ]
  return (
    <>
      <h1>Pacient</h1>
      <dl className="case-facts">
        {facts
          .filter(([, v]) => v)
          .map(([label, value]) => (
            <div key={label}>
              <dt>{label}</dt>
              <dd>{value}</dd>
            </div>
          ))}
      </dl>
      {alerts.length > 0 && (
        <ul className={`key-facts compact ${critical.length ? 'crit' : 'warn'}`}>
          {alerts.map(([i, f]) => (
            <li key={i}>
              <Alert /> {S(`red_flags.${i}`, f.statement, 'inline')}
            </li>
          ))}
        </ul>
      )}
      <section className={`question-card ${question ? '' : 'missing'}`}>
        <p className="eyebrow">Otázka pro komisi</p>
        <p className="question">{question ?? 'Chybí otázka pro komisi'}</p>
      </section>
      {preference.length > 0 && (
        <section className="question-card preference">
          <p className="eyebrow">Přání pacienta</p>
          <ul className="plain">{items(preference.slice(0, WISHES), 'preference')}</ul>
          {preference.length > WISHES && (
            <details className="more">
              <summary>
                Další <span className="muted">({preference.length - WISHES})</span>
              </summary>
              <ul className="plain">{items(preference.slice(WISHES), 'preference')}</ul>
            </details>
          )}
        </section>
      )}
      <Nav next={next} prev={prev} />
    </>
  )
}

/** The diagnosis, performance status and the course of the disease. */
function CourseStep({ c, record, next, prev }: StepProps) {
  const S = renderer(record)
  const course = (from: number) => (
    <ol className="course">
      {c.timeline.slice(Math.max(0, from)).map((e, i, all) => {
        const k = c.timeline.length - all.length + i
        return (
          <li key={k}>
            <time>{fmtDate(e.date)}</time>
            <span className="kind">{KIND[e.kind]}</span>
            {S(`timeline.${k}`, e.statement, 'inline')}
          </li>
        )
      })}
    </ol>
  )
  const ecog = c.summary.findIndex((s) => s.text.startsWith('ECOG'))
  const facts = [...c.summary.entries()].filter(([i]) => i !== ecog)
  const items = (list: [number, Statement][], path: string) =>
    list.map(([i, s]) => <li key={i}>{S(`${path}.${i}`, s, 'inline')}</li>)
  return (
    <>
      <h1>Průběh</h1>
      <div className="patient-grid">
        <section>
          <h2>Diagnóza</h2>
          <ul className="plain">{items(facts.slice(0, FACTS), 'summary')}</ul>
          {facts.length > FACTS && (
            <details className="more">
              <summary>
                Další fakta <span className="muted">({facts.length - FACTS})</span>
              </summary>
              <div className="scroll-box">
                <ul className="plain">{items(facts.slice(FACTS), 'summary')}</ul>
              </div>
            </details>
          )}
          {ecog >= 0 && (
            <>
              <h2>Výkonnostní stav</h2>
              <p>{S(`summary.${ecog}`, c.summary[ecog], 'inline')}</p>
            </>
          )}
        </section>
        <section>
          <h2>Průběh onemocnění</h2>
          <div className="course-recent">{course(c.timeline.length - RECENT)}</div>
          {c.timeline.length > RECENT && (
            <details className="more">
              <summary>
                Celý průběh <span className="muted">({c.timeline.length})</span>
              </summary>
              <div className="scroll-box">{course(0)}</div>
            </details>
          )}
        </section>
      </div>
      <Nav next={next} prev={prev} />
    </>
  )
}

const UNROLLED = 4

export function FactsStep({ c, record, next, prev }: ViewProps) {
  const S = renderer(record)
  const flags = (sev: RedFlag['severity']) => [...c.red_flags.entries()].filter(([, f]) => f.severity === sev)
  // at most UNROLLED findings in full (critical first), so the screen doesn't scroll
  const critical = flags('high').slice(0, UNROLLED)
  const important = flags('medium').slice(0, UNROLLED - critical.length)
  const more = [...flags('high').slice(critical.length), ...flags('medium').slice(important.length)]
  const minor = flags('low')
  const gaps = c.sections.flatMap((sec) =>
    sec.items.flatMap((s, i) => (s.text.endsWith(NOT_FOUND) ? [[`sections.${sec.id}.${i}`, s] as const] : [])),
  )
  const groups: [string, (readonly [string, Statement])[]][] = [
    ['Další důležitá upozornění', more.map(([i, f]) => [`red_flags.${i}`, f.statement] as const)],
    ['Méně závažná upozornění', minor.map(([i, f]) => [`red_flags.${i}`, f.statement] as const)],
    ['Chybějící údaje', gaps],
    ...c.sections.map((sec): [string, (readonly [string, Statement])[]] => [
      SECTION_LABEL[sec.id] ?? sec.title,
      sec.items.flatMap((s, i) => (s.text.endsWith(NOT_FOUND) ? [] : [[`sections.${sec.id}.${i}`, s] as const])),
    ]),
  ]
  const list = (items: [number, RedFlag][], cls: string) => (
    <ul className={`key-facts ${cls}`}>
      {items.map(([i, f]) => (
        <li key={i}>
          <Alert /> {S(`red_flags.${i}`, f.statement, 'inline')}
        </li>
      ))}
    </ul>
  )
  return (
    <>
      <h1>Klíčové informace</h1>
      {critical.length > 0 && (
        <>
          <h2 className="crit-text">Kritické</h2>
          {list(critical, 'crit')}
        </>
      )}
      {important.length > 0 && (
        <>
          <h2 className="warn-text">Důležité</h2>
          {list(important, 'warn')}
        </>
      )}
      {!critical.length && !important.length && <p>Žádná kritická ani důležitá upozornění.</p>}
      <h2>Další informace</h2>
      <div className="more-grid">
        {groups
          .filter(([, items]) => items.length)
          .map(([title, items]) => (
            <details key={title} className="more">
              <summary>
                {title} <span className="muted">({items.length})</span>
              </summary>
              <ul className="plain">
                {items.map(([k, s]) => (
                  <li key={k}>{S(k, s, 'inline')}</li>
                ))}
              </ul>
            </details>
          ))}
        <ChartsDialog trends={c.trends} />
      </div>
      <Nav next={next} prev={prev} />
    </>
  )
}

const TRIAL_VERDICTS = { eligible: 'Potenciálně vhodný', ineligible: 'Nevhodný', missing_data: 'Chybí údaj' }
/** The 2–3 questions the agent says the board must settle, before it picks the léčebný záměr. */
function QuestionsStep({ c, record, next, prev }: StepProps) {
  const S = renderer(record)
  const questions = c.decision_support.questions
  return (
    <>
      <h1>Otázky k diskusi</h1>
      {questions.length ? (
        <ol className="key-facts questions">
          {questions.map((q, i) => (
            <li key={i}>{S(`questions.${i}`, q, 'inline')}</li>
          ))}
        </ol>
      ) : (
        <p className="muted">Otázky zatím nejsou k dispozici.</p>
      )}
      {c.decision_support.trials.length > 0 && (
        <section>
          <h2>Klinické studie</h2>
          <p className="ai-note">
            <Robot /> AI předběžný filtr, nikoli potvrzení způsobilosti. Potenciální shoda může mít
            neověřená kritéria; stačí jedno doložené zařazení bez doloženého vyřazení nebo neshody
            typu nádoru. Rozhoduje lékař.
          </p>
          {c.decision_support.trials.map((trial, ti) => (
            <details key={trial.trial} className="more trial">
              <summary>
                {trial.trial} <span className="ai-chip"><Robot /> {TRIAL_VERDICTS[trial.verdict]}</span>
              </summary>
              <ul className="plain">
                {trial.criteria.map((s, i) => (
                  <li key={i}>{S(`trials.${ti}.${i}`, s, 'inline')}</li>
                ))}
              </ul>
            </details>
          ))}
        </section>
      )}
      <Nav next={next} prev={prev} />
    </>
  )
}

function IntentStep({ record, rec, save, next, prev }: StepProps) {
  const locked = !!record.decision.confirmed_by
  const [intents, setIntents] = useState(record.decision.intents)
  const [choices, setChoices] = useState(record.decision.choices)
  // several may apply at once; kept in the tiles' order so the record reads the same either way
  const toggle = (k: Intent) =>
    setIntents(intents.includes(k) ? intents.filter((x) => x !== k) : (Object.keys(INTENTS) as Intent[]).filter((x) => x === k || intents.includes(x)))
  const changed = intents.join() !== record.decision.intents.join() || JSON.stringify(cleanChoices(choices)) !== JSON.stringify(cleanChoices(record.decision.choices))
  useUnsaved(!locked && changed)
  const keep = async (go: () => void) => {
    if (locked || !intents.length || (await save({ ...record, decision: { ...record.decision, intents, choices: cleanChoices(choices) } }))) go()
  }
  return (
    <>
      <h1>Léčebný plán</h1>
      {locked && <Locked />}
      {rec && <RecommendedPopup rec={rec} record={record} />}
      <div className="tiles">
        {(Object.keys(INTENTS) as Intent[]).map((k) => (
          <button key={k} className={`tile intent-${k} ${intents.includes(k) ? 'on' : ''}`} aria-pressed={intents.includes(k)} disabled={locked} onClick={() => toggle(k)}>
            <IntentIcon intent={k} />
            {INTENTS[k].label}
          </button>
        ))}
      </div>
      <ChoiceRows value={choices} onChange={setChoices} disabled={locked} />
      <Nav next={() => keep(next)} prev={prev && (() => keep(prev))} disabled={!intents.length} saves={!locked} />
    </>
  )
}

function PlanStep({ c, record, save, setRecord, next, prev }: StepProps) {
  const locked = !!record.decision.confirmed_by
  const [plan, setPlan] = useState(record.decision.plan)
  const [rationale, setRationale] = useState(record.decision.rationale)
  useUnsaved(!locked && (plan.trim() !== record.decision.plan || rationale.trim() !== record.decision.rationale))
  const keep = async (go: () => void) => {
    if (locked || (await save({ ...record, decision: { ...record.decision, plan: plan.trim(), rationale: rationale.trim() } }))) go()
  }
  return (
    <>
      <h1>Závěr</h1>
      {locked && <Locked />}
      <label className="big-field">
        Zvolený postup
        <textarea value={plan} disabled={locked} onChange={(e) => setPlan(e.target.value)} />
      </label>
      <label className="big-field">
        Zdůvodnění
        <textarea value={rationale} disabled={locked} onChange={(e) => setRationale(e.target.value)} />
      </label>
      <Stanoviska c={c} record={record} onChange={setRecord} />
      <Nav next={() => keep(next)} prev={prev && (() => keep(prev))} disabled={!plan.trim() || !rationale.trim()} saves={!locked} />
    </>
  )
}

function ConfirmStep({ c, record, rec, save, setRecord, next, prev }: StepProps) {
  const S = renderer(record)
  const d = record.decision
  const locked = !!d.confirmed_by
  const savedAssessment = d.guideline_assessment
  // the record reloads on a timer: a string, so a fresh but equal list doesn't re-run the AI check
  const intents = d.intents.join()
  const sourcesMatch =
    !!rec &&
    savedAssessment?.recommendation_sources.length === rec.statement.sources.length &&
    savedAssessment.recommendation_sources.every(
      (source, i) =>
        source.reference === rec.statement.sources[i].reference &&
        source.excerpt === rec.statement.sources[i].excerpt,
    )
  const savedMatches =
    !!rec &&
    sourcesMatch &&
    savedAssessment?.compared_plan === d.plan &&
    savedAssessment.compared_rationale === d.rationale &&
    savedAssessment.compared_intents.join() === intents &&
    savedAssessment?.recommendation === rec.statement.text
  const assessmentKey = JSON.stringify([c.id, intents, d.plan, d.rationale, rec?.statement.text, rec?.statement.sources])
  const [assessmentResult, setAssessmentResult] = useState<
    { key: string; status: 'done'; assessment: GuidelineAssessment } | { key: string; status: 'error'; error: string } | null
  >(null)
  const [assessmentRetry, setAssessmentRetry] = useState(0)
  const [manualChoice, setManualChoice] = useState<{ key: string; value: boolean } | null>(null)
  const assessmentNeeded = !!rec && !locked && !!d.plan.trim() && !!d.rationale.trim() && !savedMatches
  const requestKey = JSON.stringify([assessmentKey, assessmentRetry])
  const currentResult = assessmentResult?.key === requestKey ? assessmentResult : null
  const assessment =
    savedMatches && savedAssessment
      ? savedAssessment
      : currentResult?.status === 'done'
        ? currentResult.assessment
        : null
  const assessmentError = currentResult?.status === 'error' ? currentResult.error : ''
  const assessmentLoading = assessmentNeeded && !currentResult
  const manual =
    manualChoice?.key === assessmentKey
      ? manualChoice.value
      : rec
        ? null
        : d.guideline_compliant
  useEffect(() => {
    if (!assessmentNeeded) return
    let active = true
    api
      .assessGuideline(c.id, { intents: intents ? (intents.split(',') as Intent[]) : [], plan: d.plan, rationale: d.rationale })
      .then(({ assessment: result }) => {
        if (active) setAssessmentResult({ key: requestKey, status: 'done', assessment: result })
      })
      .catch((e: Error) => {
        if (active) setAssessmentResult({ key: requestKey, status: 'error', error: e.message })
      })
    return () => {
      active = false
    }
  }, [assessmentNeeded, c.id, intents, d.plan, d.rationale, requestKey])
  const assessedCompliance =
    assessment?.status === 'compliant' ? true : assessment?.status === 'deviation' ? false : null
  const compliant = rec ? (assessedCompliance ?? manual) : manual
  const [reason, setReason] = useState(d.deviation_reason)
  const against = record.board.filter((m) => !m.supports) // consensus = everyone supports
  const reviewRecord: CaseRecord = locked ? record : {
    ...record,
    decision: {
      ...d,
      attendees: record.board.map((m) => ({ name: m.name, specialty: SPECIALTIES[m.specialty] ?? m.specialty })),
      guideline_compliant: compliant,
      guideline_assessment: assessment,
      deviation_reason: compliant === false ? reason.trim() : '',
    },
  }
  const reviewKey = JSON.stringify(reviewRecord)
  const [reviewed, setReviewed] = useState<{ revision: string; key: string } | null>(null)
  const reportReady = reviewed?.key === reviewKey
  useUnsaved(!locked && (manualChoice?.key === assessmentKey || reason.trim() !== d.deviation_reason))
  const compareDialog = useRef<HTMLDialogElement>(null)
  // the coordinator ticks having checked the report (opening it is up to them); a later change to the
  // decision unticks it, and Potvrdit signs the revision of the decision as it stands then
  const [read, setRead] = useState('')
  const affirmed = read === reviewKey
  const [prepError, setPrepError] = useState('')

  const confirm = async () => {
    let revision = reportReady ? reviewed.revision : null
    if (!revision)
      try {
        revision = (await api.prepareReport(c.id, reviewRecord)).revision // not opened: prepare it now
      } catch (e) {
        return setPrepError((e as Error).message)
      }
    setPrepError('')
    const decision: Decision = {
      ...reviewRecord.decision,
      report_revision: revision,
      // ponytail: one coordinator, signed by the role, no name (decision #27); ask for a name once
      // several people coordinate
      confirmed_by: 'Koordinátor/ka',
      confirmed_at: now(),
    }
    if (await save({ ...record, decision })) next()
  }

  const signed = locked && !!d.report_revision // this revision was approved with the decision
  const verdict = assessment && {
    compliant: ['ok', <Check key="i" />, 'V souladu s doporučeným postupem'],
    deviation: ['warn', <Alert key="i" />, 'Odchylka od doporučeného postupu'],
    uncertain: ['warn', <Alert key="i" />, 'Soulad nelze spolehlivě posoudit'],
  }[assessment.status]
  const manualBubbles = (yes: string, no: string) => (
    <div className="bubbles small-bubbles soulad" role="group" aria-label="Soulad s doporučeným postupem">
      {[true, false].map((v) => (
        <button key={String(v)} className={`bubble ${manual === v ? 'on' : ''}`} disabled={locked} onClick={() => setManualChoice({ key: assessmentKey, value: v })}>
          {v ? yes : no}
        </button>
      ))}
    </div>
  )

  return (
    <>
      <h1>Potvrzení</h1>
      <section className="confirm-block">
        <p className="eyebrow">Soulad s doporučeným postupem</p>
        {rec ? (
          <>
            <p className={`verdict ${verdict ? verdict[0] : ''}`}>
              {assessmentLoading && <span className="muted">AI porovnává zvolený postup s doporučením…</span>}
              {verdict && (
                <>
                  {verdict[1]} {verdict[2]}{' '}
                  <span className="ai-chip">
                    <Robot /> AI
                  </span>
                </>
              )}
              <button className="link" onClick={() => compareDialog.current?.showModal()}>
                Porovnat
              </button>
            </p>
            {assessmentError && (
              <p className="banner bad">
                {assessmentError}{' '}
                <button className="link" onClick={() => setAssessmentRetry((n) => n + 1)}>
                  Zkusit znovu
                </button>
              </p>
            )}
            {assessment?.status === 'uncertain' && manualBubbles('Přesto označit jako v souladu', 'Označit jako odchylku')}
          </>
        ) : (
          <>
            <p className="muted">Doporučení k porovnání není k dispozici.</p>
            {manualBubbles('V souladu s postupy', 'Odchylka od postupů')}
          </>
        )}
        {compliant === false &&
          (locked ? (
            d.deviation_reason && <p>Důvod odchylky: {d.deviation_reason}</p>
          ) : (
            <label className="big-field deviation">
              Proč se komise odchyluje od doporučeného postupu
              <textarea value={reason} onChange={(e) => setReason(e.target.value)} />
            </label>
          ))}
      </section>

      <Stanoviska c={c} record={record} onChange={setRecord} />
      <div className="confirm-report">
        <ReportReview id={c.id} record={reviewRecord} onReady={(revision, key) => setReviewed(revision ? { revision, key } : null)}>
          <label className="report-check">
            <input type="checkbox" checked={signed || affirmed} disabled={signed} onChange={(e) => setRead(e.target.checked ? reviewKey : '')} />
            Obsah zprávy (FHIR) jsem zkontroloval(a)
          </label>
        </ReportReview>
      </div>
      {prepError && <p className="banner bad">{prepError}</p>}
      {against.length > 0 && !locked && (
        <p className="verdict warn">
          <Alert /> Komise nemá konsenzus: nesouhlasí {against.map((m) => SPECIALTIES[m.specialty] ?? m.specialty).join(', ')}
        </p>
      )}

      {locked ? (
        <>
          <p className="verdict ok">
            <Check /> Potvrzeno: {d.confirmed_by}, {d.confirmed_at && fmtDateTime(d.confirmed_at)}
          </p>
          {!d.report_revision && (
            <button className="primary" disabled={!affirmed} onClick={confirm}>
              Potvrdit zprávu k dříve potvrzenému závěru
            </button>
          )}
          <Nav next={next} prev={prev} />
        </>
      ) : (
        <div className="confirm-row">
          {prev && (
            <button className="back" onClick={prev}>
              Předchozí
            </button>
          )}
          <button
            className="primary next"
            onClick={confirm}
            disabled={!affirmed || compliant === null || against.length > 0 || (rec !== null && (!assessment || assessmentLoading || !!assessmentError)) || (compliant === false && !reason.trim())}
          >
            {compliant === false ? 'Potvrdit s odchylkou' : 'Potvrdit'}
          </button>
        </div>
      )}

      <dialog ref={compareDialog} className="dialog compare-dialog" onClick={(e) => e.target === compareDialog.current && compareDialog.current.close()}>
        <div className="dialog-body">
          <header>
            <h3>Zvolený a doporučený postup</h3>
            <button className="icon-btn" onClick={() => compareDialog.current?.close()} aria-label="Zavřít">
              ×
            </button>
          </header>
          <div className="compare">
            <section>
              <p className="eyebrow">Zvolený postup</p>
              {d.intents.map((k) => (
                <IntentLabel key={k} intent={k} />
              ))}
              <p className="big">{d.plan}</p>
              {CHOICE_ROWS.filter((r) => d.choices[r.id]?.length).map((r) => (
                <p key={r.id} className="small">
                  <strong>{r.label}:</strong> {d.choices[r.id]!.map(choiceText).join(', ')}
                </p>
              ))}
            </section>
            <Recommended rec={rec} record={record} />
          </div>
          {assessment && S('guideline_assessment', assessment.statement)}
        </div>
      </dialog>
    </>
  )
}

function ExportStep({ c, record, prev }: StepProps) {
  const d = record.decision
  const [draft, setDraft] = useState<{ created?: string; error?: string } | null>(null)
  useEffect(() => {
    if (d.confirmed_by) api.zaverDraft(c.id).then(setDraft, (e: Error) => setDraft({ error: e.message }))
  }, [c.id, d.confirmed_by])
  if (!d.confirmed_by)
    return (
      <p>
        Závěr zatím není potvrzen. <a href={`#/case/${encodeURIComponent(c.id)}/confirm`}>Zpět na potvrzení</a>
      </p>
    )
  const url = `/api/cases/${encodeURIComponent(c.id)}/zaver`
  return (
    <>
      <h1>Export</h1>
      <p className="verdict ok">
        <Check /> Potvrzeno: {d.confirmed_by}, {d.confirmed_at && fmtDateTime(d.confirmed_at)}
      </p>
      {!d.report_revision ? (
        <p className="banner bad">
          Starší závěr nemá schválenou revizi zprávy.{' '}
          <a href={`#/case/${encodeURIComponent(c.id)}/confirm`}>Otevřít zprávu a potvrdit ji k závěru</a>.
        </p>
      ) : null}
      {!draft ? (
        <Working label="AI doplňuje podklady ze zdravotního záznamu" typical={20} />
      ) : (
        <>
          {draft.error && <div className="banner bad">{draft.error}</div>}
          <div className="export">
            <iframe className="preview" src={`${url}.pdf?v=${draft.created ?? ''}`} title="Náhled závěru" />
            <div className="export-actions">
              <a className="upload-box" href={`${url}.pdf`} download>
                <Download />
                <strong>PDF</strong>
              </a>
              <a className="upload-box" href={`${url}.docx`} download>
                <Download />
                <strong>DOCX</strong>
                <span className="muted small">k úpravám</span>
              </a>
              {d.report_revision && <a className="upload-box" href={`${url}.fhir.json`} download>
                <Download />
                <strong>FHIR</strong>
                <span className="muted small">R4</span>
              </a>}
            </div>
          </div>
        </>
      )}
      <Nav prev={prev} close={() => (location.hash = '#/')} />
    </>
  )
}

/** The recommended postup (the agent's first option, or a labelled example), to compare the
 * závěr with on Potvrzení. */
function Recommended({ rec, record }: { rec: Recommendation; record: CaseRecord }) {
  const S = renderer(record)
  return (
    <section>
      <p className="eyebrow">
        Doporučený postup {rec?.statement.model === 'ukázka' && <span className="chip muted-chip">ukázka</span>}
      </p>
      {rec ? (
        <>
          <IntentLabel intent={rec.intent} />
          <p className="big">{S('recommendation', rec.statement, 'inline')}</p>
        </>
      ) : (
        <p className="muted">Doporučení k porovnání není k dispozici.</p>
      )}
    </section>
  )
}

/** Záměr: the same recommendation folded into one AI row above the tiles, to prepare the závěr; a click opens it in
 * a pop-up, where every source opens as anywhere else. */
function RecommendedPopup({ rec, record }: { rec: NonNullable<Recommendation>; record: CaseRecord }) {
  const S = renderer(record)
  const dialog = useRef<HTMLDialogElement>(null)
  const example = rec.statement.model === 'ukázka' && <span className="chip muted-chip">ukázka</span>
  return (
    <>
      <button className="recommended-row" onClick={() => dialog.current?.showModal()}>
        <Robot label="AI" /> <span className="row-link">Doporučený postup</span> {example}
      </button>
      <dialog ref={dialog} className="dialog recommended-dialog" onClick={(e) => e.target === dialog.current && dialog.current.close()}>
        <div className="dialog-body">
          <header>
            <h3>Doporučený postup {example}</h3>
            <button className="icon-btn" onClick={() => dialog.current?.close()} aria-label="Zavřít">
              ×
            </button>
          </header>
          <IntentLabel intent={rec.intent} />
          <p className="big">{S('recommendation', rec.statement, 'inline')}</p>
        </div>
      </dialog>
    </>
  )
}

const IntentLabel = ({ intent }: { intent: Intent }) => (
  <p className={`intent-label intent-${intent}`}>
    <IntentIcon intent={intent} /> {INTENTS[intent].label}
  </p>
)
