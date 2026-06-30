import { useState, useCallback } from 'react'
import { codeforcesApi, type CFProfileResponse } from '@/utils/api'

export type IngestStatus = 'idle' | 'loading' | 'success' | 'error'

export function useCFProfile() {
  const [status, setStatus] = useState<IngestStatus>('idle')
  const [profile, setProfile] = useState<CFProfileResponse | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [handle, setHandle] = useState<string>('')

  const ingest = useCallback(async (inputHandle: string, forceRefresh = false) => {
    const trimmed = inputHandle.trim()
    if (!trimmed) return

    setStatus('loading')
    setError(null)
    setHandle(trimmed)

    try {
      const res = await codeforcesApi.ingest(trimmed, forceRefresh)
      setProfile(res.data)
      setStatus('success')
    } catch (err: any) {
      const msg = err?.message ?? 'Failed to fetch profile'
      setError(msg)
      setStatus('error')
    }
  }, [])

  const reset = useCallback(() => {
    setStatus('idle')
    setProfile(null)
    setError(null)
    setHandle('')
  }, [])

  return { status, profile, error, handle, ingest, reset }
}
