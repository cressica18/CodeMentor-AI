import {
  LineChart, Line, XAxis, YAxis, CartesianGrid,
  Tooltip, ResponsiveContainer, ReferenceLine,
} from 'recharts'
import type { RatingPoint } from '@/utils/api'

interface Props {
  data: RatingPoint[]
  height?: number
}

function getRatingColor(rating: number): string {
  if (rating >= 3000) return '#FF0000'
  if (rating >= 2600) return '#FF3333'
  if (rating >= 2400) return '#FF7777'
  if (rating >= 2100) return '#FFBB55'
  if (rating >= 1900) return '#FF8C00'
  if (rating >= 1600) return '#AA00AA'
  if (rating >= 1400) return '#0000FF'
  if (rating >= 1200) return '#03A89E'
  if (rating >= 1000) return '#008000'
  return '#808080'
}

const CustomTooltip = ({ active, payload }: any) => {
  if (!active || !payload?.length) return null
  const d: RatingPoint = payload[0].payload
  const color = getRatingColor(d.newRating)
  return (
    <div className="bg-[#1c1c26] border border-[#2a2a3a] rounded-lg p-3 text-xs shadow-xl">
      <p className="text-gray-300 font-medium mb-1 max-w-[200px] truncate">{d.contest}</p>
      <p className="text-gray-500 mb-2">{d.date}</p>
      <div className="flex gap-4">
        <span className="text-gray-400">Rating <span style={{ color }} className="font-bold">{d.newRating}</span></span>
        <span className={`font-semibold ${d.delta >= 0 ? 'text-emerald-400' : 'text-red-400'}`}>
          {d.delta >= 0 ? '+' : ''}{d.delta}
        </span>
        <span className="text-gray-500">Rank #{d.rank}</span>
      </div>
    </div>
  )
}

export default function RatingChart({ data, height = 240 }: Props) {
  if (!data.length) {
    return (
      <div className="flex items-center justify-center text-gray-500 text-sm" style={{ height }}>
        No contest history available
      </div>
    )
  }

  const maxRating = Math.max(...data.map(d => d.newRating))
  const minRating = Math.min(...data.map(d => d.newRating))

  const THRESHOLDS = [1200, 1400, 1600, 1900, 2100, 2400, 2600, 3000]

  return (
    <ResponsiveContainer width="100%" height={height}>
      <LineChart data={data} margin={{ top: 8, right: 12, bottom: 0, left: 0 }}>
        <CartesianGrid strokeDasharray="3 3" stroke="#2a2a3a" />
        <XAxis
          dataKey="date"
          tick={{ fill: '#6b7280', fontSize: 10 }}
          tickLine={false}
          axisLine={false}
          interval="preserveStartEnd"
        />
        <YAxis
          domain={[Math.max(0, minRating - 100), maxRating + 100]}
          tick={{ fill: '#6b7280', fontSize: 10 }}
          tickLine={false}
          axisLine={false}
          width={42}
        />
        <Tooltip content={<CustomTooltip />} />
        {THRESHOLDS.filter(t => t > minRating - 100 && t < maxRating + 100).map(t => (
          <ReferenceLine
            key={t}
            y={t}
            stroke={getRatingColor(t)}
            strokeDasharray="4 3"
            strokeOpacity={0.3}
          />
        ))}
        <Line
          type="monotone"
          dataKey="newRating"
          stroke="#4f46e5"
          strokeWidth={2}
          dot={data.length < 30 ? { r: 3, fill: '#4f46e5' } : false}
          activeDot={{ r: 5, fill: '#818cf8' }}
        />
      </LineChart>
    </ResponsiveContainer>
  )
}
