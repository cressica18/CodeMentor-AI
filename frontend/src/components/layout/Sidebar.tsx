import { NavLink } from 'react-router-dom'
import {
  MessageSquare, LayoutDashboard, BookOpen, Target, History,
  Zap, Code2, Brain, UserCircle, TrendingUp, Settings, Bot, Calendar, Sparkles, Activity,
} from 'lucide-react'
import { cn } from '@/utils/cn'

const NAV = [
  { to: '/',                    icon: LayoutDashboard, label: 'Home'           },
  { to: '/mentor',               icon: Sparkles,        label: 'Mentor Dashboard' },
  { to: '/profile',             icon: Code2,           label: 'CF Profile'     },
  { to: '/chat',                icon: MessageSquare,   label: 'Chat'           },
  { to: '/roadmap',             icon: BookOpen,        label: 'Learning Path'  },
  { to: '/problems',            icon: Target,          label: 'Problems'       },
  { to: '/status',              icon: Activity,        label: 'System Status'  },
]

const AGENTS_NAV = [
  { to: '/agents',            icon: Bot,      label: 'Agent Dashboard' },
  { to: '/agents/planner',    icon: Calendar, label: 'Study Planner'   },
]

const MEMORY_NAV = [
  { to: '/memory',               icon: Brain,       label: 'Memory Overview' },
  { to: '/memory/profile',       icon: UserCircle,  label: 'User Profile'    },
  { to: '/memory/history',       icon: History,     label: 'Learning History'},
  { to: '/memory/progress',      icon: TrendingUp,  label: 'Progress'        },
  { to: '/memory/preferences',   icon: Settings,    label: 'Preferences'     },
]

function NavGroup({ items }: { items: typeof NAV }) {
  return (
    <>
      {items.map(({ to, icon: Icon, label }) => (
        <NavLink
          key={to}
          to={to}
          end={to === '/' || to === '/memory' || to === '/agents'}
          className={({ isActive }) =>
            cn(
              'flex items-center gap-3 px-3 py-2 rounded-lg text-sm transition-colors',
              isActive
                ? 'bg-brand-600/20 text-brand-400 font-medium'
                : 'text-gray-400 hover:text-gray-200 hover:bg-white/5'
            )
          }
        >
          <Icon size={16} />
          {label}
        </NavLink>
      ))}
    </>
  )
}

export default function Sidebar() {
  return (
    <aside className="w-60 flex-shrink-0 flex flex-col bg-[#16161d] border-r border-[#2a2a3a] h-screen sticky top-0">
      {/* Logo */}
      <div className="flex items-center gap-2 px-5 py-5 border-b border-[#2a2a3a]">
        <div className="w-8 h-8 rounded-lg bg-brand-600 flex items-center justify-center">
          <Zap size={16} className="text-white" />
        </div>
        <span className="font-semibold text-white text-sm tracking-wide">CodeMentor AI</span>
      </div>

      {/* Nav */}
      <nav className="flex-1 px-3 py-4 space-y-1 overflow-y-auto">
        <NavGroup items={NAV} />

        <p className="px-3 pt-4 pb-1 text-[10px] uppercase tracking-wider text-gray-600">Agents</p>
        <NavGroup items={AGENTS_NAV} />

        <p className="px-3 pt-4 pb-1 text-[10px] uppercase tracking-wider text-gray-600">Memory</p>
        <NavGroup items={MEMORY_NAV} />
      </nav>

      {/* Footer */}
      <div className="px-4 py-4 border-t border-[#2a2a3a]">
        <p className="text-xs text-gray-600">AI Mentor Workflow</p>
        <p className="text-xs text-gray-700 mt-0.5">v1.0.0</p>
      </div>
    </aside>
  )
}