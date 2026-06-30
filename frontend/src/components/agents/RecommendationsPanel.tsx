import { useEffect, useState } from 'react'
import { ListChecks, Target, Goal } from 'lucide-react'
import { memoryApi, type Recommendation } from '@/utils/api'

interface Props {
  handle: string
  priorityTopics: string[]
  dailyGoals?: Record<string, unknown> | null
  className?: string
}

export default function RecommendationsPanel({ handle, priorityTopics, dailyGoals, className }: Props) {
  const [recommendations, setRecommendations] = useState<Recommendation[]>([])

  useEffect(() => {
    if (!handle) return
    memoryApi
      .getRecommendations(handle, 'pending')
      .then((res) => setRecommendations(res.data))
      .catch(() => setRecommendations([]))
  }, [handle])

  return (
    <div className={className}>
      <div className="card p-5">
        <h2 className="text-sm font-semibold text-white mb-4 flex items-center gap-2">
          <ListChecks size={15} className="text-brand-400" /> Learning Recommendations
        </h2>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mb-4">
          <div>
            <p className="text-xs font-semibold uppercase tracking-wide text-gray-500 mb-2 flex items-center gap-1">
              <Target size={11} /> Current Priorities
            </p>
            {priorityTopics.length === 0 ? (
              <p className="text-sm text-gray-500">No priorities set yet - run the Analyzer Agent first.</p>
            ) : (
              <div className="flex flex-wrap gap-2">
                {priorityTopics.map((t) => (
                  <span key={t} className="text-xs px-2 py-1 rounded-full bg-brand-600/20 text-brand-300">{t}</span>
                ))}
              </div>
            )}
          </div>

          <div>
            <p className="text-xs font-semibold uppercase tracking-wide text-gray-500 mb-2 flex items-center gap-1">
              <Goal size={11} /> Practice Goals
            </p>
            {dailyGoals ? (
              <ul className="text-sm text-gray-300 space-y-1">
                <li>{String(dailyGoals.practice_days_per_week ?? '-')} practice sessions / week</li>
                <li>{String(dailyGoals.target_problems_per_session ?? '-')} problems / session</li>
                <li>{String(dailyGoals.review_minutes_per_session ?? '-')} min review / session</li>
              </ul>
            ) : (
              <p className="text-sm text-gray-500">Generate a study plan to see practice goals.</p>
            )}
          </div>
        </div>

        <p className="text-xs font-semibold uppercase tracking-wide text-gray-500 mb-2">Stored Recommendations</p>
        {recommendations.length === 0 ? (
          <p className="text-sm text-gray-500">No pending recommendations yet for this handle.</p>
        ) : (
          <ul className="divide-y divide-[#2a2a3a]">
            {recommendations.map((r) => (
              <li key={r.id} className="py-2 flex items-center justify-between text-sm">
                <span className="text-gray-300">{r.reason ?? r.rec_type}</span>
                <span className="text-xs text-gray-600">{r.source ?? 'unknown source'}</span>
              </li>
            ))}
          </ul>
        )}
      </div>
    </div>
  )
}
