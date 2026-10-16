import { useState } from 'react'
import type { Decision, Intent, Member } from './api'
import { Soon } from './CaseView'
import { Check, IntentIcon } from './icons'
import { fmtDate, fmtDateTime, INTENTS, SPECIALTIES } from './layout'
import { now } from './render'

type Props = {
  saved: Decision
  board: Member[] // prefills the attendees
  user: string
  onSave: (d: Decision) => Promise<void>
}

// Structured MDT resolution (brief, section C; template docs/template_zaver_zasedani). Written by
// humans only. The board decides by consensus: the coordinator ticks each attendee's consent and
// then locks it (decision #16); the backend refuses later changes.
export function DecisionForm({ saved, board, user, onSave }: Props) {
  const [d, setD] = useState<Decision>(() =>
    saved.attendees.length ? saved : { ...saved, attendees: board.map((m) => ({ name: m.name, specialty: SPECIALTIES[m.specialty] ?? m.specialty })) },
  )
  const missingConsent = d.attendees.filter((a) => !d.consent.includes(a.name)).length
  const lockable = d.attendees.length > 0 && d.attendees.every((a) => a.name.trim()) && !missingConsent
  const [status, setStatus] = useState('')
  const set = <K extends keyof Decision>(k: K, v: Decision[K]) => setD({ ...d, [k]: v })
  const setAttendee = (i: number, patch: Partial<Decision['attendees'][number]>) =>
    set('attendees', d.attendees.map((a, j) => (j === i ? { ...a, ...patch } : a)))

  if (saved.confirmed_by) return <LockedDecision d={saved} />

  const submit = async (confirm: boolean) => {
    const next = confirm ? { ...d, confirmed_by: user, confirmed_at: now() } : d
    try {
      await onSave(next)
      setStatus(confirm ? 'Závěr potvrzen a uzamčen' : `Koncept uložen ${new Date().toLocaleTimeString('cs-CZ')}`)
    } catch (e) {
      setStatus(`Neuloženo: ${(e as Error).message}`)
    }
  }

  return (
    <form className="decision" onSubmit={(e) => e.preventDefault()}>
      <fieldset>
        <legend>Přítomní členové komise a jejich souhlas *</legend>
        {d.attendees.map((a, i) => (
          <div key={i} className="row">
            <input aria-label="Jméno" value={a.name} onChange={(e) => setAttendee(i, { name: e.target.value })} />
            <select aria-label="Odbornost" value={a.specialty} onChange={(e) => setAttendee(i, { specialty: e.target.value })}>
              {Object.values(SPECIALTIES).map((s) => (
                <option key={s}>{s}</option>
              ))}
            </select>
            <label className="inline consent">
              <input
                type="checkbox"
                checked={d.consent.includes(a.name)}
                disabled={!a.name.trim()}
                onChange={(e) => set('consent', e.target.checked ? [...d.consent, a.name] : d.consent.filter((n) => n !== a.name))}
              />{' '}
              Souhlasí se závěrem
            </label>
            <button type="button" className="link" onClick={() => set('attendees', d.attendees.filter((_, j) => j !== i))}>
              Odebrat
            </button>
          </div>
        ))}
        <button type="button" onClick={() => set('attendees', [...d.attendees, { name: '', specialty: SPECIALTIES.surgery }])}>
          + Přidat člena
        </button>
      </fieldset>

      <fieldset className="intents">
        <legend>Cíl léčby *</legend>
        {(Object.keys(INTENTS) as Intent[]).map((k) => (
          <label key={k} className={`intent-card intent-${k} ${d.intent === k ? 'selected' : ''}`}>
            <input type="radio" name="intent" checked={d.intent === k} onChange={() => set('intent', k)} />
            <span className="intent-icon">
              <IntentIcon intent={k} />
            </span>
            <strong>{INTENTS[k].label}</strong>
            <small>{INTENTS[k].desc}</small>
          </label>
        ))}
      </fieldset>

      <label>
        Zvolený postup *
        <textarea value={d.plan} onChange={(e) => set('plan', e.target.value)} placeholder="Např. MR jater, poté resekce metastáz S6 a S7" />
      </label>
      <label>
        Zdůvodnění *
        <textarea value={d.rationale} onChange={(e) => set('rationale', e.target.value)} />
      </label>
      <label>
        Zvažované možnosti
        <textarea value={d.options_considered} onChange={(e) => set('options_considered', e.target.value)} />
      </label>

      <fieldset>
        <legend>Soulad s doporučenými postupy *</legend>
        <Soon>AI kontrola souladu závěru s doporučenými postupy.</Soon>
        <div className="segmented">
          <label className={d.guideline_compliant === true ? 'on' : ''}>
            <input type="radio" name="gl" checked={d.guideline_compliant === true} onChange={() => set('guideline_compliant', true)} /> Ano
          </label>
          <label className={d.guideline_compliant === false ? 'on' : ''}>
            <input type="radio" name="gl" checked={d.guideline_compliant === false} onChange={() => set('guideline_compliant', false)} /> Ne
          </label>
        </div>
        {d.guideline_compliant === false && (
          <label>
            Důvod odchylky *
            <textarea value={d.deviation_reason} onChange={(e) => set('deviation_reason', e.target.value)} />
          </label>
        )}
      </fieldset>


      <label>
        Odlišná stanoviska členů
        <textarea value={d.dissent} onChange={(e) => set('dissent', e.target.value)} />
      </label>
      <div className="row">
        <label className="grow">
          Zařazení do klinické studie
          <input value={d.trial} onChange={(e) => set('trial', e.target.value)} />
        </label>
        <label>
          Re-evaluace
          <input type="date" value={d.reevaluation ?? ''} onChange={(e) => set('reevaluation', e.target.value || null)} />
        </label>
      </div>

      <div className="actions">
        <button type="button" onClick={() => submit(false)}>
          Uložit koncept
        </button>
        <button
          type="button"
          className="primary"
          disabled={!user || !lockable}
          title={!user ? 'Zadejte své jméno vpravo nahoře' : !lockable ? 'Chybí souhlas všech přítomných členů' : ''}
          onClick={() => submit(true)}
        >
          <Check /> Uzamknout závěr (souhlas všech)
        </button>
        <span className="muted" role="status">
          {status}
        </span>
      </div>
    </form>
  )
}

