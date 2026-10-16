// Mirror of backend/src/mdt_backend/provenance.py. Keep both in sync (see AGENTS.md).

export type Source = {
  reference: string
  excerpt?: string | null
  date?: string | null
  author?: string | null
}

export type Statement = {
  text: string
  origin: 'ai' | 'human'
  sources: Source[]
  model?: string | null
  confirmed_by?: string | null
  confirmed_at?: string | null
}
