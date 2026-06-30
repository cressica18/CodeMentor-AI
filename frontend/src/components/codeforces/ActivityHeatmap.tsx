import type { HeatmapPoint } from '@/utils/api'

interface Props {
  data: HeatmapPoint[]
}

function intensityClass(count: number): string {
  if (count === 0) return 'bg-[#1c1c26]'
  if (count <= 2)  return 'bg-brand-800'
  if (count <= 5)  return 'bg-brand-700'
  if (count <= 10) return 'bg-brand-600'
  return 'bg-brand-500'
}

function getWeeks(data: HeatmapPoint[]): HeatmapPoint[][] {
  // data is already sorted oldest→newest, 365 entries
  const weeks: HeatmapPoint[][] = []
  for (let i = 0; i < data.length; i += 7) {
    weeks.push(data.slice(i, i + 7))
  }
  return weeks
}

const MONTHS = ['Jan','Feb','Mar','Apr','May','Jun','Jul','Aug','Sep','Oct','Nov','Dec']

export default function ActivityHeatmap({ data }: Props) {
  if (!data.length) return null

  const weeks = getWeeks(data)
  // Derive month labels from the start of each week
  const monthLabels: { month: string; col: number }[] = []
  let lastMonth = -1
  weeks.forEach((week, i) => {
    if (week[0]) {
      const m = new Date(week[0].date).getMonth()
      if (m !== lastMonth) {
        monthLabels.push({ month: MONTHS[m], col: i })
        lastMonth = m
      }
    }
  })

  const totalSubmissions = data.reduce((acc, d) => acc + d.count, 0)
  const activeDays = data.filter(d => d.count > 0).length

  return (
    <div>
      <div className="flex items-center justify-between mb-3">
        <p className="text-xs text-gray-500">
          <span className="text-gray-200 font-medium">{totalSubmissions}</span> submissions
          over the last year &bull;&nbsp;
          <span className="text-gray-200 font-medium">{activeDays}</span> active days
        </p>
        <div className="flex items-center gap-1 text-xs text-gray-600">
          Less
          {[0,2,5,10,15].map((v,i) => (
            <span key={i} className={`w-3 h-3 rounded-sm ${intensityClass(v)}`} />
          ))}
          More
        </div>
      </div>

      <div className="overflow-x-auto">
        <div className="relative min-w-max">
          {/* Month labels */}
          <div className="flex mb-1 ml-7" style={{ gap: '2px' }}>
            {weeks.map((_, i) => {
              const label = monthLabels.find(m => m.col === i)
              return (
                <div key={i} className="w-3 text-center">
                  {label && (
                    <span className="text-[9px] text-gray-600 whitespace-nowrap">
                      {label.month}
                    </span>
                  )}
                </div>
              )
            })}
          </div>

          <div className="flex" style={{ gap: '2px' }}>
            {/* Day-of-week labels */}
            <div className="flex flex-col mr-1" style={{ gap: '2px' }}>
              {['', 'M', '', 'W', '', 'F', ''].map((d, i) => (
                <div key={i} className="w-5 h-3 flex items-center justify-end">
                  <span className="text-[9px] text-gray-600">{d}</span>
                </div>
              ))}
            </div>

            {/* Heatmap grid */}
            {weeks.map((week, wi) => (
              <div key={wi} className="flex flex-col" style={{ gap: '2px' }}>
                {week.map((day, di) => (
                  <div
                    key={di}
                    title={`${day.date}: ${day.count} submissions`}
                    className={`w-3 h-3 rounded-sm cursor-default transition-opacity hover:opacity-80 ${intensityClass(day.count)}`}
                  />
                ))}
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  )
}
