import {
  BarChart, Bar, XAxis, YAxis, Tooltip,
  CartesianGrid, ResponsiveContainer, Cell,
} from 'recharts'
import type { DifficultyBucket } from '@/utils/api'

interface Props {
  data: DifficultyBucket[]
  height?: number
}

function bucketColor(range: string): string {
  if (range === 'Unrated') return '#4b5563'
  const lo = parseInt(range.replace(/[^0-9].*/,''), 10)
  if (isNaN(lo)) return '#4b5563'
  if (lo < 800)  return '#6b7280'
  if (lo < 1200) return '#10b981'
  if (lo < 1600) return '#3b82f6'
  if (lo < 2000) return '#8b5cf6'
  if (lo < 2400) return '#f59e0b'
  if (lo < 2800) return '#ef4444'
  return '#dc2626'
}

export default function DifficultyChart({ data, height = 180 }: Props) {
  if (!data.length) return <p className="text-gray-500 text-sm">No data</p>

  return (
    <ResponsiveContainer width="100%" height={height}>
      <BarChart data={data} margin={{ top: 0, right: 8, bottom: 0, left: 0 }}>
        <CartesianGrid strokeDasharray="3 3" stroke="#2a2a3a" vertical={false} />
        <XAxis
          dataKey="range"
          tick={{ fill: '#6b7280', fontSize: 9 }}
          tickLine={false}
          axisLine={false}
          angle={-40}
          textAnchor="end"
          height={42}
        />
        <YAxis
          tick={{ fill: '#6b7280', fontSize: 10 }}
          tickLine={false}
          axisLine={false}
          width={30}
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
        <Bar dataKey="count" radius={[4, 4, 0, 0]}>
          {data.map((entry, i) => (
            <Cell key={i} fill={bucketColor(entry.range)} />
          ))}
        </Bar>
      </BarChart>
    </ResponsiveContainer>
  )
}
