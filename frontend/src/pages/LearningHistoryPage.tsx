import { useEffect, useState } from 'react'
import { History, MessageSquare, Award, Clock } from 'lucide-react'
import { useActiveHandle } from '@/hooks/useActiveHandle'
import { memoryApi, type StudySession, type ChatSessionSummary, type LearningMilestone } from '@/utils/api'
import HandleGate from '@/components/memory/HandleGate'
import { ChartSkeleton } from '@/components/ui/Skeleton'

export default function LearningHistoryPage() {
  const { handle, setHandle } = useActiveHandle()
  const [studySessions, setStudySessions] = useState<StudySession[]>([])
  const [chatSessions, setChatSessions] = useState<ChatSessionSummary[]>([])
  const [milestones, setMilestones] = useState<LearningMilestone[]>([])
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    if (!handle) return
    setLoading(true)
    setError(null)
    Promise.all([
      memoryApi.getStudySessions(handle),
      memoryApi.getChatSessions(handle),
      memoryApi.getMilestones(handle),
    ])
      .then(([s, c, m]) => {
        setStudySessions(s.data)
        setChatSessions(c.data)
        setMilestones(m.data)
      })
      .catch((err) => setError(err?.message ?? 'Failed to load history'))
      .finally(() => setLoading(false))
  }, [handle])

  return (
    <div className="p-6 max-w-5xl mx-auto">
      <div className="mb-6">
        <div className="flex items-center gap-3 mb-2">
          <div className="w-9 h-9 rounded-xl bg-brand-600 flex items-center justify-center">
            <History size={18} className="text-white" />
          </div>
          <h1 className="text-xl font-bold text-white">Learning & Session History</h1>
        </div>
        <p className="text-sm text-gray-400">A persistent record of study sessions, chat sessions, and milestones.</p>
      </div>

      <HandleGate initial={handle} onSubmit={setHandle} />

      {!handle && <div className="card p-8 text-center text-sm text-gray-500">Enter a handle to view its history.</div>}
      {handle && loading && <ChartSkeleton height={200} />}
      {handle && !loading && error && <div className="card p-6 text-sm text-red-300 border-red-700/40">{error}</div>}

      {handle && !loading && !error && (
        <div className="space-y-6">
          <Section icon={Clock} title="Study Sessions">
            {studySessions.length === 0 ? (
              <Empty />
            ) : (
              <ul className="divide-y divide-[#2a2a3a]">
                {studySessions.map((s) => (
                  <li key={s.id} className="py-3 flex items-center justify-between text-sm">
                    <div>
                      <p className="text-gray-200">{s.topic ?? 'General practice'}</p>
                      <p className="text-xs text-gray-500">{new Date(s.started_at).toLocaleString()}</p>
                    </div>
                    <span className="text-xs text-gray-400">
                      {s.problems_solved}/{s.problems_attempted} solved
                    </span>
                  </li>
                ))}
              </ul>
            )}
          </Section>

          <Section icon={MessageSquare} title="Chat Sessions">
            {chatSessions.length === 0 ? (
              <Empty />
            ) : (
              <ul className="divide-y divide-[#2a2a3a]">
                {chatSessions.map((c) => (
                  <li key={c.session_id} className="py-3 text-sm">
                    <p className="text-gray-200 truncate">{c.summary ?? 'No summary yet'}</p>
                    <p className="text-xs text-gray-500">{new Date(c.updated_at).toLocaleString()}</p>
                  </li>
                ))}
              </ul>
            )}
          </Section>

          <Section icon={Award} title="Milestones">
            {milestones.length === 0 ? (
              <Empty />
            ) : (
              <ul className="divide-y divide-[#2a2a3a]">
                {milestones.map((m) => (
                  <li key={m.id} className="py-3 text-sm">
                    <p className="text-gray-200">{m.title}</p>
                    <p className="text-xs text-gray-500">{new Date(m.achieved_at).toLocaleString()}</p>
                  </li>
                ))}
              </ul>
            )}
          </Section>
        </div>
      )}
    </div>
  )
}

function Section({ icon: Icon, title, children }: { icon: React.ElementType; title: string; children: React.ReactNode }) {
  return (
    <div className="card p-5">
      <h2 className="text-sm font-semibold text-white mb-2 flex items-center gap-2">
        <Icon size={15} className="text-brand-400" /> {title}
      </h2>
      {children}
    </div>
  )
}

function Empty() {
  return <p className="text-sm text-gray-500">Nothing recorded yet.</p>
}
