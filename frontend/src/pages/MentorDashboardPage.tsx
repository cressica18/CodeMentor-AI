import { useEffect, useState } from 'react'
import { Sparkles, AlertTriangle, Target, Trophy, RefreshCw, Calendar, ListChecks } from 'lucide-react'
import { useActiveHandle } from '@/hooks/useActiveHandle'
import HandleGate from '@/components/memory/HandleGate'
import { ProfileLoadingSkeleton } from '@/components/ui/Skeleton'
import AgentTracePanel from '@/components/agents/AgentTracePanel'
import LearningRoadmap from '@/components/agents/LearningRoadmap'
import ProblemCard from '@/components/recommendations/ProblemCard'
import {
  agentsApi,
  codeforcesApi,
  recommendationsApi,
  type AnalysisSnapshot,
  type PlannerOutputRead,
  type RecommendedProblem,
  type AgentRun,
  type AgentTrace,
  type CFProfileResponse,
} from '@/utils/api'

export default function MentorDashboardPage() {
  const { handle, setHandle } = useActiveHandle()

  const [profile, setProfile] = useState<CFProfileResponse | null>(null)
  const [analysis, setAnalysis] = useState<AnalysisSnapshot | null>(null)
  const [plan, setPlan] = useState<PlannerOutputRead | null>(null)
  const [problems, setProblems] = useState<RecommendedProblem[]>([])
  const [latestRun, setLatestRun] = useState<AgentRun | null>(null)
  const [traces, setTraces] = useState<AgentTrace[]>([])

  const [loading, setLoading] = useState(false)
  const [rerunning, setRerunning] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [actionBusy, setActionBusy] = useState<number | null>(null)

  const loadAll = async (h: string) => {
    setLoading(true)
    setError(null)
    try {
      const [profileRes, analysisRes, planRes, problemsRes, historyRes] = await Promise.allSettled([
        codeforcesApi.getProfile(h),
        agentsApi.getLatestAnalysis(h),
        agentsApi.getLatestPlan(h),
        recommendationsApi.list(h, 'pending'),
        agentsApi.getHistory(h, 1),
      ])

      setProfile(profileRes.status === 'fulfilled' ? profileRes.value.data : null)
      setAnalysis(analysisRes.status === 'fulfilled' ? analysisRes.value.data : null)
      setPlan(planRes.status === 'fulfilled' ? planRes.value.data : null)
      setProblems(problemsRes.status === 'fulfilled' ? problemsRes.value.data : [])

      if (historyRes.status === 'fulfilled' && historyRes.value.data.length > 0) {
        const run = historyRes.value.data[0]
        setLatestRun(run)
        const traceRes = await agentsApi.getTraces(run.id)
        setTraces(traceRes.data)
      } else {
        setLatestRun(null)
        setTraces([])
      }

      if (
        profileRes.status === 'rejected' &&
        analysisRes.status === 'rejected' &&
        planRes.status === 'rejected'
      ) {
        setError(`No data yet for "${h}" — run the mentor workflow from the home page first.`)
      }
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    if (handle) loadAll(handle)
  }, [handle])

  const handleRerun = async () => {
    if (!handle) return
    setRerunning(true)
    setError(null)
    try {
      await codeforcesApi.ingest(handle, true)
      await agentsApi.run(handle)
      await loadAll(handle)
    } catch (err: any) {
      setError(err?.message ?? 'Re-running the mentor workflow failed.')
    } finally {
      setRerunning(false)
    }
  }

  const refreshProblems = async () => {
    if (!handle) return
    const res = await recommendationsApi.list(handle, 'pending')
    setProblems(res.data)
  }

  const handleSolve = async (id: number) => {
    setActionBusy(id)
    try {
      await recommendationsApi.updateStatus(id, 'solve')
      await refreshProblems()
    } finally {
      setActionBusy(null)
    }
  }

  const handleSkip = async (id: number) => {
    setActionBusy(id)
    try {
      await recommendationsApi.updateStatus(id, 'skip')
      await refreshProblems()
    } finally {
      setActionBusy(null)
    }
  }

  const handleBookmark = async (id: number, bookmarked: boolean) => {
    setActionBusy(id)
    try {
      await recommendationsApi.updateStatus(id, bookmarked ? 'bookmark' : 'unbookmark')
      await refreshProblems()
    } finally {
      setActionBusy(null)
    }
  }

  const strengths = analysis?.strengths ?? []
  const weaknesses = analysis?.weaknesses ?? []
  const priorityTopics = analysis?.priority_topics ?? plan?.priority_topics ?? []
  const milestones = plan?.milestones ?? []
  const studyPlan = (plan?.study_plan ?? {}) as Record<string, any>

  return (
    <div className="p-6 max-w-6xl mx-auto">
      <div className="mb-6 flex items-start justify-between gap-4 flex-wrap">
        <div>
          <div className="flex items-center gap-3 mb-2">
            <div className="w-9 h-9 rounded-xl bg-brand-600 flex items-center justify-center">
              <Sparkles size={18} className="text-white" />
            </div>
            <h1 className="text-xl font-bold text-white">Mentor Dashboard</h1>
          </div>
          <p className="text-sm text-gray-400">
            Your full AI mentor workflow output — analytics, study plan, recommended problems, and agent reasoning.
          </p>
        </div>
        {handle && (
          <button
            onClick={handleRerun}
            disabled={rerunning}
            className="btn-secondary flex items-center gap-2 text-xs"
          >
            <RefreshCw size={13} className={rerunning ? 'animate-spin' : ''} />
            {rerunning ? 'Re-running mentor workflow…' : 'Re-run Mentor Workflow'}
          </button>
        )}
      </div>

      <HandleGate initial={handle} onSubmit={setHandle} />

      {!handle && (
        <div className="card p-8 text-center text-sm text-gray-500">
          Enter a handle, or analyze one from the home page, to view its mentor dashboard.
        </div>
      )}

      {handle && loading && <ProfileLoadingSkeleton />}

      {handle && error && !loading && (
        <div className="card p-6 text-sm text-red-300 border-red-700/40 mb-4">{error}</div>
      )}

      {handle && !loading && !error && (
        <div className="space-y-6">
          {/* Profile summary */}
          {profile && (
            <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
              <div className="card p-4">
                <p className="text-xs text-gray-500 mb-1 flex items-center gap-1"><Trophy size={11} /> Current Rating</p>
                <p className="text-xl font-bold text-white">{profile.current_rating ?? '—'}</p>
              </div>
              <div className="card p-4">
                <p className="text-xs text-gray-500 mb-1">Max Rating</p>
                <p className="text-xl font-bold text-white">{profile.max_rating ?? '—'}</p>
              </div>
              <div className="card p-4">
                <p className="text-xs text-gray-500 mb-1">Solved</p>
                <p className="text-xl font-bold text-white">{profile.solved_count}</p>
              </div>
              <div className="card p-4">
                <p className="text-xs text-gray-500 mb-1">Rank</p>
                <p className="text-xl font-bold text-white capitalize">{profile.rank ?? '—'}</p>
              </div>
            </div>
          )}

          {/* Strengths / weaknesses / priorities */}
          {(strengths.length > 0 || weaknesses.length > 0) && (
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
              <div className="card p-5">
                <h3 className="text-xs font-semibold uppercase tracking-wide text-emerald-400 mb-3 flex items-center gap-2">
                  <Sparkles size={13} /> Strengths
                </h3>
                <ul className="space-y-2">
                  {strengths.map((s) => (
                    <li key={s} className="text-sm text-gray-200 px-2 py-1 rounded bg-emerald-500/10">{s}</li>
                  ))}
                </ul>
              </div>
              <div className="card p-5">
                <h3 className="text-xs font-semibold uppercase tracking-wide text-red-400 mb-3 flex items-center gap-2">
                  <AlertTriangle size={13} /> Weaknesses
                </h3>
                <ul className="space-y-2">
                  {weaknesses.map((w) => (
                    <li key={w} className="text-sm text-gray-200 px-2 py-1 rounded bg-red-500/10">{w}</li>
                  ))}
                </ul>
              </div>
              <div className="card p-5">
                <h3 className="text-xs font-semibold uppercase tracking-wide text-brand-400 mb-3 flex items-center gap-2">
                  <Target size={13} /> Priority Topics
                </h3>
                <ol className="space-y-2 list-decimal list-inside">
                  {priorityTopics.map((t) => (
                    <li key={t} className="text-sm text-gray-200">{t}</li>
                  ))}
                </ol>
              </div>
            </div>
          )}

          {/* Study plan */}
          {plan && (
            <div className="card p-5">
              <h2 className="text-sm font-semibold text-white mb-3 flex items-center gap-2">
                <Calendar size={14} className="text-brand-400" /> Study Plan
              </h2>
              <div className="grid grid-cols-1 sm:grid-cols-3 gap-4 mb-4">
                <div>
                  <p className="text-xs text-gray-500">Estimated Duration</p>
                  <p className="text-sm text-gray-200 font-medium">{plan.estimated_duration ?? '—'}</p>
                </div>
                <div>
                  <p className="text-xs text-gray-500">Current Stage</p>
                  <p className="text-sm text-gray-200 font-medium">{studyPlan.current_stage ?? '—'}</p>
                </div>
                <div>
                  <p className="text-xs text-gray-500">Goal</p>
                  <p className="text-sm text-gray-200 font-medium">{studyPlan.goal ?? '—'}</p>
                </div>
              </div>
              {milestones.length > 0 && (
                <LearningRoadmap milestones={milestones} completedCount={0} />
              )}
            </div>
          )}

          {/* Recommended problems */}
          <div className="card p-5">
            <h2 className="text-sm font-semibold text-white mb-1 flex items-center gap-2">
              <ListChecks size={14} className="text-brand-400" /> Recommended Problems
            </h2>
            <p className="text-xs text-gray-500 mb-4">
              Real Codeforces problems matched to your weak topics, strengths, and current rating.
            </p>
            {problems.length === 0 ? (
              <p className="text-sm text-gray-500">
                No pending recommendations — re-run the mentor workflow above to generate fresh ones.
              </p>
            ) : (
              <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
                {problems.map((p) => (
                  <ProblemCard
                    key={p.id}
                    problem={p}
                    onSolve={handleSolve}
                    onSkip={handleSkip}
                    onToggleBookmark={handleBookmark}
                    busy={actionBusy === p.id}
                  />
                ))}
              </div>
            )}
          </div>

          {/* Agent trace */}
          {latestRun && traces.length > 0 && <AgentTracePanel run={latestRun} traces={traces} />}
        </div>
      )}
    </div>
  )
}
