import { CheckCircle2, Circle } from 'lucide-react'
import { cn } from '@/utils/cn'
import type { MilestoneItem } from '@/utils/api'

interface Props {
  milestones: MilestoneItem[]
  completedCount?: number
  className?: string
}

/**
 * Renders milestones as a left-to-right (desktop) / top-to-bottom
 * (mobile) roadmap, e.g. Graphs -> Trees -> Shortest Paths -> DP,
 * with a simple "completed so far" progress indicator per the Phase 5
 * spec's Learning Roadmap requirement.
 */
export default function LearningRoadmap({ milestones, completedCount = 0, className }: Props) {
  if (milestones.length === 0) return null

  return (
    <div className={className}>
      <div className="flex flex-col md:flex-row md:items-center gap-0 md:gap-2 overflow-x-auto pb-2">
        {milestones.map((m, i) => {
          const done = i < completedCount
          return (
            <div key={m.order} className="flex items-center md:flex-col flex-1 min-w-[140px]">
              <div className="flex md:flex-col items-center gap-3 md:gap-2 flex-1">
                <div
                  className={cn(
                    'w-9 h-9 rounded-full flex items-center justify-center flex-shrink-0 border-2',
                    done ? 'bg-emerald-500/20 border-emerald-500 text-emerald-400' : 'bg-white/5 border-[#2a2a3a] text-gray-500'
                  )}
                >
                  {done ? <CheckCircle2 size={16} /> : <Circle size={16} />}
                </div>
                <div className="md:text-center">
                  <p className="text-xs font-medium text-gray-200">{m.topic}</p>
                  <p className="text-[10px] text-gray-500">{m.target_problems_solved} problems</p>
                </div>
              </div>
              {i < milestones.length - 1 && (
                <div className="hidden md:block flex-1 h-0.5 bg-[#2a2a3a] mx-1 mt-[-22px]" />
              )}
            </div>
          )
        })}
      </div>
    </div>
  )
}
