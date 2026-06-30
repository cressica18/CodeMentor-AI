import { createBrowserRouter } from 'react-router-dom'
import AppLayout from '@/components/layout/AppLayout'
import MentorHomePage from '@/pages/MentorHomePage'
import MentorDashboardPage from '@/pages/MentorDashboardPage'
import DashboardPage from '@/pages/DashboardPage'
import ChatPage from '@/pages/ChatPage'
import CFProfilePage from '@/pages/CFProfilePage'
import LearningPathPage from '@/pages/LearningPathPage'
import ProblemRecommendationsPage from '@/pages/ProblemRecommendationsPage'
import MemoryOverviewPage from '@/pages/MemoryOverviewPage'
import UserProfilePage from '@/pages/UserProfilePage'
import LearningHistoryPage from '@/pages/LearningHistoryPage'
import ProgressTrackingPage from '@/pages/ProgressTrackingPage'
import UserPreferencesPage from '@/pages/UserPreferencesPage'
import AgentDashboardPage from '@/pages/AgentDashboardPage'
import StudyPlannerPage from '@/pages/StudyPlannerPage'

export const router = createBrowserRouter([
  {
    path: '/',
    element: <AppLayout />,
    children: [
      // Phase 5 — landing page: enter CF handle, click "Analyze My Profile",
      // and the entire mentor workflow (ingest -> agents/run -> recommendations)
      // runs automatically, then redirects to /mentor.
      { index: true,              element: <MentorHomePage />        },
      { path: 'mentor',           element: <MentorDashboardPage />   },
      { path: 'status',           element: <DashboardPage />         },
      { path: 'chat',             element: <ChatPage />              },
      { path: 'profile',          element: <CFProfilePage />         },
      { path: 'roadmap',          element: <LearningPathPage />      },
      { path: 'problems',         element: <ProblemRecommendationsPage /> },
      { path: 'memory',           element: <MemoryOverviewPage />    },
      { path: 'memory/profile',   element: <UserProfilePage />       },
      { path: 'memory/history',   element: <LearningHistoryPage />   },
      { path: 'memory/progress',  element: <ProgressTrackingPage />  },
      { path: 'memory/preferences', element: <UserPreferencesPage />},
      { path: 'agents',           element: <AgentDashboardPage />    },
      { path: 'agents/planner',   element: <StudyPlannerPage />      },
    ],
  },
])
