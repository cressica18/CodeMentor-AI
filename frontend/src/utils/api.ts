import axios from 'axios'

const api = axios.create({
  baseURL: '/api/v1',
  headers: { 'Content-Type': 'application/json' },
  timeout: 30_000,
})

api.interceptors.response.use(
  (res) => res,
  (err) => {
    const msg = err.response?.data?.detail ?? err.message ?? 'Unknown error'
    console.error('[API]', msg)
    return Promise.reject(new Error(msg))
  }
)

export default api

// ── Typed helpers ──────────────────────────────────────────────────────────

export interface HealthResponse {
  status: string
  env: string
  llm_provider: string
  database: string
  version: string
}

export interface ChatRequest {
  session_id: string
  cf_handle: string
  message: string
}

export interface ChatMessage {
  role: 'user' | 'assistant' | 'system'
  content: string
  metadata?: Record<string, unknown>
}

export interface ChatResponse {
  session_id: string
  message: ChatMessage
  agent_trace?: Array<Record<string, unknown>>
}

export const healthApi = {
  ping: () => api.get<{ ping: string }>('/health/ping'),
  status: () => api.get<HealthResponse>('/health'),
}

export const chatApi = {
  createSession: (cf_handle: string) =>
    api.post<{ session_id: string; cf_handle: string }>('/chat/session', null, {
      params: { cf_handle },
    }),
  send: (payload: ChatRequest) => api.post<ChatResponse>('/chat', payload),
}

export const usersApi = {
  create: (cf_handle: string) => api.post('/users', { cf_handle }),
  get: (cf_handle: string) => api.get(`/users/${cf_handle}`),
}

// ── Codeforces Phase 2 types ───────────────────────────────────────────────

export interface TagStat { tag: string; count: number }
export interface TagACRate { tag: string; acRate: number }

export interface RatingPoint {
  contestId: number
  contest: string
  date: string
  timestamp: number
  oldRating: number
  newRating: number
  delta: number
  rank: number
}

export interface DifficultyBucket { range: string; count: number }
export interface HeatmapPoint { date: string; count: number }

export interface CFProfileResponse {
  handle: string
  display_name: string | null
  rank: string | null
  max_rank: string | null
  current_rating: number | null
  max_rating: number | null
  country: string | null
  organization: string | null
  avatar: string | null
  contribution: number
  friend_of_count: number
  registered_at: string | null

  contests_participated: number
  solved_count: number

  rating_trend: RatingPoint[]

  most_solved_tags: TagStat[]
  tag_solve_counts: Record<string, number>
  weakest_tags: TagACRate[]
  strongest_tags: TagACRate[]
  tag_ac_rates: Record<string, number>

  difficulty_distribution: DifficultyBucket[]
  avg_solved_rating: number | null

  total_submissions: number
  accepted_count: number
  success_rate: number
  verdict_distribution: Record<string, number>
  language_distribution: Record<string, number>

  activity_heatmap: HeatmapPoint[]
}

export const codeforcesApi = {
  ingest: (handle: string, forceRefresh = false) =>
    api.post<CFProfileResponse>('/codeforces/ingest', {
      cf_handle: handle,
      force_refresh: forceRefresh,
    }),
  getProfile: (handle: string, refresh = false) =>
    api.get<CFProfileResponse>(`/codeforces/${handle}`, {
      params: { refresh },
    }),
}

// ── Phase 3 — Memory layer types ───────────────────────────────────────────

export interface UserProfile {
  id: number
  user_id: number
  bio: string | null
  goals: Record<string, unknown> | null
  strengths: string[] | null
  weaknesses: string[] | null
  current_streak_days: number
  longest_streak_days: number
  last_practice_date: string | null
  improvement_velocity: number | null
  historical_recommendation_count: number
  session_summaries: Array<{ summary: string; ts: string }> | null
  contest_history_snapshots: unknown[] | null
  created_at: string
  updated_at: string
}

export interface TopicRating {
  id: number
  user_id: number
  topic: string
  rating: number
  problems_solved: number
  problems_failed: number
  is_strength: boolean
  is_weakness: boolean
  last_practiced_at: string | null
  updated_at: string
}

export interface LearningPath {
  id: number
  user_id: number
  goal: string | null
  current_stage: string | null
  progress_percent: number
  state: Record<string, unknown> | null
  updated_at: string
}

export interface StudySession {
  id: number
  user_id: number
  topic: string | null
  duration_minutes: number | null
  problems_attempted: number
  problems_solved: number
  notes: string | null
  started_at: string
  ended_at: string | null
}

export interface LearningMilestone {
  id: number
  user_id: number
  title: string
  description: string | null
  milestone_type: string | null
  extra_data: Record<string, unknown> | null
  achieved_at: string
}

export interface SessionMemory {
  session_id: string
  user_id: number | null
  conversation_history: Array<{ role: string; content: string; ts: string }> | null
  current_goals: string[] | null
  current_problems: string[] | null
  topics_discussed: string[] | null
  agent_state: Record<string, unknown> | null
  updated_at: string
}

