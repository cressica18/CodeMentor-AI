import { Link } from 'react-router-dom'
import { Brain, Flame, TrendingUp, BookOpen, Sparkles, Award, RefreshCw } from 'lucide-react'
import { useActiveHandle } from '@/hooks/useActiveHandle'
import { useMemoryOverview } from '@/hooks/useMemoryOverview'
import HandleGate from '@/components/memory/HandleGate'
import { ChartSkeleton, StatCardSkeleton } from '@/components/ui/Skeleton'

export default function MemoryOverviewPage() {
  const { handle, setHandle } = useActiveHandle()
  const { status, overview, error, refresh } = useMemoryOverview(handle)

  return (
    <div className="p-6 max-w-6xl mx-auto">
      <div className="mb-6">
        <div className="flex items-center gap-3 mb-2">
          <div className="w-9 h-9 rounded-xl bg-brand-600 flex items-center justify-center">
            <Brain size={18} className="text-white" />
          </div>
          <h1 className="text-xl font-bold text-white">Mentor Memory</h1>
        </div>
        <p className="text-sm text-gray-400">
          Everything CodeMentor AI remembers about your learning journey — persisted across sessions, ready for
          future agents to use.
        </p>
      </div>

      <HandleGate initial={handle} onSubmit={setHandle} />

      {!handle && (
        <div className="card p-8 text-center text-sm text-gray-500">
          Enter a Codeforces handle above to view its stored memory.
        </div>
      )}

      {handle && status === 'loading' && (
        <div className="space-y-6">
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
            {[...Array(4)].map((_, i) => <StatCardSkeleton key={i} />)}
          </div>
          <ChartSkeleton height={200} />
        </div>
      )}

      {handle && status === 'error' && (
        <div className="card p-6 text-sm text-red-300 border-red-700/40">
          {error ?? 'No memory found for this handle yet — register the user via the Profile page first.'}
        </div>
      )}

      {handle && status === 'success' && overview && (
        <div className="space-y-6">
          {/* Top stats */}
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
            <StatTile
              icon={Flame}
              label="Current Streak"
              value={`${overview.profile?.current_streak_days ?? 0}d`}
              sub={`Best: ${overview.profile?.longest_streak_days ?? 0}d`}
            />
            <StatTile
              icon={TrendingUp}
              label="Improvement"
              value={
                overview.profile?.improvement_velocity != null
                  ? `${overview.profile.improvement_velocity > 0 ? '+' : ''}${overview.profile.improvement_velocity.toFixed(1)}/day`
                  : '—'
              }
              sub="rating velocity"
            />
            <StatTile
              icon={BookOpen}
              label="Topics Tracked"
              value={String(overview.topic_ratings.length)}
              sub={`${overview.topic_ratings.filter((t) => t.is_weakness).length} weak`}
            />
            <StatTile
              icon={Sparkles}
              label="Recommendations"
              value={String(overview.profile?.historical_recommendation_count ?? 0)}
              sub="lifetime stored"
            />
          </div>

          {/* Learning path */}
          <div className="card p-5">
            <div className="flex items-center justify-between mb-3">
              <h2 className="text-sm font-semibold text-white flex items-center gap-2">
                <BookOpen size={15} className="text-brand-400" /> Learning Path
              </h2>
              <Link to="/roadmap" className="text-xs text-brand-400 hover:underline">
                View full path →
              </Link>
            </div>
            {overview.learning_path?.current_stage ? (
              <>
                <p className="text-sm text-gray-300 mb-2">
                  Current stage: <span className="text-white font-medium">{overview.learning_path.current_stage}</span>
                </p>
                <div className="w-full h-2 rounded-full bg-[#16161d] overflow-hidden">
                  <div
                    className="h-full bg-brand-600 transition-all"
                    style={{ width: `${overview.learning_path.progress_percent}%` }}
                  />
                </div>
                <p className="text-xs text-gray-500 mt-1">{overview.learning_path.progress_percent}% complete</p>
              </>
            ) : (
              <p className="text-sm text-gray-500">No learning path set yet.</p>
            )}
          </div>

          {/* Topic ratings */}
          <div className="card p-5">
            <h2 className="text-sm font-semibold text-white mb-3">Topic Skill Ratings</h2>
            {overview.topic_ratings.length === 0 ? (
              <p className="text-sm text-gray-500">No topic ratings recorded yet.</p>
            ) : (
              <div className="space-y-2">
                {overview.topic_ratings.map((t) => (
                  <div key={t.id} className="flex items-center gap-3">
                    <span className="text-xs text-gray-400 w-32 truncate">{t.topic}</span>
                    <div className="flex-1 h-2 rounded-full bg-[#16161d] overflow-hidden">
                      <div
                        className={`h-full ${t.is_strength ? 'bg-emerald-500' : t.is_weakness ? 'bg-red-500' : 'bg-brand-500'}`}
                        style={{ width: `${Math.min(100, Math.round(t.rating * 100))}%` }}
                      />
                    </div>
                    <span className="text-xs text-gray-500 w-10 text-right">{Math.round(t.rating * 100)}%</span>
                  </div>
                ))}
              </div>
            )}
          </div>

          {/* Recommendations + Milestones */}
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            <div className="card p-5">
              <h2 className="text-sm font-semibold text-white mb-3">Stored Recommendations</h2>
              {overview.recent_recommendations.length === 0 ? (
                <p className="text-sm text-gray-500">None yet.</p>
              ) : (
                <ul className="space-y-2">
                  {overview.recent_recommendations.map((r) => (
                    <li key={r.id} className="text-sm text-gray-300 flex items-center justify-between">
                      <span className="truncate pr-2">{r.reason ?? r.rec_type}</span>
                      <span className="badge-blue">{r.status}</span>
                    </li>
                  ))}
                </ul>
              )}
            </div>

            <div className="card p-5">
              <h2 className="text-sm font-semibold text-white mb-3 flex items-center gap-2">
                <Award size={15} className="text-amber-400" /> Milestones
              </h2>
              {overview.recent_milestones.length === 0 ? (
                <p className="text-sm text-gray-500">No milestones yet.</p>
              ) : (
                <ul className="space-y-2">
                  {overview.recent_milestones.map((m) => (
                    <li key={m.id} className="text-sm text-gray-300">
                      {m.title}
                    </li>
                  ))}
                </ul>
              )}
            </div>
          </div>

          <button onClick={refresh} className="btn-secondary flex items-center gap-2 text-sm">
            <RefreshCw size={14} /> Refresh memory
          </button>
        </div>
      )}
    </div>
  )
}

function StatTile({
  icon: Icon,
  label,
  value,
  sub,
}: {
  icon: React.ElementType
  label: string
  value: string
  sub?: string
}) {
  return (
    <div className="card p-4">
      <div className="flex items-center gap-2 text-gray-500 text-xs mb-2">
        <Icon size={13} /> {label}
      </div>
      <p className="text-xl font-bold text-white">{value}</p>
      {sub && <p className="text-xs text-gray-500 mt-0.5">{sub}</p>}
    </div>
  )
}
