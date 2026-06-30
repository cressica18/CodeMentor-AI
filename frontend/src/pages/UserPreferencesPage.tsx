import { useEffect, useState } from 'react'
import { Settings, Save } from 'lucide-react'
import { useActiveHandle } from '@/hooks/useActiveHandle'
import { memoryApi, type UserPreferences } from '@/utils/api'
import HandleGate from '@/components/memory/HandleGate'
import { ChartSkeleton } from '@/components/ui/Skeleton'

const DIFFICULTIES = ['easy', 'medium', 'hard', 'adaptive']
const THEMES = ['dark', 'light']

export default function UserPreferencesPage() {
  const { handle, setHandle } = useActiveHandle()
  const [prefs, setPrefs] = useState<UserPreferences | null>(null)
  const [loading, setLoading] = useState(false)
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const [difficulty, setDifficulty] = useState('adaptive')
  const [dailyGoal, setDailyGoal] = useState('30')
  const [theme, setTheme] = useState('dark')
  const [topicsInput, setTopicsInput] = useState('')

  const load = async (h: string) => {
    setLoading(true)
    setError(null)
    try {
      const res = await memoryApi.getPreferences(h)
      setPrefs(res.data)
      setDifficulty(res.data.preferred_difficulty ?? 'adaptive')
      setDailyGoal(String(res.data.daily_goal_minutes ?? 30))
      setTheme(res.data.theme ?? 'dark')
      setTopicsInput((res.data.preferred_topics ?? []).join(', '))
    } catch (err: any) {
      setError(err?.message ?? 'Failed to load preferences')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    if (handle) load(handle)
  }, [handle])

  const handleSave = async () => {
    if (!handle) return
    setSaving(true)
    try {
      const res = await memoryApi.updatePreferences(handle, {
        preferred_difficulty: difficulty,
        daily_goal_minutes: Number(dailyGoal) || 0,
        theme,
        preferred_topics: topicsInput
          .split(',')
          .map((t) => t.trim())
          .filter(Boolean),
      })
      setPrefs(res.data)
    } finally {
      setSaving(false)
    }
  }

  return (
    <div className="p-6 max-w-2xl mx-auto">
      <div className="mb-6">
        <div className="flex items-center gap-3 mb-2">
          <div className="w-9 h-9 rounded-xl bg-brand-600 flex items-center justify-center">
            <Settings size={18} className="text-white" />
          </div>
          <h1 className="text-xl font-bold text-white">Preferences</h1>
        </div>
        <p className="text-sm text-gray-400">Settings future agents (Recommender, Planner) will respect when personalizing your experience.</p>
      </div>

      <HandleGate initial={handle} onSubmit={setHandle} />

      {!handle && <div className="card p-8 text-center text-sm text-gray-500">Enter a handle to view its preferences.</div>}
      {handle && loading && <ChartSkeleton height={220} />}
      {handle && !loading && error && <div className="card p-6 text-sm text-red-300 border-red-700/40">{error}</div>}

      {handle && !loading && prefs && (
        <div className="card p-5 space-y-4">
          <div>
            <label className="text-xs text-gray-400 mb-1 block">Preferred difficulty</label>
            <select value={difficulty} onChange={(e) => setDifficulty(e.target.value)} className="input w-full">
              {DIFFICULTIES.map((d) => (
                <option key={d} value={d}>
                  {d}
                </option>
              ))}
            </select>
          </div>

          <div>
            <label className="text-xs text-gray-400 mb-1 block">Daily goal (minutes)</label>
            <input
              type="number"
              value={dailyGoal}
              onChange={(e) => setDailyGoal(e.target.value)}
              className="input w-40"
            />
          </div>

          <div>
            <label className="text-xs text-gray-400 mb-1 block">Preferred topics (comma separated)</label>
            <input
              value={topicsInput}
              onChange={(e) => setTopicsInput(e.target.value)}
              className="input w-full"
              placeholder="dp, graphs, number theory"
            />
          </div>

          <div>
            <label className="text-xs text-gray-400 mb-1 block">Theme</label>
            <div className="flex gap-2">
              {THEMES.map((t) => (
                <button
                  key={t}
                  onClick={() => setTheme(t)}
                  className={theme === t ? 'btn-primary text-xs' : 'btn-secondary text-xs'}
                >
                  {t}
                </button>
              ))}
            </div>
          </div>

          <button onClick={handleSave} disabled={saving} className="btn-primary flex items-center gap-2 text-sm">
            <Save size={14} /> {saving ? 'Saving…' : 'Save preferences'}
          </button>
        </div>
      )}
    </div>
  )
}
