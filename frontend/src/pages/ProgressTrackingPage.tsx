import { useEffect, useState } from 'react'
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from 'recharts'
import { TrendingUp, Camera } from 'lucide-react'
import { useActiveHandle } from '@/hooks/useActiveHandle'
import { memoryApi, type ProgressSnapshot } from '@/utils/api'
import HandleGate from '@/components/memory/HandleGate'
import { ChartSkeleton } from '@/components/ui/Skeleton'

export default function ProgressTrackingPage() {
  const { handle, setHandle } = useActiveHandle()
  const [snapshots, setSnapshots] = useState<ProgressSnapshot[]>([])
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [capturing, setCapturing] = useState(false)

  const load = async (h: string) => {
    setLoading(true)
    setError(null)
    try {
      const res = await memoryApi.getProgressSnapshots(h)
      setSnapshots([...res.data].reverse())
    } catch (err: any) {
      setError(err?.message ?? 'Failed to load progress data')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    if (handle) load(handle)
  }, [handle])

  const handleCapture = async () => {
    if (!handle) return
    setCapturing(true)
    try {
      await memoryApi.createProgressSnapshot(handle)
      await load(handle)
    } catch (err: any) {
      setError(err?.message ?? 'Failed to capture snapshot (ingest a CF profile for this handle first)')
    } finally {
      setCapturing(false)
    }
  }

  const chartData = snapshots.map((s) => ({
    date: new Date(s.snapshot_at).toLocaleDateString(),
    rating: s.rating,
  }))

  return (
    <div className="p-6 max-w-5xl mx-auto">
      <div className="mb-6">
        <div className="flex items-center gap-3 mb-2">
          <div className="w-9 h-9 rounded-xl bg-brand-600 flex items-center justify-center">
            <TrendingUp size={18} className="text-white" />
          </div>
          <h1 className="text-xl font-bold text-white">Progress Tracking</h1>
        </div>
        <p className="text-sm text-gray-400">Historical snapshots used to compute improvement velocity over time.</p>
      </div>

      <HandleGate initial={handle} onSubmit={setHandle} />

      {!handle && <div className="card p-8 text-center text-sm text-gray-500">Enter a handle to view its progress.</div>}
      {handle && loading && <ChartSkeleton height={260} />}
      {handle && !loading && error && <div className="card p-6 text-sm text-red-300 border-red-700/40 mb-4">{error}</div>}

      {handle && !loading && (
        <div className="space-y-6">
          <div className="card p-5">
            <div className="flex items-center justify-between mb-4">
              <h2 className="text-sm font-semibold text-white">Rating Snapshots</h2>
              <button onClick={handleCapture} disabled={capturing} className="btn-secondary flex items-center gap-2 text-xs">
                <Camera size={13} /> {capturing ? 'Capturing…' : 'Capture snapshot now'}
              </button>
            </div>

            {chartData.length === 0 ? (
              <p className="text-sm text-gray-500">No snapshots yet — capture one to start tracking progress.</p>
            ) : (
              <ResponsiveContainer width="100%" height={260}>
                <LineChart data={chartData}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#2a2a3a" />
                  <XAxis dataKey="date" tick={{ fontSize: 11, fill: '#9ca3af' }} />
                  <YAxis tick={{ fontSize: 11, fill: '#9ca3af' }} domain={['auto', 'auto']} />
                  <Tooltip
                    contentStyle={{ background: '#1c1c26', border: '1px solid #2a2a3a', borderRadius: 8, fontSize: 12 }}
                  />
                  <Line type="monotone" dataKey="rating" stroke="#818cf8" strokeWidth={2} dot={{ r: 3 }} />
                </LineChart>
              </ResponsiveContainer>
            )}
          </div>

          {snapshots.length > 0 && (
            <div className="card p-5">
              <h2 className="text-sm font-semibold text-white mb-3">Snapshot Log</h2>
              <ul className="divide-y divide-[#2a2a3a]">
                {[...snapshots].reverse().map((s) => (
                  <li key={s.id} className="py-2 flex items-center justify-between text-sm">
                    <span className="text-gray-400">{new Date(s.snapshot_at).toLocaleString()}</span>
                    <span className="text-gray-200">{s.rating ?? '—'}</span>
                  </li>
                ))}
              </ul>
            </div>
          )}
        </div>
      )}
    </div>
  )
}
