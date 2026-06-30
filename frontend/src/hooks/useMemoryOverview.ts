import { useCallback, useEffect, useState } from 'react'
import { memoryApi, type MemoryOverview } from '@/utils/api'

export type MemoryStatus = 'idle' | 'loading' | 'success' | 'error'

export function useMemoryOverview(handle: string) {
  const [status, setStatus] = useState<MemoryStatus>('idle')
  const [overview, setOverview] = useState<MemoryOverview | null>(null)
  const [error, setError] = useState<string | null>(null)

  const refresh = useCallback(async (h: string) => {
    if (!h) return
    setStatus('loading')
    setError(null)
    try {
      const res = await memoryApi.getOverview(h)
      setOverview(res.data)
      setStatus('success')
    } catch (err: any) {
      setError(err?.message ?? 'Failed to load memory data')
      setStatus('error')
      setOverview(null)
    }
  }, [])

  useEffect(() => {
    if (handle) refresh(handle)
  }, [handle, refresh])

  return { status, overview, error, refresh: () => refresh(handle) }
}
