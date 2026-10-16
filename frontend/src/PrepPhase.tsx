import { type ReactNode, useState } from 'react'
import type { CaseRecord } from './api'
import { type Case, statements } from './briefing'
import { Board } from './Board'
import { Findings } from './Findings'
import { Alert as AlertIcon, Arrow, Check, Doc, Missing as MissingIcon, Robot } from './icons'
import { fmtDate, fmtDateTime, MIN_SPECIALTIES, type Phase } from './layout'
import type { Source } from './provenance'
import { findingKeys, isPending, now, renderer } from './render'
import { sourceType, useSources } from './sources'
import { StatementView } from './StatementView'

type Props = {
  c: Case
  record: CaseRecord
  save: (r: CaseRecord) => void
  user: string
  go: (p: Phase) => void
}

/** Phase 1, the coordinator's workspace: documents and question, triage of findings, the board
 * (more tabs follow: structure, visibility, specialists). Clinicians confirm AI claims elsewhere. */
export function PrepPhase({ c, record, save, user, go }: Props) {
  const [tab, setTab] = useState('docs')
  const [question, setQuestion] = useState(record.prep.question || c.question?.text || '')
  const prep = record.prep
  const setPrep = (p: Partial<CaseRecord['prep']>) => save({ ...record, prep: { ...prep, ...p } })

  const ai = statements(c).filter(([, s]) => s.origin === 'ai' && !s.confirmed_by)
  const done = ai.filter(([k, s]) => !isPending(record, k, s)).length
  const findings = findingKeys(c)
  const triaged = findings.filter((k) => record.triage[k]).length
  const hasQuestion = !!question.trim()
  const specialties = new Set(record.board.map((m) => m.specialty)).size
  const boardOk = specialties >= MIN_SPECIALTIES

  const tabs: { id: string; label: string; count?: string; body: ReactNode }[] = [
    {
      id: 'docs',
      label: 'Podklady',
      body: <Documents c={c} record={record} question={question} setQuestion={setQuestion} setPrep={setPrep} />,
    },
    {
      id: 'findings',
      label: 'Nálezy',
      count: `${triaged}/${findings.length}`,
      body: <Findings c={c} record={record} save={save} user={user} />,
    },
    { id: 'board', label: 'Komise', count: String(record.board.length), body: <Board c={c} record={record} save={save} /> },
  ]

  return (
    <div className="phase-grid">
      <div className="phase-main">
        <nav className="tabs" role="tablist" aria-label="Příprava případu">
          {tabs.map((t) => (
            <button key={t.id} role="tab" aria-selected={tab === t.id} className={tab === t.id ? 'on' : ''} onClick={() => setTab(t.id)}>
              {t.label}
              {t.count && <span className="count">{t.count}</span>}
            </button>
          ))}
        </nav>
        <div role="tabpanel">{tabs.find((t) => t.id === tab)?.body}</div>
      </div>

      <aside className="phase-aside">
        <section className="card readiness">
          <h3>Připravenost případu</h3>
          <ul className="checklist">
            <li className={hasQuestion ? 'ok' : 'bad'}>
              {hasQuestion ? <Check /> : <MissingIcon />} Otázka pro komisi
            </li>
            <li className={boardOk ? 'ok' : 'bad'}>
              {boardOk ? <Check /> : <MissingIcon />} Komise: {specialties} odbornosti (min. {MIN_SPECIALTIES})
            </li>
            <li className={triaged === findings.length ? 'ok' : 'warn'}>
              {triaged === findings.length ? <Check /> : <AlertIcon />} Roztříděno {triaged} z {findings.length} nálezů
            </li>
            <li className={done === ai.length ? 'ok' : 'warn'}>
              <Robot /> Lékaři potvrdili {done} z {ai.length} návrhů AI
            </li>
          </ul>
          <div className="meter" role="meter" aria-valuenow={done} aria-valuemin={0} aria-valuemax={ai.length}>
            <span style={{ width: `${ai.length ? (done / ai.length) * 100 : 100}%` }} />
          </div>
          {prep.prepared_by ? (
            <p className="done-line">
              <Check /> Připravil {prep.prepared_by}, {prep.prepared_at && fmtDateTime(prep.prepared_at)}
            </p>
          ) : (
            <button
              className="primary wide"
              disabled={!hasQuestion || !boardOk || !user}
              title={
                !user ? 'Zadejte své jméno vpravo nahoře' : !hasQuestion ? 'Chybí otázka pro komisi' : !boardOk ? 'Sestavte komisi' : ''
              }
              onClick={() => {
                setPrep({ question, prepared_by: user, prepared_at: now() })
                go('meeting')
              }}
            >
              Připraveno k projednání
            </button>
          )}
          <button className="wide" onClick={() => go('meeting')}>
            Přehled pro zasedání <Arrow />
          </button>
        </section>
      </aside>
    </div>
  )
}

