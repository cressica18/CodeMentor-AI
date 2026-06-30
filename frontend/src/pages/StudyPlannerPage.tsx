import { useEffect, useState } from 'react'
import { Calendar, Flag, Clock3, PlayCircle, RotateCw } from 'lucide-react'
import { useActiveHandle } from '@/hooks/useActiveHandle'
import { agentsApi, type AgentRunResult, type PlannerOutputRead } from '@/utils/api'
import HandleGate from '@/components/memory/HandleGate'
import { StatCardSkeleton } from '@/components/ui/Skeleton'
import AgentTracePanel from '@/components/agents/AgentTracePanel'
import RecommendationsPanel from '@/components/agents/RecommendationsPanel'

export default function StudyPlannerPage() {
  const { handle, setHandle } = useActiveHandle()
  const [latest, setLatest] = useState<PlannerOutputRead | null>(null)
  const [runResult, setRunResult] = useState<AgentRunResult | null>(null)
  const [loading, setLoading] = useState(false)
  const [running, setRunning] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const loadLatest = async (h: string) => {
    setLoading(true)
    setError(null)
    try {
      const res = await agentsApi.getLatestPlan(h)
      setLatest(res.data)
    } catch {
      setLatest(null)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    if (handle) loadLatest(handle)
  }, [handle])

  const handleGenerate = async () => {
    if (!handle) return
    setRunning(true)
    setError(null)
    try {
      const res = await agentsApi.plan(handle)
      setRunResult(res.data)
      await loadLatest(handle)
    } catch (err: any) {
      setError(err?.message ?? 'Planner run failed (ingest a CF profile for this handle first)')
    } finally {
      setRunning(false)
    }
  }

  const milestones = runResult?.plan?.milestones ?? latest?.milestones ?? []
  const weeklySchedule = runResult?.plan?.weekly_schedule ?? latest?.weekly_schedule ?? []
  const estimatedDuration = runResult?.plan?.estimated_duration ?? latest?.estimated_duration ?? null
  const priorityTopics = runResult?.plan?.priority_topics ?? latest?.priority_topics ?? []
  const studyPlan = (runResult?.plan?.study_plan ?? latest?.study_plan ?? {}) as Record<string, any>

  return (
    <div className="p-6 max-w-5xl mx-auto">
      <div className="mb-6">
        <div className="flex items-center gap-3 mb-2">
          <div className="w-9 h-9 rounded-xl bg-brand-600 flex items-center justify-center">
            <Calendar size={18} className="text-white" />
          </div>
          <h1 className="text-xl font-bold text-white">Study Planner</h1>
        </div>
        <p className="text-sm text-gray-400">
          The Planner Agent's generated roadmap: milestones, weekly schedule, and estimated completion time.
        </p>
      </div>

      <HandleGate initial={handle} onSubmit={setHandle} />

      {!handle && <div className="card p-8 text-center text-sm text-gray-500">Enter a handle to view its study plan.</div>}

      {handle && (
        <div className="mb-4 flex items-center justify-between">
          <p className="text-xs text-gray-500">
            {latest ? `Last planned ${new Date(latest.created_at).toLocaleString()}` : 'No study plan generated yet for this handle.'}
          </p>
          <button onClick={handleGenerate} disabled={running} className="btn-primary flex items-center gap-2 text-xs">
            {running ? <RotateCw size={14} className="animate-spin" /> : <PlayCircle size={14} />}
            {running ? 'Running Planner Agent...' : 'Generate Study Plan'}
          </button>
        </div>
      )}

      {handle && loading && (
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          <StatCardSkeleton /> <StatCardSkeleton /> <StatCardSkeleton />
        </div>
      )}

      {handle && error && <div className="card p-6 text-sm text-red-300 border-red-700/40 mb-4">{error}</div>}

      {handle && !loading && (milestones.length > 0 || weeklySchedule.length > 0) && (
        <div className="space-y-6">
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            <div className="card p-4">
              <p className="text-xs text-gray-500 mb-1 flex items-center gap-1"><Clock3 size={12} /> Estimated Duration</p>
              <p className="text-xl font-bold text-white">{estimatedDuration ?? '-'}</p>
            </div>
            <div className="card p-4">
              <p className="text-xs text-gray-500 mb-1">Current Stage</p>
              <p className="text-xl font-bold text-white">{studyPlan.current_stage ?? '-'}</p>
            </div>
            <div className="card p-4">
              <p className="text-xs text-gray-500 mb-1">Priority Topics</p>
              <p className="text-sm text-gray-300">{priorityTopics.length ? priorityTopics.join(', ') : '-'}</p>
            </div>
          </div>

          {studyPlan.goal && (
            <div className="card p-5">
              <h2 className="text-sm font-semibold text-white mb-1">Goal</h2>
              <p className="text-sm text-gray-300">{studyPlan.goal}</p>
            </div>
          )}

          <div className="card p-5">
            <h2 className="text-sm font-semibold text-white mb-3 flex items-center gap-2">
              <Flag size={14} className="text-brand-400" /> Milestones
            </h2>
            {milestones.length === 0 ? (
              <p className="text-sm text-gray-500">No milestones yet.</p>
            ) : (
              <ol className="space-y-2">
                {milestones.map((m) => (
                  <li key={m.order} className="flex items-center justify-between px-3 py-2 rounded-lg bg-white/5">
                    <div>
                      <p className="text-sm text-gray-200 font-medium">{m.title}</p>
                      <p className="text-xs text-gray-500">{m.type.replace(/_/g, ' ')} - target {m.target_problems_solved} problems</p>
                    </div>
                    <span className="text-xs text-gray-600">#{m.order}</span>
                  </li>
                ))}
              </ol>
            )}
          </div>

          <div className="card p-5">
            <h2 className="text-sm font-semibold text-white mb-3">Weekly Schedule</h2>
            {weeklySchedule.length === 0 ? (
              <p className="text-sm text-gray-500">No schedule yet.</p>
            ) : (
              <div className="overflow-x-auto">
                <table className="w-full text-sm">
                  <thead>
                    <tr className="text-left text-xs text-gray-500 border-b border-[#2a2a3a]">
                      <th className="py-2 pr-4">Week</th>
                      <th className="py-2 pr-4">Focus Topic</th>
                      <th className="py-2 pr-4">Sessions</th>
                      <th className="py-2 pr-4">Goal</th>
                      <th className="py-2">Revision Week</th>
                    </tr>
                  </thead>
                  <tbody>
                    {weeklySchedule.map((w) => (
                      <tr key={w.week} className="border-b border-[#2a2a3a]/60">
                        <td className="py-2 pr-4 text-gray-400">{w.week}</td>
                        <td className="py-2 pr-4 text-gray-200">{w.focus_topic}</td>
                        <td className="py-2 pr-4 text-gray-400">{w.sessions_planned}</td>
                        <td className="py-2 pr-4 text-gray-400">{w.goal}</td>
                        <td className="py-2">{w.revision ? <span className="text-amber-400 text-xs">Yes</span> : <span className="text-gray-600 text-xs">-</span>}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </div>
        </div>
      )}

      {handle && !loading && milestones.length === 0 && weeklySchedule.length === 0 && (
        <div className="card p-8 text-center text-sm text-gray-500">
          No study plan yet for this handle. Generate one above (requires a Codeforces profile already ingested for this handle).
        </div>
      )}

      {handle && !loading && (milestones.length > 0 || weeklySchedule.length > 0) && (
        <RecommendationsPanel
          handle={handle}
          priorityTopics={priorityTopics}
          dailyGoals={(studyPlan.daily_goals as Record<string, unknown>) ?? null}
          className="mt-6"
        />
      )}

      {runResult && <AgentTracePanel traces={runResult.traces} run={runResult.run} className="mt-6" />}
    </div>
  )
}
