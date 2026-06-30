import { useEffect, useState } from 'react'
import { Code2, Cpu, Database, Layers, Zap, ArrowRight } from 'lucide-react'
import { useNavigate } from 'react-router-dom'
import HealthBadge from '@/components/ui/HealthBadge'
import { healthApi, type HealthResponse } from '@/utils/api'

const FEATURES = [
  { icon: Cpu,      label: 'Multi-Agent Architecture', desc: 'Analyzer, Planner, and Problem Recommender agents orchestrated end-to-end' },
  { icon: Layers,   label: 'LangGraph Workflow',        desc: 'Stateful graph: RetrieveMemory → Analyzer → Planner → Recommender → Persist' },
  { icon: Database, label: 'Codeforces Analytics',      desc: 'Rating trend, tag accuracy, difficulty spread, and submission heatmaps'      },
  { icon: Zap,      label: 'Persistent Memory',         desc: 'Long-term user profile + session context across interactions'              },
]

export default function DashboardPage() {
  const navigate = useNavigate()
  const [health, setHealth] = useState<HealthResponse | null>(null)

  useEffect(() => {
    healthApi.status().then((r) => setHealth(r.data)).catch(() => null)
  }, [])

  return (
    <div className="p-8 max-w-5xl mx-auto">
      {/* Header */}
      <div className="mb-8">
        <div className="flex items-center gap-3 mb-2">
          <div className="w-10 h-10 rounded-xl bg-brand-600 flex items-center justify-center">
            <Code2 size={20} className="text-white" />
          </div>
          <h1 className="text-2xl font-bold text-white">CodeMentor AI</h1>
        </div>
        <p className="text-gray-400 text-sm mb-3">
          Autonomous AI mentor for competitive programming, DSA, and interview prep.
        </p>
        <HealthBadge />
      </div>

      {/* System overview banner */}
      <div className="card p-5 mb-8 border-brand-600/30 bg-brand-600/5">
        <div className="flex items-center justify-between">
          <div>
            <p className="text-xs text-brand-400 font-medium uppercase tracking-widest mb-1">System Overview</p>
            <h2 className="text-lg font-semibold text-white">Codeforces Analytics &amp; AI Mentoring</h2>
            <p className="text-sm text-gray-400 mt-1">
              Full CF profile ingestion, analytics engine, multi-agent mentoring, and persistent memory are all live.
            </p>
          </div>
          <button
            onClick={() => navigate('/profile')}
            className="btn-primary flex items-center gap-2 text-sm"
          >
            Analyse Profile <ArrowRight size={14} />
          </button>
        </div>
      </div>

      {/* System status */}
      {health && (
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-4 mb-8">
          {[
            { label: 'API Status',    value: health.status,       ok: health.status === 'ok'         },
            { label: 'Database',      value: health.database,     ok: health.database === 'connected' },
            { label: 'LLM Provider',  value: health.llm_provider, ok: health.llm_provider !== 'none' },
            { label: 'Environment',   value: health.env,          ok: true                            },
          ].map(({ label, value, ok }) => (
            <div key={label} className="card p-4">
              <p className="text-xs text-gray-500 mb-1">{label}</p>
              <div className="flex items-center gap-2">
                <span className={`w-1.5 h-1.5 rounded-full ${ok ? 'bg-emerald-400' : 'bg-red-400'}`} />
                <span className="text-sm font-medium text-gray-200 capitalize">{value}</span>
              </div>
            </div>
          ))}
        </div>
      )}

      {/* Feature grid */}
      <h3 className="text-sm font-medium text-gray-500 uppercase tracking-widest mb-4">System Architecture</h3>
      <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
        {FEATURES.map(({ icon: Icon, label, desc }) => (
          <div key={label} className="card p-5 hover:border-brand-600/40 transition-colors">
            <div className="flex items-start gap-3">
              <div className="w-8 h-8 rounded-lg bg-brand-600/15 flex items-center justify-center flex-shrink-0">
                <Icon size={15} className="text-brand-400" />
              </div>
              <div>
                <p className="text-sm font-medium text-white mb-1">{label}</p>
                <p className="text-xs text-gray-500 leading-relaxed">{desc}</p>
              </div>
            </div>
          </div>
        ))}
      </div>
    </div>
  )
}