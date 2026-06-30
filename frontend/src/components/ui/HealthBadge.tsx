import { useEffect, useState } from 'react'
import { healthApi, type HealthResponse } from '@/utils/api'
import { cn } from '@/utils/cn'

type Status = 'loading' | 'ok' | 'error'

export default function HealthBadge() {
  const [status, setStatus] = useState<Status>('loading')
  const [data, setData] = useState<HealthResponse | null>(null)

  useEffect(() => {
    healthApi.status()
      .then((r) => { setData(r.data); setStatus('ok') })
      .catch(() => setStatus('error'))
  }, [])

  return (
    <div className="flex items-center gap-2">
      <span
        className={cn(
          'w-2 h-2 rounded-full',
          status === 'loading' && 'bg-amber-400 animate-pulse',
          status === 'ok'      && 'bg-emerald-400',
          status === 'error'   && 'bg-red-400',
        )}
      />
      <span className="text-xs text-gray-500">
        {status === 'loading' && 'Connecting…'}
        {status === 'ok'      && `API ${data?.status} · DB ${data?.database} · ${data?.llm_provider}`}
        {status === 'error'   && 'Backend unreachable'}
      </span>
    </div>
  )
}
