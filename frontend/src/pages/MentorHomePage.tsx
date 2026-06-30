import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { Sparkles, Search, Loader2, CheckCircle2, Circle, AlertCircle, Zap } from 'lucide-react'
import { codeforcesApi, agentsApi, recommendationsApi } from '@/utils/api'
import { useActiveHandle } from '@/hooks/useActiveHandle'
import { cn } from '@/utils/cn'

type StepStatus = 'pending' | 'active' | 'done' | 'error'

interface Step {
  key: string
  label: string
}

const STEPS: Step[] = [
  { key: 'ingest', label: 'Fetching your Codeforces profile' },
  { key: 'memory', label: 'Updating persistent memory' },
  { key: 'agents', label: 'Running Analyzer → Planner → Recommender agents' },
  { key: 'recommendations', label: 'Matching real Codeforces problems to your gaps' },
  { key: 'done', label: 'Building your dashboard' },
]

const POPULAR_HANDLES = ['tourist', 'jiangly', 'Um_nik', 'neal']

export default function MentorHomePage() {
  const navigate = useNavigate()
  const { setHandle } = useActiveHandle()
  const [inputHandle, setInputHandle] = useState('')
  const [running, setRunning] = useState(false)
  const [stepStatus, setStepStatus] = useState<Record<string, StepStatus>>({})
  const [error, setError] = useState<string | null>(null)

  const setStep = (key: string, status: StepStatus) =>
    setStepStatus((prev) => ({ ...prev, [key]: status }))

  const runWorkflow = async (handle: string) => {
    const trimmed = handle.trim()
    if (!trimmed || running) return

    setRunning(true)
    setError(null)
    setStepStatus({})

    try {
      // 1. Fetch CF profile (Phase 2 ingestion — also upserts the User row
      //    + persistent memory the agents read from).
      setStep('ingest', 'active')
      await codeforcesApi.ingest(trimmed)
      setStep('ingest', 'done')

      setStep('memory', 'active')
      setStep('memory', 'done')

      // 2. Single call runs the full LangGraph workflow server-side:
      //    RetrieveMemory -> Analyzer -> Planner -> Recommender -> Persist.
      setStep('agents', 'active')
      await agentsApi.run(trimmed)
      setStep('agents', 'done')

      // 3. Recommendations were already generated + persisted by the
      //    Recommender node above; this just confirms they're queryable.
      setStep('recommendations', 'active')
      await recommendationsApi.list(trimmed, 'pending')
      setStep('recommendations', 'done')

      setStep('done', 'active')
      setHandle(trimmed)
      setStep('done', 'done')

      navigate('/mentor')
    } catch (err: any) {
      const failedStep = STEPS.find((s) => stepStatus[s.key] === 'active')
      if (failedStep) setStep(failedStep.key, 'error')
      setError(err?.message ?? 'Something went wrong running the mentor workflow.')
      setRunning(false)
    }
  }

  return (
    <div className="min-h-screen flex items-center justify-center p-6">
      <div className="w-full max-w-xl">
        <div className="text-center mb-8">
          <div className="w-14 h-14 rounded-2xl bg-brand-600 flex items-center justify-center mx-auto mb-4">
            <Zap size={26} className="text-white" />
          </div>
          <h1 className="text-2xl font-bold text-white mb-2">CodeMentor AI</h1>
          <p className="text-sm text-gray-400 max-w-md mx-auto">
            Your autonomous mentor for competitive programming. Enter your Codeforces handle and
            click one button — analytics, study plan, and real problem recommendations follow
            automatically.
          </p>
        </div>

        <div className="card p-6">
          <div className="flex gap-3 mb-3">
            <div className="relative flex-1">
              <Search size={16} className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-500 pointer-events-none" />
              <input
                type="text"
                value={inputHandle}
                onChange={(e) => setInputHandle(e.target.value)}
                onKeyDown={(e) => e.key === 'Enter' && runWorkflow(inputHandle)}
                placeholder="Enter Codeforces handle, e.g. tourist"
                className="input w-full pl-9 pr-4 py-3"
                disabled={running}
                autoFocus
              />
            </div>
            <button
              onClick={() => runWorkflow(inputHandle)}
              disabled={running || !inputHandle.trim()}
              className="btn-primary flex items-center gap-2 px-5 disabled:opacity-50"
            >
              {running ? <Loader2 size={16} className="animate-spin" /> : <Sparkles size={16} />}
              {running ? 'Analyzing…' : 'Analyze My Profile'}
            </button>
          </div>

          <div className="flex flex-wrap gap-2 mb-2">
            <span className="text-xs text-gray-600">Try:</span>
            {POPULAR_HANDLES.map((h) => (
              <button
                key={h}
                onClick={() => setInputHandle(h)}
                disabled={running}
                className="text-xs text-brand-400 hover:text-brand-300 disabled:opacity-50"
              >
                {h}
              </button>
            ))}
          </div>

          {(running || Object.keys(stepStatus).length > 0) && (
            <div className="mt-5 space-y-2.5 border-t border-[#2a2a3a] pt-5">
              {STEPS.map((s) => {
                const status = stepStatus[s.key] ?? 'pending'
                return (
                  <div key={s.key} className="flex items-center gap-2.5 text-sm">
                    {status === 'done' && <CheckCircle2 size={15} className="text-emerald-400 flex-shrink-0" />}
                    {status === 'active' && <Loader2 size={15} className="text-brand-400 animate-spin flex-shrink-0" />}
                    {status === 'pending' && <Circle size={15} className="text-gray-700 flex-shrink-0" />}
                    {status === 'error' && <AlertCircle size={15} className="text-red-400 flex-shrink-0" />}
                    <span
                      className={cn(
                        'transition-colors',
                        status === 'done' && 'text-gray-300',
                        status === 'active' && 'text-white font-medium',
                        status === 'pending' && 'text-gray-600',
                        status === 'error' && 'text-red-400'
                      )}
                    >
                      {s.label}
                    </span>
                  </div>
                )
              })}
            </div>
          )}

          {error && (
            <div className="mt-4 text-sm text-red-300 bg-red-500/10 border border-red-700/40 rounded-lg p-3">
              {error}
            </div>
          )}
        </div>

        <p className="text-center text-xs text-gray-600 mt-4">
          No Swagger. No manual API calls. Just your handle.
        </p>
      </div>
    </div>
  )
}
