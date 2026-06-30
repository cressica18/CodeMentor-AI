import {
  BarChart, Bar, XAxis, YAxis, CartesianGrid,
  Tooltip, ResponsiveContainer, Cell,
} from 'recharts'
import type { TagStat, TagACRate } from '@/utils/api'

// ── Most Solved Tags (bar chart) ──────────────────────────────────────────

interface SolvedProps {
  data: TagStat[]
  height?: number
}

const COLORS = [
  '#4f46e5', '#6366f1', '#818cf8', '#a5b4fc',
  '#7c3aed', '#8b5cf6', '#a78bfa', '#c4b5fd',
  '#2563eb', '#3b82f6',
]

export function TopicSolvedChart({ data, height = 220 }: SolvedProps) {
  if (!data.length) return <p className="text-gray-500 text-sm">No data</p>

  const sorted = [...data].sort((a, b) => b.count - a.count).slice(0, 10)

  return (
    <ResponsiveContainer width="100%" height={height}>
      <BarChart
        data={sorted}
        layout="vertical"
        margin={{ top: 0, right: 16, bottom: 0, left: 0 }}
      >
        <CartesianGrid strokeDasharray="3 3" stroke="#2a2a3a" horizontal={false} />
        <XAxis
          type="number"
          tick={{ fill: '#6b7280', fontSize: 10 }}
          tickLine={false}
          axisLine={false}
        />
        <YAxis
          type="category"
          dataKey="tag"
          width={110}
          tick={{ fill: '#9ca3af', fontSize: 11 }}
          tickLine={false}
          axisLine={false}
        />
        <Tooltip
          contentStyle={{
            backgroundColor: '#1c1c26',
            border: '1px solid #2a2a3a',
            borderRadius: 8,
            fontSize: 12,
          }}
          labelStyle={{ color: '#e5e7eb' }}
          formatter={(v: number) => [`${v} problems`, 'Solved']}
        />
        <Bar dataKey="count" radius={[0, 4, 4, 0]}>
          {sorted.map((_, i) => (
            <Cell key={i} fill={COLORS[i % COLORS.length]} />
          ))}
        </Bar>
      </BarChart>
    </ResponsiveContainer>
  )
}

// ── Weak/Strong tag comparison ─────────────────────────────────────────────

interface WeaknessProps {
  weakest: TagACRate[]
  strongest: TagACRate[]
}

export function WeaknessStrengthPanel({ weakest, strongest }: WeaknessProps) {
  return (
    <div className="grid grid-cols-2 gap-4">
      <div>
        <p className="text-xs text-red-400 font-medium uppercase tracking-widest mb-3">
          Weakest Topics
        </p>
        <div className="space-y-2">
          {weakest.slice(0, 6).map((t) => (
            <div key={t.tag} className="flex items-center justify-between">
              <span className="text-xs text-gray-300 capitalize truncate max-w-[120px]">
                {t.tag}
              </span>
              <div className="flex items-center gap-2">
                <div className="w-20 h-1.5 bg-[#2a2a3a] rounded-full overflow-hidden">
                  <div
                    className="h-full bg-red-500 rounded-full"
                    style={{ width: `${Math.round(t.acRate * 100)}%` }}
                  />
                </div>
                <span className="text-xs text-gray-500 w-8 text-right">
                  {Math.round(t.acRate * 100)}%
                </span>
              </div>
            </div>
          ))}
        </div>
      </div>

      <div>
        <p className="text-xs text-emerald-400 font-medium uppercase tracking-widest mb-3">
          Strongest Topics
        </p>
        <div className="space-y-2">
          {strongest.slice(0, 6).map((t) => (
            <div key={t.tag} className="flex items-center justify-between">
              <span className="text-xs text-gray-300 capitalize truncate max-w-[120px]">
                {t.tag}
              </span>
              <div className="flex items-center gap-2">
                <div className="w-20 h-1.5 bg-[#2a2a3a] rounded-full overflow-hidden">
                  <div
                    className="h-full bg-emerald-500 rounded-full"
                    style={{ width: `${Math.round(t.acRate * 100)}%` }}
                  />
                </div>
                <span className="text-xs text-gray-500 w-8 text-right">
                  {Math.round(t.acRate * 100)}%
                </span>
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  )
}
