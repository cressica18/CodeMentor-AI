import type { CFProfileResponse } from '@/utils/api'
import { Trophy, MapPin, Building2, Users, RefreshCw } from 'lucide-react'

interface Props {
  profile: CFProfileResponse
  onRefresh?: () => void
  isRefreshing?: boolean
}

function ratingColor(rating: number | null): string {
  if (!rating) return '#9ca3af'
  if (rating >= 3000) return '#FF0000'
  if (rating >= 2600) return '#FF3333'
  if (rating >= 2400) return '#FF7777'
  if (rating >= 2100) return '#FFBB55'
  if (rating >= 1900) return '#FF8C00'
  if (rating >= 1600) return '#AA00AA'
  if (rating >= 1400) return '#0000FF'
  if (rating >= 1200) return '#03A89E'
  if (rating >= 1000) return '#008000'
  return '#9ca3af'
}

export default function CFProfileCard({ profile, onRefresh, isRefreshing }: Props) {
  const color = ratingColor(profile.current_rating)

  return (
    <div className="card p-5">
      <div className="flex items-start gap-4">
        {/* Avatar */}
        <div className="flex-shrink-0">
          {profile.avatar ? (
            <img
              src={profile.avatar}
              alt={profile.handle}
              className="w-16 h-16 rounded-full object-cover ring-2 ring-[#2a2a3a]"
              onError={(e) => { (e.target as HTMLImageElement).style.display = 'none' }}
            />
          ) : (
            <div className="w-16 h-16 rounded-full bg-brand-600/20 flex items-center justify-center">
              <span className="text-2xl font-bold text-brand-400">
                {profile.handle[0].toUpperCase()}
              </span>
            </div>
          )}
        </div>

        {/* Info */}
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 flex-wrap">
            <h2 className="text-xl font-bold text-white">{profile.handle}</h2>
            {profile.display_name && profile.display_name !== profile.handle && (
              <span className="text-sm text-gray-400">({profile.display_name})</span>
            )}
          </div>
          <p className="text-sm capitalize" style={{ color }}>
            {profile.rank ?? 'unrated'}
          </p>
          <div className="flex flex-wrap items-center gap-x-4 gap-y-1 mt-2">
            {profile.country && (
              <span className="flex items-center gap-1 text-xs text-gray-500">
                <MapPin size={11} />{profile.country}
              </span>
            )}
            {profile.organization && (
              <span className="flex items-center gap-1 text-xs text-gray-500">
                <Building2 size={11} />{profile.organization}
              </span>
            )}
            <span className="flex items-center gap-1 text-xs text-gray-500">
              <Users size={11} />{profile.friend_of_count.toLocaleString()} followers
            </span>
          </div>
        </div>

        {/* Rating badge */}
        <div className="flex-shrink-0 text-right">
          <p className="text-3xl font-black" style={{ color }}>
            {profile.current_rating ?? '—'}
          </p>
          <p className="text-xs text-gray-500">
            max <span style={{ color }}>{profile.max_rating ?? '—'}</span>
          </p>
          {onRefresh && (
            <button
              onClick={onRefresh}
              disabled={isRefreshing}
              className="mt-2 flex items-center gap-1 text-xs text-gray-500 hover:text-gray-300 transition-colors ml-auto"
            >
              <RefreshCw size={11} className={isRefreshing ? 'animate-spin' : ''} />
              Refresh
            </button>
          )}
        </div>
      </div>

      {/* Stats row */}
      <div className="grid grid-cols-3 gap-3 mt-4 pt-4 border-t border-[#2a2a3a]">
        <div className="text-center">
          <p className="text-lg font-bold text-white">{profile.solved_count}</p>
          <p className="text-xs text-gray-500">Problems Solved</p>
        </div>
        <div className="text-center border-x border-[#2a2a3a]">
          <p className="text-lg font-bold text-white">{profile.contests_participated}</p>
          <p className="text-xs text-gray-500">Contests</p>
        </div>
        <div className="text-center">
          <p className="text-lg font-bold text-white">
            {Math.round(profile.success_rate * 100)}%
          </p>
          <p className="text-xs text-gray-500">AC Rate</p>
        </div>
      </div>
    </div>
  )
}
