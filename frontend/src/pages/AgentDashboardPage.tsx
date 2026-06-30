import { useEffect, useState } from 'react'
import { Brain, Sparkles, AlertTriangle, Target, PlayCircle } from 'lucide-react'
import { useActiveHandle } from '@/hooks/useActiveHandle'
import { agentsApi, type AgentRunResult, type AnalysisSnapshot } from '@/utils/api'
import HandleGate from '@/components/memory/HandleGate'
import { StatCardSkeleton } from '@/components/ui/Skeleton'
import AgentTracePanel from '@/components/agents/AgentTracePanel'

export default function AgentDashboardPage() {
  const { handle, setHandle } = useActiveHandle()
  const [latest, setLatest] = useState<AnalysisSnapshot | null>(null)
  const [runResult, setRunResult] = useState<AgentRunResult | null>(null)
  const [loading, setLoading] = useState(false)
  const [running, setRunning] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const loadLatest = async (h: string) => {
    setLoading(true)
    setError(null)
    try {
      const res = await agentsApi.getLatestAnalysis(h)
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

  const handleAnalyze = async () => {
    if (!handle) return
    setRunning(true)
    setError(null)
    try {
      const res = await agentsApi.analyze(handle)
      setRunResult(res.data)
      await loadLatest(handle)
    } catch (err: any) {
      setError(err?.message ?? 'Analyzer run failed (ingest a CF profile for this handle first)')
    } finally {
      setRunning(false)
    }
  }

  const strengths = runResult?.analysis?.strengths ?? latest?.strengths ?? []
  const weaknesses = runResult?.analysis?.weaknesses ?? latest?.weaknesses ?? []
  const priorityTopics = runResult?.analysis?.priority_topics ?? latest?.priority_topics ?? []
  const velocity = runResult?.analysis?.improvement_velocity ?? latest?.improvement_velocity ?? null
  const summary = runResult?.analysis?.analysis_summary ?? latest?.analysis_summary ?? null

  return (
    <div className="p-6 max-w-5xl mx-auto">
      <div className="mb-6">
        <div className="flex items-center gap-3 mb-2">
          <div className="w-9 h-9 rounded-xl bg-brand-600 flex items-center justify-center">
            <Brain size={18} className="text-white" />
          </div>
          <h1 className="text-xl font-bold text-white">Agent Dashboard</h1>
        </div>
        <p className="text-sm text-gray-400">
          The Analyzer Agent's current read on this student — strengths, weaknesses, and what to prioritize next.
        </p>
      </div>

      <HandleGate initial={handle} onSubmit={setHandle} />

      {!handle && <div className="card p-8 text-center text-sm text-gray-500">Enter a handle to view its analysis.</div>}

      {handle && (
        <div className="mb-4 flex items-center justify-between">
          <p className="text-xs text-gray-500">
            {latest ? `Last analyzed ${new Date(latest.created_at).toLocaleString()}` : 'No analysis run yet for this handle.'}
          </p>
          <button onClick={handleAnalyze} disabled={running} className="btn-primary flex items-center gap-2 text-xs">
            <PlayCircle size={14} /> {running ? 'Running Analyzer Agent…' : 'Run Analyzer Agent'}
          </button>
        </div>
      )}

      {handle && loading && (
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          <StatCardSkeleton /> <StatCardSkeleton /> <StatCardSkeleton />
        </div>
      )}

      {handle && error && <div className="card p-6 text-sm text-red-300 border-red-700/40 mb-4">{error}</div>}

      {handle && !loading && (strengths.length > 0 || weaknesses.length > 0 || summary) && (
        <div className="space-y-6">
          {summary && (
            <div className="card p-5">
              <h2 className="text-sm font-semibold text-white mb-2 flex items-center gap-2">
                <Sparkles size={14} className="text-brand-400" /> Analysis Summary
              </h2>
              <p className="text-sm text-gray-300 leading-relaxed">{summary}</p>
              {velocity !== null && (
                <p className="text-xs text-gray-500 mt-3">
                  Improvement velocity: <span className={velocity >= 0 ? 'text-emerald-400' : 'text-red-400'}>{velocity.toFixed(2)}</span> rating/day
                </p>
              )}
            </div>
          )}

          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            <div className="card p-5">
              <h3 className="text-xs font-semibold uppercase tracking-wide text-emerald-400 mb-3 flex items-center gap-2">
                <Sparkles size={13} /> Strengths
              </h3>
              {strengths.length === 0 ? (
                <p className="text-sm text-gray-500">None identified yet.</p>
              ) : (
                <ul className="space-y-2">
                  {strengths.map((s) => (
                    <li key={s} className="text-sm text-gray-200 px-2 py-1 rounded bg-emerald-500/10">{s}</li>
                  ))}
                </ul>
              )}
            </div>

            <div className="card p-5">
              <h3 className="text-xs font-semibold uppercase tracking-wide text-red-400 mb-3 flex items-center gap-2">
                <AlertTriangle size={13} /> Weaknesses
              </h3>
              {weaknesses.length === 0 ? (
                <p className="text-sm text-gray-500">None identified yet.</p>
              ) : (
                <ul className="space-y-2">
                  {weaknesses.map((w) => (
                    <li key={w} className="text-sm text-gray-200 px-2 py-1 rounded bg-red-500/10">{w}</li>
                  ))}
                </ul>
              )}
            </div>

            <div className="card p-5">
              <h3 className="text-xs font-semibold uppercase tracking-wide text-brand-400 mb-3 flex items-center gap-2">
                <Target size={13} /> Priority Topics
              </h3>
              {priorityTopics.length === 0 ? (
                <p className="text-sm text-gray-500">None identified yet.</p>
              ) : (
                <ol className="space-y-2 list-decimal list-inside">
                  {priorityTopics.map((t) => (
                    <li key={t} className="text-sm text-gray-200">{t}</li>
                  ))}
                </ol>
              )}
            </div>
          </div>
        </div>
      )}

      {handle && !loading && strengths.length === 0 && weaknesses.length === 0 && !summary && (
        <div className="card p-8 text-center text-sm text-gray-500">
          No analysis yet for this handle. Run the Analyzer Agent above (requires a Codeforces profile already ingested for this handle).
        </div>
      )}

      {runResult && <AgentTracePanel traces={runResult.traces} run={runResult.run} className="mt-6" />}
    </div>
  )
}
