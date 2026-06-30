import { Target } from 'lucide-react'

function PlaceholderPage({ icon: Icon, title, phase }: {
  icon: React.ElementType
  title: string
  phase: string
}) {
  return (
    <div className="h-screen flex items-center justify-center p-8">
      <div className="text-center">
        <div className="w-12 h-12 rounded-xl bg-[#1c1c26] border border-[#2a2a3a] flex items-center justify-center mx-auto mb-4">
          <Icon size={20} className="text-gray-500" />
        </div>
        <h2 className="text-lg font-semibold text-white mb-2">{title}</h2>
        <p className="text-sm text-gray-500">Coming in {phase}</p>
      </div>
    </div>
  )
}

export function ProblemsPage() {
  return <PlaceholderPage icon={Target} title="Problem Recommendations" phase="Phase 7" />
}