export interface Recommendation {
  id: number
  user_id: number
  rec_type: 'problem' | 'topic' | 'path' | 'concept'
  payload: Record<string, unknown>
  reason: string | null
  status: 'pending' | 'accepted' | 'dismissed' | 'completed'
  source: string | null
  created_at: string
}

export interface ProgressSnapshot {
  id: number
  user_id: number
  rating: number | null
  solved_count: number | null
  topic_ratings: Record<string, number> | null
  weak_topics: string[] | null
  strong_topics: string[] | null
  metrics: Record<string, unknown> | null
  snapshot_at: string
}

export interface UserPreferences {
  user_id: number
  preferred_difficulty: string | null
  preferred_topics: string[] | null
  daily_goal_minutes: number | null
  notification_settings: Record<string, unknown> | null
  theme: string | null
  language: string | null
  extra: Record<string, unknown> | null
  updated_at: string
}

export interface MemoryOverview {
  profile: UserProfile | null
  topic_ratings: TopicRating[]
  learning_path: LearningPath | null
  recent_sessions: StudySession[]
  recent_recommendations: Recommendation[]
  recent_milestones: LearningMilestone[]
  progress_snapshots: ProgressSnapshot[]
  preferences: UserPreferences | null
}

export interface ChatSessionSummary {
  session_id: string
  user_id: number
  summary: string | null
  messages: ChatMessage[] | null
  created_at: string
  updated_at: string
}

export const memoryApi = {
  getOverview: (handle: string) => api.get<MemoryOverview>(`/memory/overview/${handle}`),
  getChatSessions: (handle: string) => api.get<ChatSessionSummary[]>(`/memory/chat-sessions/${handle}`),

  getProfile: (handle: string) => api.get<UserProfile>(`/memory/profile/${handle}`),
  updateProfile: (handle: string, payload: Partial<Pick<UserProfile, 'bio' | 'goals' | 'strengths' | 'weaknesses'>>) =>
    api.put<UserProfile>(`/memory/profile/${handle}`, payload),
  touchStreak: (handle: string) => api.post<UserProfile>(`/memory/profile/${handle}/streak`),

  getTopicRatings: (handle: string) => api.get<TopicRating[]>(`/memory/topics/${handle}`),
  upsertTopicRating: (handle: string, payload: { topic: string; rating?: number; solved?: boolean; failed?: boolean }) =>
    api.put<TopicRating>(`/memory/topics/${handle}`, payload),

  getLearningPath: (handle: string) => api.get<LearningPath>(`/memory/learning-path/${handle}`),
  updateLearningPath: (
    handle: string,
    payload: Partial<Pick<LearningPath, 'goal' | 'current_stage' | 'progress_percent' | 'state'>>
  ) => api.put<LearningPath>(`/memory/learning-path/${handle}`, payload),

  getStudySessions: (handle: string) => api.get<StudySession[]>(`/memory/study-sessions/${handle}`),
  createStudySession: (
    handle: string,
    payload: Partial<Pick<StudySession, 'topic' | 'duration_minutes' | 'problems_attempted' | 'problems_solved' | 'notes'>>
  ) => api.post<StudySession>(`/memory/study-sessions/${handle}`, payload),
  endStudySession: (sessionDbId: number) => api.post<StudySession>(`/memory/study-sessions/${sessionDbId}/end`),

  getMilestones: (handle: string) => api.get<LearningMilestone[]>(`/memory/milestones/${handle}`),
  createMilestone: (
    handle: string,
    payload: { title: string; description?: string; milestone_type?: string; extra_data?: Record<string, unknown> }
  ) => api.post<LearningMilestone>(`/memory/milestones/${handle}`, payload),

  getSessionMemory: (sessionId: string) => api.get<SessionMemory>(`/memory/session/${sessionId}`),
  appendSessionMessage: (sessionId: string, role: 'user' | 'assistant' | 'system', content: string) =>
    api.post<SessionMemory>(`/memory/session/${sessionId}/messages`, { role, content }),

  getRecommendations: (handle: string, status?: string) =>
    api.get<Recommendation[]>(`/memory/recommendations/${handle}`, { params: status ? { status } : {} }),
  createRecommendation: (
    handle: string,
    payload: { rec_type: Recommendation['rec_type']; payload: Record<string, unknown>; reason?: string; source?: string }
  ) => api.post<Recommendation>(`/memory/recommendations/${handle}`, payload),
  updateRecommendationStatus: (recommendationId: number, status: Recommendation['status']) =>
    api.patch<Recommendation>(`/memory/recommendations/item/${recommendationId}`, { status }),

  getProgressSnapshots: (handle: string) => api.get<ProgressSnapshot[]>(`/memory/progress/${handle}`),
  createProgressSnapshot: (handle: string) => api.post<ProgressSnapshot>(`/memory/progress/${handle}/snapshot`),

  getPreferences: (handle: string) => api.get<UserPreferences>(`/memory/preferences/${handle}`),
  updatePreferences: (handle: string, payload: Partial<UserPreferences>) =>
    api.put<UserPreferences>(`/memory/preferences/${handle}`, payload),
}

// -- Phase 4 -- Agentic workflow types ---------------------------------

