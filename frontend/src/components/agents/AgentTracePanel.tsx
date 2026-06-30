import { useState } from 'react'
import { ChevronDown, ChevronRight, Workflow, Clock, CheckCircle2, XCircle } from 'lucide-react'
import { cn } from '@/utils/cn'
import type { AgentRun, AgentTrace } from '@/utils/api'

interface Props {
  run: AgentRun
  traces: AgentTrace[]
  className?: string
}

const NODE_LABELS: Record<string, string> = {
  RetrieveMemory: 'Retrieve Memory',
  AnalyzerAgent: 'Analyzer Agent',
  PlannerAgent: 'Planner Agent',
  RecommenderAgent: 'Recommender Agent',
  PersistMemory: 'Persist Memory',
}

export default function AgentTracePanel({ run, traces, className }: Props) {
  const [expanded, setExpanded] = useState<number | null>(traces.length ? traces[0].id : null)

  const totalMs = traces.reduce((sum, t) => sum + (t.duration_ms ?? 0), 0)

  return (
    <div className={cn('card p-5', className)}>
      <div className="flex items-center justify-between mb-4">
        <h2 className="text-sm font-semibold text-white flex items-center gap-2">
          <Workflow size={15} className="text-brand-400" /> Agent Trace
        </h2>
        <div className="flex items-center gap-3 text-xs text-gray-500">
          <span
            className={cn(
              'px-2 py-0.5 rounded-full font-medium',
              run.status === 'completed' && 'bg-emerald-500/15 text-emerald-400',
              run.status === 'failed' && 'bg-red-500/15 text-red-400',
              run.status === 'running' && 'bg-amber-500/15 text-amber-400'
            )}
          >
            {run.status}
          </span>
          <span className="flex items-center gap-1">
            <Clock size={11} /> {totalMs}ms total
          </span>
        </div>
      </div>

      <p className="text-xs text-gray-500 mb-3">
        thread_id <code className="text-gray-400">{run.thread_id}</code> · LangGraph workflow: START → RetrieveMemory → AnalyzerAgent → PlannerAgent → RecommenderAgent → PersistMemory → END
      </p>

      <ol className="space-y-2">
        {traces.map((t, i) => {
          const isOpen = expanded === t.id
          return (
            <li key={t.id} className="border border-[#2a2a3a] rounded-lg overflow-hidden">
              <button
                onClick={() => setExpanded(isOpen ? null : t.id)}
                className="w-full flex items-center justify-between px-3 py-2 text-left hover:bg-white/5 transition-colors"
              >
                <div className="flex items-center gap-2">
                  {isOpen ? <ChevronDown size={14} className="text-gray-500" /> : <ChevronRight size={14} className="text-gray-500" />}
                  <span className="text-xs text-gray-600 w-5">{i + 1}</span>
                  {t.status === 'completed' ? (
                    <CheckCircle2 size={13} className="text-emerald-400" />
                  ) : (
                    <XCircle size={13} className="text-red-400" />
                  )}
                  <span className="text-sm text-gray-200 font-medium">{NODE_LABELS[t.node_name] ?? t.node_name}</span>
                </div>
                <span className="text-xs text-gray-500">{t.duration_ms ?? 0}ms</span>
              </button>

              {isOpen && (
                <div className="px-3 pb-3 pt-1 border-t border-[#2a2a3a] bg-black/20">
                  <p className="text-[10px] uppercase tracking-wide text-gray-600 mb-1 mt-2">Output</p>
                  <pre className="text-xs text-gray-300 whitespace-pre-wrap break-words bg-[#0f0f13] rounded p-2 max-h-48 overflow-auto">
                    {JSON.stringify(t.output_summary ?? {}, null, 2)}
                  </pre>
                  {t.error && <p className="text-xs text-red-400 mt-2">{t.error}</p>}
                </div>
              )}
            </li>
          )
        })}
      </ol>
    </div>
  )
}
