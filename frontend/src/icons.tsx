// Small stroke icons (16px grid, currentColor) so the visual language needs no icon library.
import type { ReactNode } from 'react'
import type { Intent } from './api'

const Icon = ({ children, label }: { children: ReactNode; label?: string }) => (
  <svg
    className="icon"
    viewBox="0 0 16 16"
    width="1em"
    height="1em"
    fill="none"
    stroke="currentColor"
    strokeWidth="1.5"
    strokeLinecap="round"
    strokeLinejoin="round"
    role={label ? 'img' : undefined}
    aria-label={label}
    aria-hidden={label ? undefined : true}
  >
    {children}
  </svg>
)

export const Robot = ({ label }: { label?: string }) => (
  <Icon label={label}>
    <path d="M8 1.8v1.7" />
    <rect x="2.5" y="3.5" width="11" height="8.5" rx="2.5" />
    <circle cx="6" cy="7.6" r="1" fill="currentColor" stroke="none" />
    <circle cx="10" cy="7.6" r="1" fill="currentColor" stroke="none" />
    <path d="M6.5 10h3M1 7v2.2M15 7v2.2" />
  </Icon>
)
export const Check = () => (
  <Icon>
    <path d="M3 8.5l3 3 7-7" />
  </Icon>
)
export const Alert = () => (
  <Icon>
    <path d="M8 2L1.5 13.5h13z" />
    <path d="M8 6.5v3M8 11.6v.1" />
  </Icon>
)
export const Doc = () => (
  <Icon>
    <path d="M4 1.5h5.5L12.5 4.5v10h-8.5z" />
    <path d="M9.5 1.5v3h3M6 8h4.5M6 10.5h4.5" />
  </Icon>
)
export const Download = () => (
  <Icon>
    <path d="M8 2v8M4.8 7 8 10.2 11.2 7" />
    <path d="M2.5 11v2.5h11V11" />
  </Icon>
)
export const Lock = () => (
  <Icon>
    <rect x="3" y="7" width="10" height="7.5" rx="1.5" />
    <path d="M5.5 7V5a2.5 2.5 0 0 1 5 0v2" />
  </Icon>
)
export const Reset = () => (
  <Icon>
    <path d="M2.5 8a5.5 5.5 0 1 0 1.6-3.9" />
    <path d="M2.5 1.8v2.7h2.7" />
  </Icon>
)
const INTENT_ICON: Record<Intent, ReactNode> = {
  curative: (
    <>
      <circle cx="8" cy="8" r="6" />
      <circle cx="8" cy="8" r="3" />
      <circle cx="8" cy="8" r=".6" fill="currentColor" />
    </>
  ),
  palliative: <path d="M8 13.5S2 10 2 5.8A3 3 0 0 1 8 4.5a3 3 0 0 1 6 1.3C14 10 8 13.5 8 13.5z" />,
  supportive: <path d="M8 2.5v11M2.5 8h11" />,
  deferred: <path d="M4.5 2h7M4.5 14h7M5 2c0 3.5 6 4 6 6s-6 2.5-6 6M11 2c0 3.5-6 4-6 6s6 2.5 6 6" />,
  surveillance: (
    <>
      <path d="M1.5 8S4 3.5 8 3.5 14.5 8 14.5 8 12 12.5 8 12.5 1.5 8 1.5 8z" />
      <circle cx="8" cy="8" r="2" />
    </>
  ),
}
export const IntentIcon = ({ intent }: { intent: Intent }) => <Icon>{INTENT_ICON[intent]}</Icon>
