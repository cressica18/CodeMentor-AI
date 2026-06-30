import { CheckCircle2, SkipForward, Bookmark, BookmarkCheck, Clock, ExternalLink, Target } from 'lucide-react'
import { cn } from '@/utils/cn'
import type { RecommendedProblem } from '@/utils/api'

interface Props {
  problem: RecommendedProblem
  onSolve: (id: number) => void
  onSkip: (id: number) => void
  onToggleBookmark: (id: number, bookmarked: boolean) => void
  busy?: boolean
}

const TYPE_LABELS: Record<string, { label: string; className: string }> = {
  reinforcement: { label: 'Reinforcement', className: 'bg-amber-500/15 text-amber-400' },
  advancement: { label: 'Advancement', className: 'bg-emerald-500/15 text-emerald-400' },
  recovery: { label: 'Recovery', className: 'bg-sky-500/15 text-sky-400' },
  contest_prep: { label: 'Contest Prep', className: 'bg-violet-500/15 text-violet-400' },
}

function ratingColor(rating: number | null): string {
  if (!rating) return '#9ca3af'
  if (rating >= 2400) return '#FF3333'
  if (rating >= 2100) return '#FFBB55'
  if (rating >= 1900) return '#FF8C00'
  if (rating >= 1600) return '#AA00AA'
  if (rating >= 1400) return '#0000FF'
  if (rating >= 1200) return '#03A89E'
  return '#008000'
}

export default function ProblemCard({ problem, onSolve, onSkip, onToggleBookmark, busy }: Props) {
  const typeMeta = TYPE_LABELS[problem.recommendation_type] ?? { label: problem.recommendation_type, className: 'bg-gray-500/15 text-gray-400' }
  const matchPct = problem.difficulty_match_score != null ? Math.round(problem.difficulty_match_score * 100) : null

  return (
    <div
      className={cn(
        'card p-4 flex flex-col gap-3 transition-opacity',
        problem.solved && 'opacity-60',
        problem.skipped && 'opacity-40'
      )}
    >
      <div className="flex items-start justify-between gap-2">
        <div>
          <p className="text-sm font-semibold text-white leading-snug">
            {problem.contest_id}
            {problem.index} — {problem.problem_name}
          </p>
          <div className="flex items-center gap-2 mt-1 text-xs">
            <span className="font-medium" style={{ color: ratingColor(problem.rating) }}>
              {problem.rating ?? '—'}
            </span>
            <span className={cn('px-1.5 py-0.5 rounded-full', typeMeta.className)}>{typeMeta.label}</span>
          </div>
        </div>
        <button
          onClick={() => onToggleBookmark(problem.id, !problem.bookmarked)}
          className="text-gray-500 hover:text-amber-400 transition-colors flex-shrink-0"
          title={problem.bookmarked ? 'Remove bookmark' : 'Bookmark'}
        >
          {problem.bookmarked ? <BookmarkCheck size={16} className="text-amber-400" /> : <Bookmark size={16} />}
        </button>
      </div>

      {problem.tags && problem.tags.length > 0 && (
        <div className="flex flex-wrap gap-1.5">
          {problem.tags.slice(0, 4).map((t) => (
            <span key={t} className="text-[10px] px-1.5 py-0.5 rounded bg-white/5 text-gray-400">
              {t}
            </span>
          ))}
        </div>
      )}

      {problem.recommendation_reason && (
        <p className="text-xs text-gray-500 leading-relaxed">{problem.recommendation_reason}</p>
      )}

      <div className="flex items-center gap-3 text-xs text-gray-500">
        {problem.estimated_solve_minutes != null && (
          <span className="flex items-center gap-1">
            <Clock size={11} /> ~{problem.estimated_solve_minutes} min
          </span>
        )}
        {matchPct != null && (
          <span className="flex items-center gap-1">
            <Target size={11} /> {matchPct}% match
          </span>
        )}
        {problem.url && (
          <a
            href={problem.url}
            target="_blank"
            rel="noreferrer"
            className="flex items-center gap-1 text-brand-400 hover:text-brand-300 ml-auto"
          >
            Open on CF <ExternalLink size={11} />
          </a>
        )}
      </div>

      <div className="flex items-center gap-2 pt-1 border-t border-[#2a2a3a]">
        <button
          onClick={() => onSolve(problem.id)}
          disabled={busy || problem.solved}
          className="flex-1 flex items-center justify-center gap-1.5 text-xs font-medium px-2 py-1.5 rounded-lg bg-emerald-600/15 text-emerald-400 hover:bg-emerald-600/25 disabled:opacity-40 transition-colors"
        >
          <CheckCircle2 size={13} /> {problem.solved ? 'Solved' : 'Solve'}
        </button>
        <button
          onClick={() => onSkip(problem.id)}
          disabled={busy || problem.skipped || problem.solved}
          className="flex-1 flex items-center justify-center gap-1.5 text-xs font-medium px-2 py-1.5 rounded-lg bg-white/5 text-gray-400 hover:bg-white/10 disabled:opacity-40 transition-colors"
        >
          <SkipForward size={13} /> {problem.skipped ? 'Skipped' : 'Skip'}
        </button>
      </div>
    </div>
  )
}
