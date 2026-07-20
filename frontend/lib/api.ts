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
    request<{ task_id: string; answer: string }>(`/papers/${paperId}/chat`, {
      method: "POST",
      body: JSON.stringify({ question })
    }),
  analyzePaper: (paperId: string, type: "summary" | "method" | "experiments" | "novelty" | "limitations") =>
    request<{ task_id: string; answer: string }>(`/papers/${paperId}/${type}`, { method: "POST" }),
  agentTasks: (limit = 20) => request<AgentTask[]>(`/agent/tasks?limit=${limit}`),
  agentTask: (taskId: string) => request<AgentTask>(`/agent/tasks/${taskId}`),
  agentTrace: (taskId: string) => request<TraceStep[]>(`/agent/tasks/${taskId}/trace`),
  agentLearning: (taskId: string) => request<AgentTaskLearning>(`/agent/tasks/${taskId}/learning`)
};
