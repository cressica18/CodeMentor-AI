import { useEffect, useState } from 'react'
import { Target, RefreshCw, Sparkles } from 'lucide-react'
import HandleGate from '@/components/memory/HandleGate'
import ProblemCard from '@/components/recommendations/ProblemCard'
import { ProfileLoadingSkeleton } from '@/components/ui/Skeleton'
import { useActiveHandle } from '@/hooks/useActiveHandle'
import { recommendationsApi, type RecommendedProblem } from '@/utils/api'
import { cn } from '@/utils/cn'

type FilterTab = 'pending' | 'solved' | 'bookmarked'

const TABS: { key: FilterTab; label: string }[] = [
  { key: 'pending', label: 'Pending' },
  { key: 'solved', label: 'Solved' },
  { key: 'bookmarked', label: 'Bookmarked' },
]

export default function ProblemRecommendationsPage() {
  const { handle, setHandle } = useActiveHandle()
  const [tab, setTab] = useState<FilterTab>('pending')
  const [problems, setProblems] = useState<RecommendedProblem[]>([])
  const [loading, setLoading] = useState(false)
  const [generating, setGenerating] = useState(false)
  const [actionBusy, setActionBusy] = useState<number | null>(null)
  const [error, setError] = useState<string | null>(null)

  const load = async (h: string, status: FilterTab) => {
    setLoading(true)
    setError(null)
    try {
      const res = await recommendationsApi.list(h, status)
      setProblems(res.data)
    } catch (err: any) {
      setError(err?.message ?? 'Failed to load recommendations.')
      setProblems([])
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    if (handle) load(handle, tab)
  }, [handle, tab])

  const handleGenerate = async () => {
    if (!handle) return
    setGenerating(true)
    setError(null)
    try {
      await recommendationsApi.generate(handle)
      await load(handle, tab)
    } catch (err: any) {
      setError(err?.message ?? 'Failed to generate recommendations — try running the mentor workflow from the home page first.')
    } finally {
      setGenerating(false)
    }
  }

  const refresh = () => handle && load(handle, tab)

  const runAction = async (id: number, fn: () => Promise<unknown>) => {
    setActionBusy(id)
    try {
      await fn()
      await refresh()
    } finally {
      setActionBusy(null)
    }
  }

  return (
    <div className="p-6 max-w-6xl mx-auto">
      <div className="mb-6 flex items-start justify-between gap-4 flex-wrap">
        <div>
          <div className="flex items-center gap-3 mb-2">
            <div className="w-9 h-9 rounded-xl bg-brand-600 flex items-center justify-center">
              <Target size={18} className="text-white" />
            </div>
            <h1 className="text-xl font-bold text-white">Problem Recommendations</h1>
          </div>
          <p className="text-sm text-gray-400">
            Real Codeforces problems chosen by the Problem Recommender Agent — reinforcement, advancement, recovery, and contest-prep picks.
          </p>
        </div>
        {handle && (
          <button onClick={handleGenerate} disabled={generating} className="btn-primary flex items-center gap-2 text-xs">
            <Sparkles size={13} className={generating ? 'animate-pulse' : ''} />
            {generating ? 'Generating…' : 'Generate New Recommendations'}
          </button>
        )}
      </div>

      <HandleGate initial={handle} onSubmit={setHandle} />

      {!handle && (
        <div className="card p-8 text-center text-sm text-gray-500">
          Enter a Codeforces handle to view its recommended problems.
        </div>
      )}

      {handle && (
        <>
          <div className="flex items-center gap-2 mb-5">
            {TABS.map((t) => (
              <button
                key={t.key}
                onClick={() => setTab(t.key)}
                className={cn(
                  'text-xs font-medium px-3 py-1.5 rounded-lg transition-colors',
                  tab === t.key ? 'bg-brand-600 text-white' : 'bg-white/5 text-gray-400 hover:bg-white/10'
                )}
              >
                {t.label}
              </button>
            ))}
            <button onClick={refresh} className="ml-auto text-gray-500 hover:text-gray-300" title="Refresh">
              <RefreshCw size={14} />
            </button>
          </div>

          {error && (
            <div className="card p-4 text-sm text-red-300 border-red-700/40 mb-4">{error}</div>
          )}

          {loading ? (
            <ProfileLoadingSkeleton />
          ) : problems.length === 0 ? (
            <div className="card p-8 text-center text-sm text-gray-500">
              No {tab} problems yet. {tab === 'pending' && 'Click "Generate New Recommendations" above.'}
            </div>
          ) : (
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
              {problems.map((p) => (
                <ProblemCard
                  key={p.id}
                  problem={p}
                  onSolve={(id) => runAction(id, () => recommendationsApi.updateStatus(id, 'solve'))}
                  onSkip={(id) => runAction(id, () => recommendationsApi.updateStatus(id, 'skip'))}
                  onToggleBookmark={(id, bookmarked) =>
                    runAction(id, () => recommendationsApi.updateStatus(id, bookmarked ? 'bookmark' : 'unbookmark'))
                  }
                  busy={actionBusy === p.id}
                />
              ))}
            </div>
          )}
        </>
      )}
    </div>
  )
}
