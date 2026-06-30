import { useState, FormEvent } from 'react'
import { Search, AlertCircle, Code2, TrendingUp, Tag, BarChart3, Activity, Zap } from 'lucide-react'
import { useCFProfile } from '@/hooks/useCFProfile'
import CFProfileCard from '@/components/codeforces/CFProfileCard'
import RatingChart from '@/components/codeforces/RatingChart'
import { TopicSolvedChart, WeaknessStrengthPanel } from '@/components/codeforces/TagCharts'
import DifficultyChart from '@/components/codeforces/DifficultyChart'
import ActivityHeatmap from '@/components/codeforces/ActivityHeatmap'
import { ProfileLoadingSkeleton } from '@/components/ui/Skeleton'

const POPULAR_HANDLES = ['tourist', 'Um_nik', 'jiangly', 'neal', 'Petr']

export default function CFProfilePage() {
  const [inputHandle, setInputHandle] = useState('')
  const { status, profile, error, ingest } = useCFProfile()

  const handleSubmit = (e: FormEvent) => {
    e.preventDefault()
    if (inputHandle.trim()) ingest(inputHandle)
  }

  const handleRefresh = () => {
    if (profile) ingest(profile.handle, true)
  }

  return (
    <div className="p-6 max-w-5xl mx-auto">
      {/* Page header */}
      <div className="mb-6">
        <div className="flex items-center gap-3 mb-2">
          <div className="w-9 h-9 rounded-xl bg-brand-600 flex items-center justify-center">
            <Code2 size={18} className="text-white" />
          </div>
          <h1 className="text-xl font-bold text-white">Codeforces Analytics</h1>
        </div>
        <p className="text-sm text-gray-400">
          Analyse any Codeforces profile — rating history, topic strengths, activity, and more.
        </p>
      </div>

      {/* Search form */}
      <form onSubmit={handleSubmit} className="mb-6">
        <div className="flex gap-3">
          <div className="relative flex-1">
            <Search
              size={16}
              className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-500 pointer-events-none"
            />
            <input
              type="text"
              value={inputHandle}
              onChange={(e) => setInputHandle(e.target.value)}
              placeholder="Enter Codeforces handle, e.g. tourist"
              className="input w-full pl-9 pr-4 py-2.5"
              disabled={status === 'loading'}
              autoFocus
            />
          </div>
          <button
            type="submit"
            disabled={!inputHandle.trim() || status === 'loading'}
            className="btn-primary px-5 flex items-center gap-2 disabled:opacity-50 disabled:cursor-not-allowed"
          >
            {status === 'loading' ? (
              <>
                <span className="w-4 h-4 border-2 border-white/30 border-t-white rounded-full animate-spin" />
                Fetching…
              </>
            ) : (
              <>
                <Zap size={14} />
                Analyse
              </>
            )}
          </button>
        </div>

        {/* Quick handles */}
        {status === 'idle' && (
          <div className="flex items-center gap-2 mt-3 flex-wrap">
            <span className="text-xs text-gray-600">Try:</span>
            {POPULAR_HANDLES.map((h) => (
              <button
                key={h}
                type="button"
                onClick={() => { setInputHandle(h); ingest(h) }}
                className="text-xs px-2.5 py-1 rounded-full bg-[#1c1c26] border border-[#2a2a3a]
                           text-gray-400 hover:text-brand-400 hover:border-brand-600/40 transition-colors"
              >
                {h}
              </button>
            ))}
          </div>
        )}
      </form>

      {/* Error state */}
      {status === 'error' && error && (
        <div className="flex items-start gap-3 card p-4 border-red-500/30 bg-red-500/5 mb-6">
          <AlertCircle size={16} className="text-red-400 flex-shrink-0 mt-0.5" />
          <div>
            <p className="text-sm font-medium text-red-400">Failed to load profile</p>
            <p className="text-xs text-gray-400 mt-1">{error}</p>
            <button
              onClick={() => ingest(inputHandle)}
              className="text-xs text-brand-400 hover:text-brand-300 mt-2 transition-colors"
            >
              Try again
            </button>
          </div>
        </div>
      )}

      {/* Loading skeleton */}
      {status === 'loading' && <ProfileLoadingSkeleton />}

      {/* Profile dashboard */}
      {status === 'success' && profile && (
        <div className="space-y-6">
          {/* Profile card */}
          <CFProfileCard
            profile={profile}
            onRefresh={handleRefresh}
          />

          {/* Stat strip */}
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
            {[
              {
                label: 'Avg Solved Rating',
                value: profile.avg_solved_rating ?? '—',
                icon: TrendingUp,
                color: 'text-brand-400',
              },
              {
                label: 'Total Submissions',
                value: profile.total_submissions.toLocaleString(),
                icon: Activity,
                color: 'text-emerald-400',
              },
              {
                label: 'Accepted',
                value: profile.accepted_count.toLocaleString(),
                icon: BarChart3,
                color: 'text-blue-400',
              },
              {
                label: 'Top Tag',
                value: profile.most_solved_tags[0]?.tag ?? '—',
                icon: Tag,
                color: 'text-amber-400',
              },
            ].map(({ label, value, icon: Icon, color }) => (
              <div key={label} className="card p-4">
                <div className="flex items-center gap-2 mb-1">
                  <Icon size={13} className={color} />
                  <p className="text-xs text-gray-500">{label}</p>
                </div>
                <p className="text-lg font-bold text-white capitalize">{value}</p>
              </div>
            ))}
          </div>

          {/* Rating chart */}
          <div className="card p-5">
            <div className="flex items-center gap-2 mb-4">
              <TrendingUp size={15} className="text-brand-400" />
              <h3 className="text-sm font-semibold text-white">Rating History</h3>
              <span className="text-xs text-gray-500 ml-auto">
                {profile.contests_participated} contests
              </span>
            </div>
            <RatingChart data={profile.rating_trend} height={260} />
          </div>

          {/* Tag analysis */}
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            {/* Most solved */}
            <div className="card p-5">
              <div className="flex items-center gap-2 mb-4">
                <Tag size={15} className="text-brand-400" />
                <h3 className="text-sm font-semibold text-white">Most Solved Topics</h3>
              </div>
              <TopicSolvedChart data={profile.most_solved_tags} height={240} />
            </div>

            {/* Weakness / strength */}
            <div className="card p-5">
              <div className="flex items-center gap-2 mb-4">
                <BarChart3 size={15} className="text-brand-400" />
                <h3 className="text-sm font-semibold text-white">Weakness Analysis</h3>
              </div>
              <WeaknessStrengthPanel
                weakest={profile.weakest_tags}
                strongest={profile.strongest_tags}
              />
            </div>
          </div>

          {/* Difficulty distribution */}
          <div className="card p-5">
            <div className="flex items-center justify-between mb-4">
              <div className="flex items-center gap-2">
                <BarChart3 size={15} className="text-brand-400" />
                <h3 className="text-sm font-semibold text-white">Difficulty Distribution</h3>
              </div>
              {profile.avg_solved_rating && (
                <span className="text-xs text-gray-500">
                  Avg difficulty: <span className="text-gray-300 font-medium">{profile.avg_solved_rating}</span>
                </span>
              )}
            </div>
            <DifficultyChart data={profile.difficulty_distribution} height={200} />
          </div>

          {/* Activity heatmap */}
          <div className="card p-5">
            <div className="flex items-center gap-2 mb-4">
              <Activity size={15} className="text-brand-400" />
              <h3 className="text-sm font-semibold text-white">Submission Activity</h3>
            </div>
            <ActivityHeatmap data={profile.activity_heatmap} />
          </div>

          {/* Language distribution */}
          {Object.keys(profile.language_distribution).length > 0 && (
            <div className="card p-5">
              <h3 className="text-sm font-semibold text-white mb-4">Language Usage</h3>
              <div className="flex flex-wrap gap-2">
                {Object.entries(profile.language_distribution).map(([lang, count]) => (
                  <div key={lang} className="flex items-center gap-2 px-3 py-1.5 rounded-lg bg-[#16161d] border border-[#2a2a3a]">
                    <span className="text-xs text-gray-300">{lang}</span>
                    <span className="text-xs text-gray-500">{count}</span>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  )
}
