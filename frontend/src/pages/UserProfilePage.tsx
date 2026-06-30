import { useEffect, useState } from 'react'
import { UserCircle, Save, Flame } from 'lucide-react'
import { useActiveHandle } from '@/hooks/useActiveHandle'
import { memoryApi, type UserProfile } from '@/utils/api'
import HandleGate from '@/components/memory/HandleGate'
import { ProfileCardSkeleton } from '@/components/ui/Skeleton'

export default function UserProfilePage() {
  const { handle, setHandle } = useActiveHandle()
  const [profile, setProfile] = useState<UserProfile | null>(null)
  const [loading, setLoading] = useState(false)
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const [bio, setBio] = useState('')
  const [targetRating, setTargetRating] = useState('')

  const load = async (h: string) => {
    if (!h) return
    setLoading(true)
    setError(null)
    try {
      const res = await memoryApi.getProfile(h)
      setProfile(res.data)
      setBio(res.data.bio ?? '')
      setTargetRating(((res.data.goals as any)?.target_rating ?? '').toString())
    } catch (err: any) {
      setError(err?.message ?? 'Could not load profile (has this handle been registered yet?)')
      setProfile(null)
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
      const res = await memoryApi.updateProfile(handle, {
        bio,
        goals: targetRating ? { target_rating: Number(targetRating) } : {},
      })
      setProfile(res.data)
    } finally {
      setSaving(false)
    }
  }

  const handleTouchStreak = async () => {
    if (!handle) return
    const res = await memoryApi.touchStreak(handle)
    setProfile(res.data)
  }

  return (
    <div className="p-6 max-w-3xl mx-auto">
      <div className="mb-6">
        <div className="flex items-center gap-3 mb-2">
          <div className="w-9 h-9 rounded-xl bg-brand-600 flex items-center justify-center">
            <UserCircle size={18} className="text-white" />
          </div>
          <h1 className="text-xl font-bold text-white">User Profile</h1>
        </div>
        <p className="text-sm text-gray-400">The mentor's persistent model of who you are and what you're working toward.</p>
      </div>

      <HandleGate initial={handle} onSubmit={setHandle} />

      {!handle && <div className="card p-8 text-center text-sm text-gray-500">Enter a handle to view its profile.</div>}

      {handle && loading && <ProfileCardSkeleton />}

      {handle && !loading && error && (
        <div className="card p-6 text-sm text-red-300 border-red-700/40">{error}</div>
      )}

      {handle && !loading && profile && (
        <div className="space-y-6">
          <div className="card p-5 flex items-center justify-between">
            <div className="flex items-center gap-3">
              <div className="w-10 h-10 rounded-full bg-amber-900/40 border border-amber-700/40 flex items-center justify-center">
                <Flame size={18} className="text-amber-400" />
              </div>
              <div>
                <p className="text-sm text-white font-medium">{profile.current_streak_days}-day streak</p>
                <p className="text-xs text-gray-500">Longest: {profile.longest_streak_days} days</p>
              </div>
            </div>
            <button onClick={handleTouchStreak} className="btn-secondary text-sm">
              Log practice today
            </button>
          </div>

          <div className="card p-5 space-y-4">
            <div>
              <label className="text-xs text-gray-400 mb-1 block">Bio</label>
              <textarea
                value={bio}
                onChange={(e) => setBio(e.target.value)}
                rows={3}
                className="input w-full resize-none"
                placeholder="A short note about your goals as a competitive programmer..."
              />
            </div>
            <div>
              <label className="text-xs text-gray-400 mb-1 block">Target rating goal</label>
              <input
                type="number"
                value={targetRating}
                onChange={(e) => setTargetRating(e.target.value)}
                className="input w-40"
                placeholder="e.g. 1900"
              />
            </div>
            <button onClick={handleSave} disabled={saving} className="btn-primary flex items-center gap-2 text-sm">
              <Save size={14} /> {saving ? 'Saving…' : 'Save profile'}
            </button>
          </div>

          <div className="grid grid-cols-2 gap-4">
            <div className="card p-4">
              <p className="text-xs text-gray-500 mb-1">Strengths</p>
              <p className="text-sm text-gray-300">
                {profile.strengths && profile.strengths.length > 0 ? profile.strengths.join(', ') : '—'}
              </p>
            </div>
            <div className="card p-4">
              <p className="text-xs text-gray-500 mb-1">Weaknesses</p>
              <p className="text-sm text-gray-300">
                {profile.weaknesses && profile.weaknesses.length > 0 ? profile.weaknesses.join(', ') : '—'}
              </p>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
