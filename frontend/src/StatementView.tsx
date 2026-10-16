import type { Statement } from './provenance'

// The one way to render clinical content. AI output is visibly marked until a clinician confirms it,
// and every source is one click away. Don't render Statement.text anywhere without this component.
export function StatementView({ s }: { s: Statement }) {
  const pending = s.origin === 'ai' && !s.confirmed_by
  return (
    <div className={`statement ${s.origin} ${pending ? 'pending' : ''}`}>
      {s.origin === 'ai' && <span className="badge">AI{pending ? ' · nepotvrzeno' : ''}</span>}
      <p>{s.text}</p>
      {s.confirmed_by && <small>Potvrdil: {s.confirmed_by}</small>}
      {s.sources.length > 0 && (
        <details>
          <summary>Zdroje ({s.sources.length})</summary>
          <ul>
            {s.sources.map((src) => (
              <li key={src.reference}>
                <code>{src.reference}</code> {src.date} {src.author}
                {src.excerpt && <blockquote>{src.excerpt}</blockquote>}
              </li>
            ))}
          </ul>
        </details>
      )}
    </div>
  )
}
