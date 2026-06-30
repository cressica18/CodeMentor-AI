import { useCallback, useState } from 'react'

const STORAGE_KEY = 'codementor:active_handle'

/**
 * Phase 3 — lightweight shared state for "which CF handle's memory am I
 * looking at" across the new memory pages (Profile, History, Progress,
 * Learning Path, Preferences). Backed by localStorage so it survives
 * navigation/refresh without needing a global store.
 */
export function useActiveHandle() {
  const [handle, setHandleState] = useState<string>(() => {
    try {
      return localStorage.getItem(STORAGE_KEY) ?? ''
    } catch {
      return ''
    }
  })

  const setHandle = useCallback((value: string) => {
    const trimmed = value.trim()
    setHandleState(trimmed)
    try {
      if (trimmed) localStorage.setItem(STORAGE_KEY, trimmed)
    } catch {
      // ignore storage failures (e.g. private browsing)
    }
  }, [])

  return { handle, setHandle }
}