function LockedDecision({ d }: { d: Decision }) {
  const rows: [string, string][] = [
    ['Zvolený postup', d.plan],
    ['Zdůvodnění', d.rationale],
    ['Zvažované možnosti', d.options_considered],
    ['Soulad s postupy', d.guideline_compliant ? 'Ano' : `Ne – ${d.deviation_reason}`],
    ['Odlišná stanoviska', d.dissent],
    ['Klinická studie', d.trial],
    ['Re-evaluace', d.reevaluation ? fmtDate(d.reevaluation) : ''],
    ['Přítomní a souhlasili', d.attendees.map((a) => `${a.name} (${a.specialty})`).join(', ')],
  ]
  return (
    <div className="locked">
      {d.intent && (
        <div className={`intent-banner intent-${d.intent}`}>
          <IntentIcon intent={d.intent} />
          <div>
            <strong>{INTENTS[d.intent].label} záměr</strong>
            <small>{INTENTS[d.intent].desc}</small>
          </div>
        </div>
      )}
      <dl>
        {rows
          .filter(([, v]) => v)
          .map(([k, v]) => (
            <div key={k}>
              <dt>{k}</dt>
              <dd>{v}</dd>
            </div>
          ))}
      </dl>
      <p className="done-line">
        <Check /> Konsenzus všech přítomných · zapsal {d.confirmed_by}, {d.confirmed_at && fmtDateTime(d.confirmed_at)} · záznam uzamčen
      </p>
    </div>
  )
}
