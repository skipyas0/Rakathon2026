// Whether the current screen has input it hasn't saved, so leaving it asks first (App guards every
// navigation: chevrons, top bar, role pick, Předchozí, closing the tab). Buttons that save clear it.
import { useEffect } from 'react'

let dirty = false

export const setUnsaved = (d: boolean) => {
  dirty = d
}
export const hasUnsaved = () => dirty

/** True when there's nothing to lose or the user agrees to lose it. */
export function mayLeave() {
  if (dirty && !window.confirm('Máte neuložené změny. Odejít bez uložení?')) return false
  dirty = false
  return true
}

/** A screen reports its unsaved input while it's shown. */
export function useUnsaved(isDirty: boolean) {
  useEffect(() => {
    setUnsaved(isDirty)
    return () => setUnsaved(false)
  }, [isDirty])
}
