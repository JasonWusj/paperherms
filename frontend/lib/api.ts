export const API_BASE = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000/api";
const SERVER_API_BASE = process.env.INTERNAL_API_BASE_URL ?? API_BASE;

export function resolveApiBase() {
  if (typeof window === "undefined") {
    return SERVER_API_BASE;
  }
  if (API_BASE !== "/api") {
    return API_BASE;
  }
  if (window.location.port === "3000") {
    return `${window.location.protocol}//${window.location.hostname}:8000/api`;
  }
  return "/api";
}

export type Paper = {
  id: string;
  title: string;
  authors: string[];
  abstract: string;
  original_filename: string;
  status: string;
  created_at: string;
};

export type Memory = {
  id: string;
  user_id: string;
  memory_type: string;
  content: string;
  metadata_json: Record<string, unknown>;
  created_at: string;
  updated_at: string;
};

export type Skill = {
  id: string;
  name: string;
  description: string;
  prompt_template: string;
  usage_count: number;
  metadata_json: Record<string, unknown>;
  created_at: string;
  updated_at: string;
};

export type ReviewStatus = "draft" | "active" | "rejected" | "archived";

export type TraceStep = {
  id: string;
  task_id: string;
  user_id: string;
  agent_name: string;
  step_name: string;
  input_json: Record<string, unknown>;
  output_json: Record<string, unknown>;
  tool_calls: Record<string, unknown>[];
  retrieved_chunks: Record<string, unknown>[];
  latency_ms: number;
  token_usage: Record<string, unknown>;
  error: string | null;
  status: string;
  created_at: string;
};

export type AgentTask = {
  id: string;
  user_id: string;
  paper_id: string | null;
  task_type: string;
  input_text: string;
  output_text: string;
  status: string;
  metadata_json: Record<string, unknown>;
  created_at: string;
  updated_at: string;
};

export type AgentTaskLearning = {
  task_id: string;
  learning_traces: TraceStep[];
  memory_candidates: Memory[];
  skill_candidates: Skill[];
  workflow_lessons: Record<string, unknown>[];
};

export type Citation = {
  id: string;
  paper_id: string;
  text: string;
  section_title: string;
  score: number;
  page_start: number | null;
  page_end: number | null;
};

export type AgentAnswer = {
  task_id: string;
  answer: string;
  citations: Citation[];
  policy_decision?: Record<string, unknown>;
  model_version?: string | null;
  metrics?: Record<string, unknown>;
};

export type FeedbackSubmission = {
  feedback: {
    id: string;
    task_id: string;
    user_id: string;
    rating: -1 | 1;
    issue_tags: string[];
    comment: string;
  };
  reward: {
    id: string;
    reward_type: string;
    reward: number;
    components: Record<string, unknown>;
  };
};

export type PolicySummary = {
  policy_name: string;
  policy_version: string;
  actions: string[];
  counts: Record<string, number>;
  total_updates: number;
  average_reward_by_action: Record<string, number>;
};

export type RewardSummary = {
  event_count: number;
  feedback_count: number;
  average_reward: number;
  average_final_reward: number;
};

export type PolicyReplay = {
  method: string;
  sample_count: number;
  cumulative_regret: number;
  policies: Record<string, { estimated_reward: number; matched_samples: number }>;
  observed_arm_means: Record<string, number>;
  warning: string;
};

async function request<T>(path: string, options?: RequestInit): Promise<T> {
  const response = await fetch(`${resolveApiBase()}${path}`, {
    ...options,
    headers: {
      "Content-Type": "application/json",
      ...(options?.headers ?? {})
    },
    cache: "no-store"
  });

  if (!response.ok) {
    throw new Error(await response.text());
  }

  return response.json() as Promise<T>;
}

export const api = {
  papers: () => request<Paper[]>("/papers"),
  memories: (status?: ReviewStatus) => request<Memory[]>(`/memories${status ? `?status=${status}` : ""}`),
  skills: (status?: ReviewStatus) => request<Skill[]>(`/skills${status ? `?status=${status}` : ""}`),
  createMemory: (payload: { user_id: string; memory_type: string; content: string }) =>
    request<Memory>("/memories", { method: "POST", body: JSON.stringify(payload) }),
  createSkill: (payload: { name: string; description: string; prompt_template: string }) =>
    request<Skill>("/skills", { method: "POST", body: JSON.stringify(payload) }),
  updateMemoryStatus: (memoryId: string, status: ReviewStatus) =>
    request<Memory>(`/memories/${memoryId}/status`, {
      method: "PATCH",
      body: JSON.stringify({ status })
    }),
  updateSkillStatus: (skillId: string, status: ReviewStatus) =>
    request<Skill>(`/skills/${skillId}/status`, {
      method: "PATCH",
      body: JSON.stringify({ status })
    }),
  askPaper: (paperId: string, question: string) =>
    request<AgentAnswer>(`/papers/${paperId}/chat`, {
      method: "POST",
      body: JSON.stringify({ question })
    }),
  analyzePaper: (paperId: string, type: "summary" | "method" | "experiments" | "novelty" | "limitations") =>
    request<{ task_id: string; answer: string }>(`/papers/${paperId}/${type}`, { method: "POST" }),
  agentTasks: (limit = 20) => request<AgentTask[]>(`/agent/tasks?limit=${limit}`),
  agentTask: (taskId: string) => request<AgentTask>(`/agent/tasks/${taskId}`),
  agentTrace: (taskId: string) => request<TraceStep[]>(`/agent/tasks/${taskId}/trace`),
  agentLearning: (taskId: string) => request<AgentTaskLearning>(`/agent/tasks/${taskId}/learning`),
  policySummary: () => request<PolicySummary>("/agent/policy/summary"),
  rewardSummary: () => request<RewardSummary>("/agent/rewards/summary"),
  replayPolicy: () => request<PolicyReplay>("/agent/policy/replay", { method: "POST" }),
  submitFeedback: (taskId: string, rating: -1 | 1, issueTags: string[] = [], comment = "") =>
    request<FeedbackSubmission>(`/agent/tasks/${taskId}/feedback`, {
      method: "POST",
      body: JSON.stringify({ user_id: "default", rating, issue_tags: issueTags, comment })
    })
};