function Documents({
  c,
  record,
  question,
  setQuestion,
  setPrep,
}: {
  c: Case
  record: CaseRecord
  question: string
  setQuestion: (q: string) => void
  setPrep: (p: Partial<CaseRecord['prep']>) => void
}) {
  const show = useSources()
  const S = renderer(record)
  const [newQ, setNewQ] = useState('')
  const prep = record.prep

  // Consolidated sources: every record referenced anywhere in the briefing, grouped by type.
  const all: Source[] = [
    ...(c.question?.sources ?? []),
    ...statements(c).flatMap(([, s]) => s.sources),
    ...c.trends.flatMap((t) => t.points.map((p) => p.source)),
  ]
  const unique = [...new Map(all.map((s) => [s.reference, s])).values()]
  const groups = [...Map.groupBy(unique, (s: Source) => sourceType(s.reference))].sort((a, b) => b[1].length - a[1].length)

  return (
    <>
      <section className="card">
        <h3>Otázka pro komisi</h3>
        {c.question ? (
          <div className="nomination">
            <span className="eyebrow">Z nominace</span>
            <StatementView s={c.question} />
          </div>
        ) : (
          <p className="banner warn">
            <MissingIcon /> Nominace neobsahuje otázku pro komisi. Vyžádejte ji od navrhujícího lékaře a zapište jeho
            znění, jinak případ nelze projednat.
          </p>
        )}
        <label>
          Otázka, kterou bude komise řešit
          <textarea
            value={question}
            onChange={(e) => setQuestion(e.target.value)}
            onBlur={() => question !== prep.question && setPrep({ question })}
            placeholder="Znění od navrhujícího lékaře"
          />
        </label>
      </section>

      <section className="card">
        <h3>Konsolidovaný souhrn</h3>
        {c.summary.map((s, i) => S(`summary.${i}`, s))}
      </section>

      <section className="card">
        <h3>Otázky k diskusi</h3>
        {c.decision_support.questions.map((s, i) => S(`questions.${i}`, s))}
        {prep.questions.map((q, i) => (
          <div key={i} className="stmt human-q">
            <p>{q}</p>
            <div className="stmt-foot">
              <button className="link" onClick={() => setPrep({ questions: prep.questions.filter((_, j) => j !== i) })}>
                Odebrat
              </button>
            </div>
          </div>
        ))}
        <form
          className="row"
          onSubmit={(e) => {
            e.preventDefault()
            if (newQ.trim()) setPrep({ questions: [...prep.questions, newQ.trim()] })
            setNewQ('')
          }}
        >
          <input value={newQ} onChange={(e) => setNewQ(e.target.value)} placeholder="Vlastní otázka k diskusi" />
          <button type="submit">Přidat</button>
        </form>
      </section>

      <section className="card">
        <h3>Konsolidované zdroje</h3>
        <ul className="source-groups">
          {groups.map(([type, list]) => {
            const latest = list.map((s) => s.date).filter(Boolean).sort().pop()
            return (
              <li key={type}>
                <button className="link-row" onClick={() => show({ title: type, sources: list })}>
                  <Doc /> <span>{type}</span>
                  <strong>{list.length}</strong>
                </button>
                {latest && <small className="muted">poslední {fmtDate(latest)}</small>}
              </li>
            )
          })}
        </ul>
      </section>
    </>
  )
}
