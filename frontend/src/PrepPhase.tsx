import { useState } from 'react'
import type { CaseRecord } from './api'
import { type Case, statements } from './briefing'
import { FlagItem, MissingItem } from './CaseView'
import { confirmer, isPending, missing, now, renderer } from './render'
import { Alert as AlertIcon, Arrow, Check, Doc, Missing as MissingIcon, Robot } from './icons'
import { fmtDate, fmtDateTime, type Phase, SEVERITY_RANK } from './layout'
import type { Source } from './provenance'
import { sourceType, useSources } from './sources'
import { StatementView } from './StatementView'

type Props = {
  c: Case
  record: CaseRecord
  save: (r: CaseRecord) => void
  user: string
  go: (p: Phase) => void
}

/** Phase 1: consolidate sources, surface problems, settle the question for the board. */
export function PrepPhase({ c, record, save, user, go }: Props) {
  const show = useSources()
  const S = renderer(record, confirmer(record, save, user))
  const [question, setQuestion] = useState(record.prep.question || c.question?.text || '')
  const [newQ, setNewQ] = useState('')
  const prep = record.prep
  const setPrep = (p: Partial<CaseRecord['prep']>) => save({ ...record, prep: { ...prep, ...p } })

  const ai = statements(c).filter(([, s]) => s.origin === 'ai' && !s.confirmed_by)
  const done = ai.filter(([k, s]) => !isPending(record, k, s)).length
  const gaps = missing(c)
  const hasQuestion = !!question.trim()

  // Consolidated sources: every record referenced anywhere in the briefing, grouped by type.
  const all: Source[] = [
    ...(c.question?.sources ?? []),
    ...statements(c).flatMap(([, s]) => s.sources),
    ...c.trends.flatMap((t) => t.points.map((p) => p.source)),
  ]
  const unique = [...new Map(all.map((s) => [s.reference, s])).values()]
  const groups = [...Map.groupBy(unique, (s: Source) => sourceType(s.reference))].sort((a, b) => b[1].length - a[1].length)

  return (
    <div className="phase-grid">
      <div className="phase-main">
        <section className="card">
          <h3>Otázka pro komisi</h3>
          {c.question ? (
            <div className="nomination">
              <span className="eyebrow">Z nominace</span>
              <StatementView s={c.question} />
            </div>
          ) : (
            <p className="banner warn">
              <MissingIcon /> Nominace neobsahuje otázku pro komisi. Doplňte ji po konzultaci s navrhujícím lékařem, jinak
              případ nelze projednat.
            </p>
          )}
          <label>
            Otázka, kterou bude komise řešit
            <textarea
              value={question}
              onChange={(e) => setQuestion(e.target.value)}
              onBlur={() => question !== prep.question && setPrep({ question })}
              placeholder="Např. Resekabilita jaterních metastáz versus změna systémové léčby?"
            />
          </label>
        </section>

        <section className="card">
          <h3>K vyřešení před zasedáním</h3>
          <p className="muted small">Rozpory mezi zdroji a chybějící údaje. Ověřte a potvrďte, nebo nechte doplnit.</p>
          {[...c.red_flags.entries()]
            .sort(([, a], [, b]) => SEVERITY_RANK[a.severity] - SEVERITY_RANK[b.severity])
            .map(([i, f]) => (
              <FlagItem key={i} f={f} i={i} S={S} />
            ))}
          {gaps.map(([k, s]) => (
            <MissingItem key={k} k={k} s={s} S={S} />
          ))}
          {!c.red_flags.length && !gaps.length && <p className="muted">Žádné problémy nenalezeny.</p>}
        </section>

        <section className="card">
          <h3>Konsolidovaný souhrn</h3>
          {c.summary.map((s, i) => S(`summary.${i}`, s))}
        </section>

        <section className="card">
          <h3>Otázky k diskusi</h3>
          <p className="muted small">Návrhy AI potvrďte, pokud je chcete na zasedání. Můžete přidat vlastní.</p>
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
      </div>

      <aside className="phase-aside">
        <section className="card readiness">
          <h3>Připravenost případu</h3>
          <ul className="checklist">
            <li className={hasQuestion ? 'ok' : 'bad'}>
              {hasQuestion ? <Check /> : <MissingIcon />} Otázka pro komisi
            </li>
            <li className={c.red_flags.some((f) => f.severity === 'high') ? 'warn' : 'ok'}>
              {c.red_flags.some((f) => f.severity === 'high') ? <AlertIcon /> : <Check />} {c.red_flags.length} upozornění,{' '}
              {gaps.length} chybějících údajů
            </li>
            <li className={done === ai.length ? 'ok' : 'warn'}>
              <Robot /> Potvrzeno {done} z {ai.length} návrhů AI
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
              disabled={!hasQuestion || !user}
              title={!user ? 'Zadejte své jméno vpravo nahoře' : !hasQuestion ? 'Chybí otázka pro komisi' : ''}
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
      </aside>
    </div>
  )
}
