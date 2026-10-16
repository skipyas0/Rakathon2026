import { createContext, useContext } from 'react'
import type { Source } from './provenance'

export type Shown = { title: string; sources: Source[]; ai?: string | null }
export const SourcesContext = createContext<(s: Shown) => void>(() => {})

/** Opens the side panel with the exact source records behind a statement or data point. */
export const useSources = () => useContext(SourcesContext)

const TYPE: Record<string, string> = {
  DiagnosticReport: 'Lékařská zpráva',
  Observation: 'Laboratoř / měření',
  QuestionnaireResponse: 'Dotazník pacienta (PROMs)',
  MedicationAdministration: 'Podaná léčba',
  MedicationStatement: 'Medikace',
  Procedure: 'Výkon',
  Condition: 'Diagnóza',
  ServiceRequest: 'Nominace na MDT',
  guideline: 'Doporučený postup',
  trial: 'Klinická studie',
}
export const sourceType = (ref: string) => {
  const t = ref.split(/[/:]/)[0]
  return TYPE[t] ?? t
}
