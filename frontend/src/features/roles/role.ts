// Who uses the app in this browser: the coordinator or one of the board specialists
// (docs/workflow-plan.md). ponytail: picked, not authenticated (one shared password); per-user
// login when a stance must be attributable to a signed-in clinician.
import { load, save } from '../../layout'

/** The 4 specialist roles of the process doc; the id is the board specialty and the section id. */
export const ROLES = ['surgery', 'oncology', 'radiology', 'pathology']

/** '' = the coordinator. */
export const getRole = () => {
  const r = load('mdt.role', '')
  return ROLES.includes(r) ? r : ''
}
export const setRole = (role: string) => save('mdt.role', role)

/** A specialist's journey through one case, at #/case/<id>/<step> like the coordinator's. */
export const SPECIALIST_STEPS = [
  { id: 'patient', label: 'Pacient' },
  { id: 'facts', label: 'Klíčové informace' },
  { id: 'stanovisko', label: 'Stanovisko' },
] as const
export type SpecialistStep = (typeof SPECIALIST_STEPS)[number]['id']