export interface AnalyzerOutput {
  strengths: string[]
  weaknesses: string[]
  priority_topics: string[]
  improvement_velocity: number
  analysis_summary: string
}

export interface MilestoneItem {
  order: number
  title: string
  topic: string
  target_problems_solved: number
  type: string
}

export interface WeeklyScheduleItem {
  week: number
  focus_topic: string
  sessions_planned: number
  goal: string
  revision: boolean
}

export interface PlannerOutputSchema {
  study_plan: Record<string, unknown>
  milestones: MilestoneItem[]
  weekly_schedule: WeeklyScheduleItem[]
  priority_topics: string[]
  estimated_duration: string
}

export interface AgentRun {
  id: number
  user_id: number
  cf_handle: string
  run_type: 'analyze' | 'plan' | 'full'
  status: 'pending' | 'running' | 'completed' | 'failed'
  thread_id: string
  error: string | null
  started_at: string
  finished_at: string | null
  duration_ms: number | null
}

export interface AgentTrace {
  id: number
  agent_run_id: number
  step_index: number
  node_name: string
  status: string
  input_summary: Record<string, unknown> | null
  output_summary: Record<string, unknown> | null
  tool_calls: unknown[] | null
  error: string | null
  started_at: string
  finished_at: string | null
  duration_ms: number | null
}

export interface AgentRunResult {
  run: AgentRun
  traces: AgentTrace[]
  analysis: AnalyzerOutput | null
  plan: PlannerOutputSchema | null
  recommendations: RecommenderOutputSchema | null
}

export interface RecommendedProblemPreview {
  contest_id: number | null
  index: string
  problem_name: string
  rating: number | null
  tags: string[]
  recommendation_type: string
  recommendation_score: number
  recommendation_reason: string | null
  difficulty_match_score: number | null
  estimated_solve_minutes: number | null
  url: string | null
}

export interface RecommenderOutputSchema {
  recommendations: RecommendedProblemPreview[]
  strategy: Record<string, unknown>
  reasoning: string
}

export interface AnalysisSnapshot {
  id: number
  user_id: number
  agent_run_id: number | null
  strengths: string[] | null
  weaknesses: string[] | null
  priority_topics: string[] | null
  improvement_velocity: number | null
  analysis_summary: string | null
  raw_output: Record<string, unknown> | null
  created_at: string
}

export interface PlannerOutputRead {
  id: number
  user_id: number
  agent_run_id: number | null
  analysis_snapshot_id: number | null
  study_plan: Record<string, unknown> | null
  milestones: MilestoneItem[] | null
  weekly_schedule: WeeklyScheduleItem[] | null
  priority_topics: string[] | null
  estimated_duration: string | null
  raw_output: Record<string, unknown> | null
  created_at: string
}

export const agentsApi = {
  analyze: (cf_handle: string) => api.post<AgentRunResult>('/agents/analyze', { cf_handle }),
  plan: (cf_handle: string) => api.post<AgentRunResult>('/agents/plan', { cf_handle }),
  run: (cf_handle: string) => api.post<AgentRunResult>('/agents/run', { cf_handle }),
  getHistory: (cf_handle?: string, limit = 50) =>
    api.get<AgentRun[]>('/agents/history', { params: { cf_handle, limit } }),
  getTraces: (agent_run_id: number) => api.get<AgentTrace[]>('/agents/traces', { params: { agent_run_id } }),
  getLatestAnalysis: (cf_handle: string) => api.get<AnalysisSnapshot>(`/agents/analysis/${cf_handle}/latest`),
  getLatestPlan: (cf_handle: string) => api.get<PlannerOutputRead>(`/agents/plan/${cf_handle}/latest`),
}

// -- Phase 5 -- Problem Recommender Agent types ---------------------------

export type RecommendationType = 'reinforcement' | 'advancement' | 'recovery' | 'contest_prep'

export interface RecommendedProblem {
  id: number
  user_id: number
  recommendation_session_id: number | null
  contest_id: number | null
  index: string
  problem_name: string
  rating: number | null
  tags: string[] | null
  recommendation_type: RecommendationType
  recommendation_score: number
  recommendation_reason: string | null
  difficulty_match_score: number | null
  estimated_solve_minutes: number | null
  url: string | null
  solved: boolean
  attempted: boolean
  skipped: boolean
  bookmarked: boolean
  recommended_at: string
  updated_at: string
}

export type ProblemAction = 'solve' | 'skip' | 'bookmark' | 'unbookmark' | 'attempt'

export const recommendationsApi = {
  generate: (cf_handle: string) =>
    api.post<RecommendedProblem[]>('/recommendations/generate', { cf_handle }),
  list: (cf_handle: string, status?: 'pending' | 'solved' | 'bookmarked') =>
    api.get<RecommendedProblem[]>(`/recommendations/${cf_handle}`, { params: status ? { status } : {} }),
  updateStatus: (id: number, action: ProblemAction, time_spent_minutes?: number) =>
    api.patch<RecommendedProblem>(`/recommendations/item/${id}`, { action, time_spent_minutes }),
}
