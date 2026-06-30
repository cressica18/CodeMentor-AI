import { useEffect, useState } from 'react'
import { BookOpen, Save } from 'lucide-react'
import { useActiveHandle } from '@/hooks/useActiveHandle'
import { memoryApi, type LearningPath } from '@/utils/api'
import HandleGate from '@/components/memory/HandleGate'
import { ChartSkeleton } from '@/components/ui/Skeleton'

export default function LearningPathPage() {
  const { handle, setHandle } = useActiveHandle()
  const [path, setPath] = useState<LearningPath | null>(null)
  const [loading, setLoading] = useState(false)
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const [goal, setGoal] = useState('')
  const [stage, setStage] = useState('')
  const [progress, setProgress] = useState('0')

  const load = async (h: string) => {
    setLoading(true)
    setError(null)
    try {
      const res = await memoryApi.getLearningPath(h)
      setPath(res.data)
      setGoal(res.data.goal ?? '')
      setStage(res.data.current_stage ?? '')
      setProgress(String(res.data.progress_percent ?? 0))
    } catch (err: any) {
      setError(err?.message ?? 'Failed to load learning path')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    if (handle) load(handle)
  }, [handle])

  const handleSave = async () => {
    if (!handle) return
    setSaving(true)
    try {
      const res = await memoryApi.updateLearningPath(handle, {
        goal,
        current_stage: stage,
        progress_percent: Number(progress) || 0,
      })
      setPath(res.data)
    } finally {
      setSaving(false)
    }
  }

  return (
    <div className="p-6 max-w-3xl mx-auto">
      <div className="mb-6">
        <div className="flex items-center gap-3 mb-2">
          <div className="w-9 h-9 rounded-xl bg-brand-600 flex items-center justify-center">
            <BookOpen size={18} className="text-white" />
          </div>
          <h1 className="text-xl font-bold text-white">Learning Path</h1>
        </div>
        <p className="text-sm text-gray-400">
          Persisted adaptive path state. The Planner Agent (a later phase) will generate this automatically —
          for now it's stored and editable directly.
        </p>
      </div>

      <HandleGate initial={handle} onSubmit={setHandle} />

      {!handle && <div className="card p-8 text-center text-sm text-gray-500">Enter a handle to view its learning path.</div>}
      {handle && loading && <ChartSkeleton height={180} />}
      {handle && !loading && error && <div className="card p-6 text-sm text-red-300 border-red-700/40">{error}</div>}

      {handle && !loading && path && (
        <div className="card p-5 space-y-4">
          <div className="w-full h-2 rounded-full bg-[#16161d] overflow-hidden">
            <div className="h-full bg-brand-600 transition-all" style={{ width: `${Number(progress) || 0}%` }} />
          </div>

          <div>
            <label className="text-xs text-gray-400 mb-1 block">Goal</label>
            <input value={goal} onChange={(e) => setGoal(e.target.value)} className="input w-full" placeholder="e.g. Reach 1900 rating by Q4" />
          </div>
          <div>
            <label className="text-xs text-gray-400 mb-1 block">Current stage</label>
            <input value={stage} onChange={(e) => setStage(e.target.value)} className="input w-full" placeholder="e.g. Segment Trees" />
          </div>
          <div>
            <label className="text-xs text-gray-400 mb-1 block">Progress (%)</label>
            <input
              type="number"
              min={0}
              max={100}
              value={progress}
              onChange={(e) => setProgress(e.target.value)}
              className="input w-32"
            />
          </div>

          <button onClick={handleSave} disabled={saving} className="btn-primary flex items-center gap-2 text-sm">
            <Save size={14} /> {saving ? 'Saving…' : 'Save path'}
          </button>

          {path.state && Object.keys(path.state).length > 0 && (
            <div className="pt-2 border-t border-[#2a2a3a]">
              <p className="text-xs text-gray-500 mb-1">Stored state (raw)</p>
              <pre className="text-xs text-gray-400 bg-[#16161d] rounded-lg p-3 overflow-x-auto">
                {JSON.stringify(path.state, null, 2)}
              </pre>
            </div>
          )}
        </div>
      )}
    </div>
  )
}
