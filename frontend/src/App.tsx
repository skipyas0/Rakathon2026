import { useEffect, useState } from 'react'
import { StatementView } from './StatementView'
import type { Statement } from './provenance'

// ponytail: placeholder example until the backend serves real statements.
const example: Statement = {
  text: 'Pacient hlásí v dotazníku únavu 8/10, hemoglobin klesl na 95 g/l.',
  origin: 'ai',
  model: 'example',
  sources: [
    { reference: 'Observation/hb-1', excerpt: 'Hb 95 g/l', date: '2026-10-01' },
    { reference: 'QuestionnaireResponse/proms-2', excerpt: 'Únava: 8', date: '2026-10-03' },
  ],
}

export default function App() {
  const [health, setHealth] = useState('…')
  useEffect(() => {
    fetch('/api/health')
      .then((r) => r.json())
      .then((d) => setHealth(d.status))
      .catch(() => setHealth('backend nedostupný'))
  }, [])

  return (
    <main>
      <h1>MDT Copilot</h1>
      <p>Backend: {health}</p>
      <StatementView s={example} />
      <StatementView s={{ ...example, confirmed_by: 'MUDr. Ukázka' }} />
    </main>
  )
}
