"use client";

import { useCallback, useEffect, useMemo, useState } from "react";
import { BrainCircuit, Check, History, ListChecks, RefreshCw, ShieldCheck, X } from "lucide-react";
import { Panel } from "@/components/Panel";
import { API_BASE, AgentTask, Memory, ReviewStatus, Skill, api } from "@/lib/api";

const statuses: ReviewStatus[] = ["draft", "active", "rejected", "archived"];

const statusLabels: Record<string, string> = {
  active: "已启用",
  allowed: "允许",
  applied: "已应用",
  archived: "已归档",
  blocked: "已阻止",
  candidate: "候选",
  completed: "已完成",
  draft: "待审核",
  failed: "失败",
  helpful: "有帮助",
  improved: "已改善",
  incomplete: "未完成",
  needs_review: "需审核",
  pending: "待处理",
  regressed: "已退化",
  rejected: "已拒绝",
  replayed: "已回放",
  review: "审核",
  review_recommended: "建议审核",
  running: "运行中",
  skipped: "已跳过",
  success: "成功",
  unchanged: "无变化",
  unknown: "未知",
  used: "已使用"
};

const targetTypeLabels: Record<string, string> = {
  memory: "记忆",
  skill: "技能",
  workflow: "工作流",
  plan: "计划"
};

const actionLabels: Record<string, string> = {
  before_apply: "应用前快照",
  content_update: "内容更新",
  draft_workflow_lesson: "生成工作流经验",
  manual_rollback: "手动回滚",
  review_memory: "审核记忆",
  review_patch: "审核修订",
  review_skill: "审核技能",
  review_workflow_lesson: "审核工作流经验",
  status_update: "状态更新",
  workflow_lesson_patch: "工作流经验修订"
};

const taskTypeLabels: Record<string, string> = {
  paper_question_answering: "论文问答",
  paper_summary: "论文总结",
  paper_method: "方法分析",
  paper_experiments: "实验分析",
  paper_novelty: "创新点分析",
  paper_limitations: "局限性分析",
  paper_ingestion: "论文入库"
};

const memoryTypeLabels: Record<string, string> = {
  research_preference: "研究偏好",
  workflow_lesson: "工作流经验"
};

type SkillOutcomeSummary = {
  skill_id: string;
  uses: number;
  helpful: number;
  needs_review: number;
  unknown: number;
  average_reflection_confidence: number;
};

type SkillReviewSignal = {
  skill_id: string;
  signal: string;
  reason: string;
  uses: number;
  helpful: number;
  needs_review: number;
};

type MemoryOutcomeSummary = {
  memory_id: string;
  uses: number;
  used: number;
  needs_review: number;
  unknown: number;
};

type MemoryReviewSignal = {
  memory_id: string;
  signal: string;
  reason: string;
  uses: number;
  used: number;
  needs_review: number;
};

type PlanOutcomeSummary = {
  task_type: string;
  uses: number;
  completed: number;
  incomplete: number;
  unknown: number;
  average_evidence_count: number;
};

type PlanReviewSignal = {
  task_type: string;
  signal: string;
  reason: string;
  uses: number;
  completed: number;
  incomplete: number;
};

type HermesEvaluation = {
  user_id: string | null;
  evaluation_suite?: string;
  task_count: number;
  completed_tasks: number;
  needs_review_tasks: number;
  completion_rate: number;
  plan_completion_rate: number;
  average_evidence_count: number;
  review_signal_counts: {
    skill: number;
    memory: number;
    workflow_lesson?: number;
    plan: number;
  };
  replay_summary?: ReplaySummary;
};

type EvaluationRun = {
  id: string;
  user_id: string;
  evaluation_suite?: string | null;
  trigger: string;
  summary: HermesEvaluation;
  created_at?: string | null;
};

type ReplayCase = {
  case_id?: string;
  source_task_id?: string;
  replay_task_id?: string;
  task_type?: string;
  replay_status?: string;
  task_status?: string;
  plan_status?: string;
  evidence_count?: number;
  reason?: string;
};

type ReplaySummary = {
  replayable_cases?: number;
  replayed_cases?: ReplayCase[];
  skipped_cases?: ReplayCase[];
};

type EvaluationDelta = {
  completion_rate?: number;
  plan_completion_rate?: number;
  average_evidence_count?: number;
  review_signals?: {
    skill?: number;
    memory?: number;
    workflow_lesson?: number;
    plan?: number;
  };
};

type EvaluationComparison = {
  baseline_run_id?: string;
  candidate_run_id?: string;
  aggregate_delta?: EvaluationDelta;
  case_deltas?: {
    case_id?: string;
    status?: string;
    baseline_plan_status?: string;
    candidate_plan_status?: string;
    baseline_evidence_count?: number;
    candidate_evidence_count?: number;
  }[];
};

type ImprovementSuggestion = {
  id: string;
  target_type: string;
  target_id: string;
  suggestion_type: string;
  status: string;
  reason: string;
  proposed_patch: Record<string, unknown>;
  evaluation_before?: Partial<HermesEvaluation>;
  evaluation_after?: Partial<HermesEvaluation>;
  evaluation_delta?: EvaluationDelta;
  baseline_evaluation_run_id?: string | null;
  candidate_evaluation_run_id?: string | null;
  evaluation_comparison?: EvaluationComparison;
  reviewed_by?: string | null;
  reviewed_at?: string | null;
};

type HermesRevision = {
  id: string;
  target_type: string;
  target_id: string;
  suggestion_id?: string | null;
  sequence: number;
  action: string;
  snapshot: Record<string, unknown>;
  policy_decision?: {
    status?: string;
    reason?: string;
  };
  created_at?: string | null;
};

type SkillEditDraft = {
  description: string;
  promptTemplate: string;
  triggerPatterns: string;
  steps: string;
};

type WorkflowLessonDraft = {
  content: string;
};

type ReviewHistoryEntry = {
  action?: string;
  reviewed_at?: string;
  reviewed_by?: string;
  from_status?: string;
  to_status?: string;
  changed_fields?: string[];
};

export default function LearningPage() {
  const [status, setStatus] = useState<ReviewStatus>("draft");
  const [memories, setMemories] = useState<Memory[]>([]);
  const [skills, setSkills] = useState<Skill[]>([]);
  const [tasks, setTasks] = useState<AgentTask[]>([]);
  const [selectedTaskId, setSelectedTaskId] = useState("");
  const [workflowLessons, setWorkflowLessons] = useState<Record<string, unknown>[]>([]);
  const [workflowLessonCandidates, setWorkflowLessonCandidates] = useState<Memory[]>([]);
  const [skillOutcomeSummary, setSkillOutcomeSummary] = useState<SkillOutcomeSummary[]>([]);
  const [skillReviewSignals, setSkillReviewSignals] = useState<SkillReviewSignal[]>([]);
  const [memoryOutcomeSummary, setMemoryOutcomeSummary] = useState<MemoryOutcomeSummary[]>([]);
  const [memoryReviewSignals, setMemoryReviewSignals] = useState<MemoryReviewSignal[]>([]);
  const [planOutcomeSummary, setPlanOutcomeSummary] = useState<PlanOutcomeSummary[]>([]);
  const [planReviewSignals, setPlanReviewSignals] = useState<PlanReviewSignal[]>([]);
  const [evaluation, setEvaluation] = useState<HermesEvaluation | null>(null);
  const [evaluationSuite, setEvaluationSuite] = useState("");
  const [baselineRun, setBaselineRun] = useState<EvaluationRun | null>(null);
  const [candidateRun, setCandidateRun] = useState<EvaluationRun | null>(null);
  const [manualComparison, setManualComparison] = useState<EvaluationComparison | null>(null);
  const [improvementSuggestions, setImprovementSuggestions] = useState<ImprovementSuggestion[]>([]);
  const [improvementRevisions, setImprovementRevisions] = useState<Record<string, HermesRevision[]>>({});
  const [applyingSuggestionKey, setApplyingSuggestionKey] = useState("");
  const [reviewingSuggestionKey, setReviewingSuggestionKey] = useState("");
  const [restoringRevisionId, setRestoringRevisionId] = useState("");
  const [runningEvaluationTrigger, setRunningEvaluationTrigger] = useState("");
  const [isComparingRuns, setIsComparingRuns] = useState(false);
  const [isLoading, setIsLoading] = useState(false);

  const refresh = useCallback(async (nextStatus: ReviewStatus = status) => {
    setIsLoading(true);
    try {
      const [nextMemories, nextSkills, nextTasks, nextEvaluation, nextSuggestions] = await Promise.all([
        api.memories(nextStatus),
        api.skills(nextStatus),
        api.agentTasks(10),
        loadEvaluation(evaluationSuite),
        loadImprovementSuggestions()
      ]);
      setMemories(nextMemories);
      setSkills(nextSkills);
      setTasks(nextTasks);
      setEvaluation(nextEvaluation);
      setImprovementSuggestions(nextSuggestions.suggestions ?? []);
      setImprovementRevisions(await loadImprovementRevisions(nextSuggestions.suggestions ?? []));
      setSelectedTaskId((current) => current || nextTasks[0]?.id || "");
    } finally {
      setIsLoading(false);
    }
  }, [evaluationSuite, status]);

  function changeStatus(nextStatus: ReviewStatus) {
    setStatus(nextStatus);
  }

  async function loadEvaluation(suite: string) {
    const query = suite.trim() ? `?suite=${encodeURIComponent(suite.trim())}` : "";
    const response = await fetch(`${API_BASE}/agent/evaluation${query}`);
    if (!response.ok) throw new Error(await response.text());
    return response.json() as Promise<HermesEvaluation>;
  }

  async function loadImprovementSuggestions() {
    const response = await fetch(`${API_BASE}/agent/improvement-suggestions`);
    if (!response.ok) throw new Error(await response.text());
    return response.json() as Promise<{ suggestions: ImprovementSuggestion[] }>;
  }

  async function loadImprovementRevisions(suggestions: ImprovementSuggestion[]) {
    const entries = await Promise.all(suggestions.map(async (suggestion) => {
      const query = new URLSearchParams({
        target_type: suggestion.target_type,
        target_id: suggestion.target_id
      });
      const response = await fetch(`${API_BASE}/agent/improvement-revisions?${query.toString()}`);
      if (!response.ok) throw new Error(await response.text());
      return [suggestionKey(suggestion), await response.json() as HermesRevision[]] as const;
    }));
    return Object.fromEntries(entries);
  }

  async function refreshEvaluation() {
    setEvaluation(await loadEvaluation(evaluationSuite));
  }

  async function createEvaluationRun(trigger: "baseline" | "candidate") {
    setRunningEvaluationTrigger(trigger);
    try {
      const response = await fetch(`${API_BASE}/agent/evaluation-runs`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          user_id: "default",
          suite: evaluationSuite.trim() || null,
          trigger
        })
      });
      if (!response.ok) throw new Error(await response.text());
      const run = await response.json() as EvaluationRun;
      if (trigger === "baseline") setBaselineRun(run);
      if (trigger === "candidate") setCandidateRun(run);
      setEvaluation(run.summary);
      setManualComparison(null);
    } finally {
      setRunningEvaluationTrigger("");
    }
  }

  async function compareEvaluationRuns() {
    if (!baselineRun || !candidateRun) return;
    setIsComparingRuns(true);
    try {
      const query = new URLSearchParams({
        baseline_run_id: baselineRun.id,
        candidate_run_id: candidateRun.id
      });
      const response = await fetch(`${API_BASE}/agent/evaluation-runs/compare?${query.toString()}`);
      if (!response.ok) throw new Error(await response.text());
      setManualComparison(await response.json() as EvaluationComparison);
    } finally {
      setIsComparingRuns(false);
    }
  }

  async function applyImprovementSuggestion(suggestion: ImprovementSuggestion) {
    const key = suggestionKey(suggestion);
    setApplyingSuggestionKey(key);
    try {
      const response = await fetch(`${API_BASE}/agent/improvement-suggestions/apply`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          user_id: "default",
          target_type: suggestion.target_type,
          target_id: suggestion.target_id,
          suggestion_type: suggestion.suggestion_type,
          proposed_patch: suggestion.proposed_patch,
          reviewed_by: "default"
        })
      });
      if (!response.ok) throw new Error(await response.text());
      const [nextEvaluation, nextSuggestions] = await Promise.all([
        loadEvaluation(evaluationSuite),
        loadImprovementSuggestions()
      ]);
      setEvaluation(nextEvaluation);
      setImprovementSuggestions(nextSuggestions.suggestions ?? []);
      setImprovementRevisions(await loadImprovementRevisions(nextSuggestions.suggestions ?? []));
      if (selectedTaskId) await loadTaskLearning(selectedTaskId);
    } finally {
      setApplyingSuggestionKey("");
    }
  }

  async function reviewImprovementSuggestion(suggestion: ImprovementSuggestion, nextStatus: "rejected" | "archived") {
    const key = `${suggestionKey(suggestion)}-${nextStatus}`;
    setReviewingSuggestionKey(key);
    try {
      const response = await fetch(`${API_BASE}/agent/improvement-suggestions/${suggestion.id}/review`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ status: nextStatus, reviewed_by: "default" })
      });
      if (!response.ok) throw new Error(await response.text());
      const nextSuggestions = await loadImprovementSuggestions();
      setImprovementSuggestions(nextSuggestions.suggestions ?? []);
      setImprovementRevisions(await loadImprovementRevisions(nextSuggestions.suggestions ?? []));
    } finally {
      setReviewingSuggestionKey("");
    }
  }

  async function restoreRevision(suggestion: ImprovementSuggestion, revision: HermesRevision) {
    setRestoringRevisionId(revision.id);
    try {
      const response = await fetch(`${API_BASE}/agent/improvement-revisions/${revision.id}/rollback`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ reviewed_by: "default" })
      });
      if (!response.ok) throw new Error(await response.text());
      await refresh(status);
    } finally {
      setRestoringRevisionId("");
    }
  }

  async function updateMemory(memoryId: string, nextStatus: ReviewStatus) {
    await api.updateMemoryStatus(memoryId, nextStatus);
    await refresh();
  }

  async function updateSkill(skillId: string, nextStatus: ReviewStatus) {
    await api.updateSkillStatus(skillId, nextStatus);
    await refresh();
  }

  async function updateSkillDetails(skill: Skill, draft: SkillEditDraft) {
    const response = await fetch(`${API_BASE}/skills/${skill.id}`, {
      method: "PATCH",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        description: draft.description,
        prompt_template: draft.promptTemplate,
        metadata: {
          ...skill.metadata_json,
          trigger_patterns: parseList(draft.triggerPatterns),
          steps: parseList(draft.steps)
        }
      })
    });
    if (!response.ok) throw new Error(await response.text());
    await refresh();
  }

  async function updateWorkflowLessonStatus(memoryId: string, nextStatus: ReviewStatus) {
    await api.updateMemoryStatus(memoryId, nextStatus);
    await loadTaskLearning(selectedTaskId);
  }

  async function updateWorkflowLessonDetails(memory: Memory, draft: WorkflowLessonDraft) {
    const response = await fetch(`${API_BASE}/memories/${memory.id}`, {
      method: "PATCH",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        content: draft.content,
        metadata: memory.metadata_json
      })
    });
    if (!response.ok) throw new Error(await response.text());
    await loadTaskLearning(selectedTaskId);
  }

  async function loadTaskLearning(taskId: string) {
    if (!taskId) return;
    setSelectedTaskId(taskId);
    try {
      const learning = await api.agentLearning(taskId) as Awaited<ReturnType<typeof api.agentLearning>> & {
        skill_outcome_summary?: SkillOutcomeSummary[];
        skill_review_signals?: SkillReviewSignal[];
        memory_outcome_summary?: MemoryOutcomeSummary[];
        memory_review_signals?: MemoryReviewSignal[];
        plan_outcome_summary?: PlanOutcomeSummary[];
        plan_review_signals?: PlanReviewSignal[];
        workflow_lesson_candidates?: Memory[];
      };
      setWorkflowLessons(learning.workflow_lessons);
      setWorkflowLessonCandidates(learning.workflow_lesson_candidates ?? []);
      setSkillOutcomeSummary(learning.skill_outcome_summary ?? []);
      setSkillReviewSignals(learning.skill_review_signals ?? []);
      setMemoryOutcomeSummary(learning.memory_outcome_summary ?? []);
      setMemoryReviewSignals(learning.memory_review_signals ?? []);
      setPlanOutcomeSummary(learning.plan_outcome_summary ?? []);
      setPlanReviewSignals(learning.plan_review_signals ?? []);
    } catch {
      setWorkflowLessons([]);
      setWorkflowLessonCandidates([]);
      setSkillOutcomeSummary([]);
      setSkillReviewSignals([]);
      setMemoryOutcomeSummary([]);
      setMemoryReviewSignals([]);
      setPlanOutcomeSummary([]);
      setPlanReviewSignals([]);
    }
  }

  useEffect(() => {
    refresh();
  }, [refresh]);

  const totalCandidates = memories.length + skills.length;
  const selectedTask = useMemo(
    () => tasks.find((task) => task.id === selectedTaskId),
    [selectedTaskId, tasks]
  );

  return (
    <div className="space-y-6">
      <PageHeader
        title="学习审核"
        description="审核系统沉淀的记忆、技能和工作流经验。只有已启用的条目会进入后续智能体提示词。"
        icon={<ListChecks />}
        action={
          <button onClick={() => refresh()} className="inline-flex items-center gap-2 rounded-md bg-moss px-4 py-2 text-sm font-semibold text-white">
            <RefreshCw className="h-4 w-4" />
            刷新
          </button>
        }
      />

      <div className="grid gap-4 md:grid-cols-4">
        <StatCard label="当前状态" value={displayLabel(status)} icon={<ShieldCheck />} tone="moss" />
        <StatCard label="记忆候选" value={memories.length} icon={<BrainCircuit />} tone="blue" />
        <StatCard label="技能候选" value={skills.length} icon={<ListChecks />} tone="rust" />
        <StatCard label="候选总数" value={totalCandidates} icon={<Check />} tone="slate" />
      </div>

      <Panel title="系统评估">
        <div className="mb-4 flex flex-col gap-2 md:flex-row md:items-end">
          <Field label="评估套件" value={evaluationSuite} onChange={setEvaluationSuite} />
          <button onClick={refreshEvaluation} className="inline-flex items-center justify-center gap-2 rounded-md bg-moss px-4 py-2 text-sm font-semibold text-white">
            <RefreshCw className="h-4 w-4" />
            加载
          </button>
          <button
            onClick={() => createEvaluationRun("baseline")}
            disabled={Boolean(runningEvaluationTrigger)}
            className="inline-flex items-center justify-center gap-2 rounded-md border border-slate-200 bg-white px-4 py-2 text-sm font-semibold text-slate-700 hover:border-moss/50 disabled:cursor-not-allowed disabled:bg-slate-100 disabled:text-slate-400"
          >
            <History className="h-4 w-4" />
            {runningEvaluationTrigger === "baseline" ? "运行中" : "运行基线"}
          </button>
          <button
            onClick={() => createEvaluationRun("candidate")}
            disabled={Boolean(runningEvaluationTrigger)}
            className="inline-flex items-center justify-center gap-2 rounded-md border border-slate-200 bg-white px-4 py-2 text-sm font-semibold text-slate-700 hover:border-moss/50 disabled:cursor-not-allowed disabled:bg-slate-100 disabled:text-slate-400"
          >
            <ShieldCheck className="h-4 w-4" />
            {runningEvaluationTrigger === "candidate" ? "运行中" : "运行候选"}
          </button>
          <button
            onClick={compareEvaluationRuns}
            disabled={!baselineRun || !candidateRun || isComparingRuns}
            className="inline-flex items-center justify-center gap-2 rounded-md bg-ink px-4 py-2 text-sm font-semibold text-white disabled:cursor-not-allowed disabled:bg-slate-300"
          >
            <ListChecks className="h-4 w-4" />
            {isComparingRuns ? "对比中" : "对比评估"}
          </button>
        </div>
        {evaluation === null ? (
          <LoadingBox />
        ) : (
          <>
            <div className="mb-3 text-sm text-slate-500">{evaluation.evaluation_suite ? `套件 ${evaluation.evaluation_suite}` : "全部已记录任务"}</div>
            <div className="grid gap-3 md:grid-cols-3 xl:grid-cols-6">
              <Metric label="任务数" value={evaluation.task_count} />
              <Metric label="已完成" value={evaluation.completed_tasks} />
              <Metric label="需审核" value={evaluation.needs_review_tasks} />
              <Metric label="完成率" value={formatRate(evaluation.completion_rate)} />
              <Metric label="计划完成率" value={formatRate(evaluation.plan_completion_rate)} />
              <Metric label="平均证据" value={evaluation.average_evidence_count.toFixed(3)} />
              <Metric label="技能信号" value={evaluation.review_signal_counts.skill} />
              <Metric label="记忆信号" value={evaluation.review_signal_counts.memory} />
              <Metric label="经验信号" value={evaluation.review_signal_counts.workflow_lesson ?? 0} />
              <Metric label="计划信号" value={evaluation.review_signal_counts.plan} />
            </div>
            <div className="mt-3 grid gap-2 text-xs text-slate-600 md:grid-cols-2">
              <Metric label="基线运行" value={shortId(baselineRun?.id)} />
              <Metric label="候选运行" value={shortId(candidateRun?.id)} />
            </div>
            <EvaluationComparisonPanel
              comparison={manualComparison}
              baselineReplay={baselineRun?.summary.replay_summary}
              candidateReplay={candidateRun?.summary.replay_summary}
            />
          </>
        )}
      </Panel>

      <Panel title="改进建议">
        {improvementSuggestions.length === 0 ? (
          <div className="text-sm text-slate-500">当前没有需要审核的改进建议。</div>
        ) : (
          <div className="space-y-3">
            {improvementSuggestions.map((suggestion) => (
              <div key={suggestion.id || suggestionKey(suggestion)} className="rounded-md border border-amber-200 bg-amber-50 p-3 text-sm">
                <div className="flex flex-wrap items-center gap-2">
                  <StatusPill label={suggestion.status} tone="amber" />
                  <span className="font-semibold text-ink">{displayLabel(suggestion.target_type)}</span>
                  <span className="text-slate-600">{suggestion.target_id}</span>
                </div>
                <p className="mt-2 text-sm leading-6 text-slate-700">{formatReason(suggestion.reason)}</p>
                {suggestion.reviewed_by ? (
                  <div className="mt-2 text-xs text-slate-500">
                    审核人 {suggestion.reviewed_by}{suggestion.reviewed_at ? `，时间 ${new Date(suggestion.reviewed_at).toLocaleString()}` : ""}
                  </div>
                ) : null}
                <LocalizedRecord data={suggestion.proposed_patch} />
                <SuggestionImpact suggestion={suggestion} />
                <SuggestionRevisions
                  revisions={improvementRevisions[suggestionKey(suggestion)] ?? []}
                  restoringRevisionId={restoringRevisionId}
                  onRestore={(revision) => restoreRevision(suggestion, revision)}
                />
                {suggestion.status === "draft" ? (
                  <div className="mt-3 flex flex-wrap gap-2">
                    <ActionButton
                      label={applyingSuggestionKey === suggestionKey(suggestion) ? "应用中" : "应用"}
                      icon={<Check className="h-4 w-4" />}
                      onClick={() => applyImprovementSuggestion(suggestion)}
                    />
                    <ActionButton
                      label={reviewingSuggestionKey === `${suggestionKey(suggestion)}-rejected` ? "拒绝中" : "拒绝"}
                      icon={<X className="h-4 w-4" />}
                      onClick={() => reviewImprovementSuggestion(suggestion, "rejected")}
                    />
                    <ActionButton
                      label={reviewingSuggestionKey === `${suggestionKey(suggestion)}-archived` ? "归档中" : "归档"}
                      icon={<History className="h-4 w-4" />}
                      onClick={() => reviewImprovementSuggestion(suggestion, "archived")}
                    />
                  </div>
                ) : null}
              </div>
            ))}
          </div>
        )}
      </Panel>

      <div className="flex flex-wrap gap-2">
        {statuses.map((item) => (
          <button
            key={item}
            onClick={() => changeStatus(item)}
            className={`rounded-md border px-3 py-2 text-sm font-semibold ${
              item === status ? "border-moss bg-moss text-white" : "border-slate-200 bg-white text-slate-700 hover:border-moss/50"
            }`}
          >
            {displayLabel(item)}
          </button>
        ))}
      </div>

      <div className="grid gap-6 xl:grid-cols-2">
        <Panel title="记忆候选">
          {isLoading ? (
            <LoadingBox />
          ) : memories.length === 0 ? (
            <EmptyState title="暂无记忆候选" description="当前状态下没有匹配的记忆候选。" icon={<BrainCircuit />} />
          ) : (
            <div className="space-y-3">
              {memories.map((memory) => (
                <CandidateCard
                  key={memory.id}
                  title={formatMemoryType(memory.memory_type)}
                  body={memory.content}
                  metadata={memory.metadata_json}
                  onApprove={() => updateMemory(memory.id, "active")}
                  onReject={() => updateMemory(memory.id, "rejected")}
                  onArchive={() => updateMemory(memory.id, "archived")}
                  footer={<ReviewHistory metadata={memory.metadata_json} />}
                />
              ))}
            </div>
          )}
        </Panel>

        <Panel title="技能候选">
          {isLoading ? (
            <LoadingBox />
          ) : skills.length === 0 ? (
            <EmptyState title="暂无技能候选" description="当前状态下没有匹配的技能候选。" icon={<ListChecks />} />
          ) : (
            <div className="space-y-3">
              {skills.map((skill) => (
                <SkillCandidateCard
                  key={skill.id}
                  skill={skill}
                  onApprove={() => updateSkill(skill.id, "active")}
                  onReject={() => updateSkill(skill.id, "rejected")}
                  onArchive={() => updateSkill(skill.id, "archived")}
                  onSave={(draft) => updateSkillDetails(skill, draft)}
                />
              ))}
            </div>
          )}
        </Panel>
      </div>

      <Panel title="学习追踪">
        <div className="grid gap-4 lg:grid-cols-[0.85fr_1.15fr]">
          <div className="space-y-2">
            {tasks.length === 0 ? (
              <EmptyState title="暂无最近任务" description="运行一次 Agent 任务后，可以在这里查看提取出的经验。" icon={<History />} />
            ) : (
              tasks.map((task) => (
                <button
                  key={task.id}
                  onClick={() => loadTaskLearning(task.id)}
                  className={`w-full rounded-md border p-3 text-left text-sm ${
                    task.id === selectedTaskId ? "border-moss bg-moss/5" : "border-slate-200 bg-slate-50 hover:bg-white"
                  }`}
                >
                  <div className="font-semibold text-ink">{formatTaskType(task.task_type)}</div>
                  <div className="mt-1 line-clamp-1 text-slate-600">{task.input_text || "无输入"}</div>
                </button>
              ))
            )}
          </div>
          <div className="space-y-4 rounded-md border border-slate-200 bg-slate-50 p-4">
            <div className="mb-3 flex items-center justify-between gap-3">
              <div className="text-sm font-semibold text-ink">{selectedTask ? formatTaskType(selectedTask.task_type) : "选择一个任务"}</div>
              {selectedTask ? <StatusPill label={selectedTask.status} /> : null}
            </div>
            <div>
              <div className="mb-3 text-sm font-semibold text-ink">工作流经验候选</div>
              {workflowLessonCandidates.length === 0 ? (
                <div className="text-sm text-slate-500">暂无已加载的工作流经验候选。</div>
              ) : (
                <div className="space-y-3">
                  {workflowLessonCandidates.map((memory) => (
                    <WorkflowLessonCandidateCard
                      key={memory.id}
                      memory={memory}
                      onApprove={() => updateWorkflowLessonStatus(memory.id, "active")}
                      onReject={() => updateWorkflowLessonStatus(memory.id, "rejected")}
                      onArchive={() => updateWorkflowLessonStatus(memory.id, "archived")}
                      onSave={(draft) => updateWorkflowLessonDetails(memory, draft)}
                    />
                  ))}
                </div>
              )}
            </div>
            <div>
              <div className="mb-3 text-sm font-semibold text-ink">已提取的工作流经验</div>
            {workflowLessons.length === 0 ? (
              <div className="text-sm text-slate-500">暂无已加载的工作流经验。</div>
            ) : (
              <LocalizedRecordList items={workflowLessons} />
            )}
            </div>
          </div>
        </div>
      </Panel>

      <Panel title="工作流治理">
        <div className="grid gap-4 lg:grid-cols-2">
          <div className="rounded-md border border-slate-200 bg-slate-50 p-4">
            <div className="mb-3 text-sm font-semibold text-ink">结果汇总</div>
            {planOutcomeSummary.length === 0 ? (
              <div className="text-sm text-slate-500">暂无已加载的工作流结果汇总。</div>
            ) : (
              <div className="space-y-3">
                {planOutcomeSummary.map((item) => (
                  <div key={item.task_type} className="rounded-md border border-slate-200 bg-white p-3 text-sm">
                    <div className="font-semibold text-ink">{formatTaskType(item.task_type)}</div>
                    <div className="mt-2 grid grid-cols-2 gap-2 text-xs text-slate-600 sm:grid-cols-5">
                      <Metric label="使用次数" value={item.uses} />
                      <Metric label="已完成" value={item.completed} />
                      <Metric label="未完成" value={item.incomplete} />
                      <Metric label="未知" value={item.unknown} />
                      <Metric label="平均证据" value={item.average_evidence_count.toFixed(3)} />
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>

          <div className="rounded-md border border-slate-200 bg-slate-50 p-4">
            <div className="mb-3 text-sm font-semibold text-ink">审核信号</div>
            {planReviewSignals.length === 0 ? (
              <div className="text-sm text-slate-500">当前任务所有者没有工作流审核信号。</div>
            ) : (
              <div className="space-y-3">
                {planReviewSignals.map((signal) => (
                  <div key={`${signal.task_type}-${signal.signal}`} className="rounded-md border border-amber-200 bg-amber-50 p-3 text-sm">
                    <div className="flex flex-wrap items-center gap-2">
                      <StatusPill label={signal.signal} tone="amber" />
                      <span className="font-semibold text-ink">{formatTaskType(signal.task_type)}</span>
                    </div>
                    <p className="mt-2 text-sm leading-6 text-slate-700">{formatReason(signal.reason)}</p>
                    <div className="mt-3 flex flex-wrap gap-2 text-xs text-slate-600">
                      <span>{signal.uses} 次使用</span>
                      <span>{signal.completed} 次完成</span>
                      <span>{signal.incomplete} 次未完成</span>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>
      </Panel>

      <Panel title="技能治理">
        <div className="grid gap-4 lg:grid-cols-2">
          <div className="rounded-md border border-slate-200 bg-slate-50 p-4">
            <div className="mb-3 text-sm font-semibold text-ink">结果汇总</div>
            {skillOutcomeSummary.length === 0 ? (
              <div className="text-sm text-slate-500">暂无已加载的技能结果汇总。</div>
            ) : (
              <div className="space-y-3">
                {skillOutcomeSummary.map((item) => (
                  <div key={item.skill_id} className="rounded-md border border-slate-200 bg-white p-3 text-sm">
                    <div className="font-semibold text-ink">{item.skill_id}</div>
                    <div className="mt-2 grid grid-cols-2 gap-2 text-xs text-slate-600 sm:grid-cols-5">
                      <Metric label="使用次数" value={item.uses} />
                      <Metric label="有帮助" value={item.helpful} />
                      <Metric label="需审核" value={item.needs_review} />
                      <Metric label="未知" value={item.unknown} />
                      <Metric label="置信度" value={item.average_reflection_confidence.toFixed(3)} />
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>

          <div className="rounded-md border border-slate-200 bg-slate-50 p-4">
            <div className="mb-3 text-sm font-semibold text-ink">审核信号</div>
            {skillReviewSignals.length === 0 ? (
              <div className="text-sm text-slate-500">当前任务所有者没有技能审核信号。</div>
            ) : (
              <div className="space-y-3">
                {skillReviewSignals.map((signal) => (
                  <div key={`${signal.skill_id}-${signal.signal}`} className="rounded-md border border-amber-200 bg-amber-50 p-3 text-sm">
                    <div className="flex flex-wrap items-center gap-2">
                      <StatusPill label={signal.signal} tone="amber" />
                      <span className="font-semibold text-ink">{signal.skill_id}</span>
                    </div>
                    <p className="mt-2 text-sm leading-6 text-slate-700">{formatReason(signal.reason)}</p>
                    <div className="mt-3 flex flex-wrap gap-2 text-xs text-slate-600">
                      <span>{signal.uses} 次使用</span>
                      <span>{signal.helpful} 次有帮助</span>
                      <span>{signal.needs_review} 次需审核</span>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>
      </Panel>

      <Panel title="记忆治理">
        <div className="grid gap-4 lg:grid-cols-2">
          <div className="rounded-md border border-slate-200 bg-slate-50 p-4">
            <div className="mb-3 text-sm font-semibold text-ink">结果汇总</div>
            {memoryOutcomeSummary.length === 0 ? (
              <div className="text-sm text-slate-500">暂无已加载的记忆结果汇总。</div>
            ) : (
              <div className="space-y-3">
                {memoryOutcomeSummary.map((item) => (
                  <div key={item.memory_id} className="rounded-md border border-slate-200 bg-white p-3 text-sm">
                    <div className="font-semibold text-ink">{item.memory_id}</div>
                    <div className="mt-2 grid grid-cols-2 gap-2 text-xs text-slate-600 sm:grid-cols-4">
                      <Metric label="使用次数" value={item.uses} />
                      <Metric label="已使用" value={item.used} />
                      <Metric label="需审核" value={item.needs_review} />
                      <Metric label="未知" value={item.unknown} />
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>

          <div className="rounded-md border border-slate-200 bg-slate-50 p-4">
            <div className="mb-3 text-sm font-semibold text-ink">审核信号</div>
            {memoryReviewSignals.length === 0 ? (
              <div className="text-sm text-slate-500">当前任务所有者没有记忆审核信号。</div>
            ) : (
              <div className="space-y-3">
                {memoryReviewSignals.map((signal) => (
                  <div key={`${signal.memory_id}-${signal.signal}`} className="rounded-md border border-amber-200 bg-amber-50 p-3 text-sm">
                    <div className="flex flex-wrap items-center gap-2">
                      <StatusPill label={signal.signal} tone="amber" />
                      <span className="font-semibold text-ink">{signal.memory_id}</span>
                    </div>
                    <p className="mt-2 text-sm leading-6 text-slate-700">{formatReason(signal.reason)}</p>
                    <div className="mt-3 flex flex-wrap gap-2 text-xs text-slate-600">
                      <span>{signal.uses} 次使用</span>
                      <span>{signal.used} 次已使用</span>
                      <span>{signal.needs_review} 次需审核</span>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>
      </Panel>
    </div>
  );
}

function Metric({ label, value }: { label: string; value: string | number }) {
  return (
    <div className="rounded-md bg-slate-50 px-2 py-1">
      <div className="font-semibold text-ink">{value}</div>
      <div className="mt-0.5 text-[11px] uppercase tracking-normal text-slate-500">{label}</div>
    </div>
  );
}

function formatRate(value: number) {
  return `${Math.round(value * 100)}%`;
}

function formatDelta(value?: number, mode: "rate" | "number" = "number") {
  if (typeof value !== "number") return "-";
  const sign = value > 0 ? "+" : "";
  if (mode === "rate") return `${sign}${Math.round(value * 100)}%`;
  return `${sign}${value.toFixed(3)}`;
}

function displayLabel(value?: string | null) {
  const key = String(value ?? "unknown");
  return statusLabels[key] ?? targetTypeLabels[key] ?? actionLabels[key] ?? taskTypeLabels[key] ?? memoryTypeLabels[key] ?? key;
}

function formatTaskType(value?: string | null) {
  if (!value) return "未选择任务";
  return taskTypeLabels[value] ?? value;
}

function formatMemoryType(value: string) {
  return memoryTypeLabels[value] ?? value;
}

function formatReason(reason?: string | null) {
  if (!reason) return "";
  const text = String(reason);
  const needsHelpful = text.match(/^needs_review outcomes exceed helpful outcomes after (\d+) uses$/);
  if (needsHelpful) return `需审核结果超过有帮助结果，累计 ${needsHelpful[1]} 次使用后建议复核。`;
  const needsUsed = text.match(/^needs_review outcomes exceed used outcomes after (\d+) uses$/);
  if (needsUsed) return `需审核结果超过已使用结果，累计 ${needsUsed[1]} 次使用后建议复核。`;
  const needsApplied = text.match(/^needs_review outcomes exceed applied outcomes after (\d+) uses$/);
  if (needsApplied) return `需审核结果超过已应用结果，累计 ${needsApplied[1]} 次使用后建议复核。`;
  const incompletePlans = text.match(/^incomplete plan outcomes exceed completed outcomes after (\d+) uses$/);
  if (incompletePlans) return `未完成计划多于已完成计划，累计 ${incompletePlans[1]} 次使用后建议复核。`;
  const regressedCase = text.match(/^candidate evaluation regressed case (.+)$/);
  if (regressedCase) return `候选评估用例 ${regressedCase[1]} 出现退化。`;
  const regressedKey = text.match(/^candidate evaluation regressed (.+)$/);
  if (regressedKey) return `候选评估指标 ${formatMetricKey(regressedKey[1])} 出现退化。`;
  if (text === "candidate evaluation increased workflow_lesson review signals") return "候选评估增加了工作流经验审核信号。";
  if (text === "candidate evaluation did not regress") return "候选评估未出现退化。";
  if (text === "already in evaluation suite") return "已在评估套件中。";
  if (text === "plan status incomplete") return "计划状态未完成。";
  if (text === "notification webhook url not configured") return "未配置通知回调地址。";
  const rolledBackBy = text.match(/^rolled back by (.+)$/);
  if (rolledBackBy) return `由 ${rolledBackBy[1]} 回滚。`;
  return text;
}

function formatMetricKey(key: string) {
  const metricLabels: Record<string, string> = {
    average_evidence_count: "平均证据数",
    completion_rate: "完成率",
    plan_completion_rate: "计划完成率",
    review_signals: "审核信号"
  };
  return metricLabels[key] ?? key;
}

function formatRecordKey(key: string) {
  const labels: Record<string, string> = {
    action: "动作",
    confidence: "置信度",
    content: "内容",
    created_memory: "已创建记忆",
    description: "描述",
    evaluation_case_reason: "评估用例原因",
    evidence_count: "证据数",
    id: "编号",
    lesson: "经验",
    lesson_id: "经验编号",
    memory_id: "记忆编号",
    metadata_json: "元数据",
    name: "名称",
    plan_status: "计划状态",
    prompt_template: "提示词模板",
    reason: "原因",
    recommendation: "建议",
    reviewed_at: "审核时间",
    reviewed_by: "审核人",
    skill_id: "技能编号",
    source: "来源",
    source_task_id: "来源任务",
    status: "状态",
    steps: "执行步骤",
    suggestion_type: "建议类型",
    target_id: "目标编号",
    task_status: "任务状态",
    task_type: "任务类型",
    trigger_patterns: "触发模式",
    updated_memory: "已更新记忆",
    workflow_lessons: "工作流经验"
  };
  return labels[key] ?? key;
}

function formatRecordValue(value: unknown): React.ReactNode {
  if (value === null || value === undefined || value === "") return "-";
  if (typeof value === "number" || typeof value === "boolean") return String(value);
  if (typeof value === "string") {
    const recommendationLabels: Record<string, string> = {
      "revise or archive this memory before future recall": "在后续召回前修订或归档这条记忆",
      "revise or archive this workflow lesson before future planning": "在后续规划前修订或归档这条工作流经验",
      "tighten trigger patterns or revise execution steps": "收紧触发模式或修订执行步骤"
    };
    const workflowLesson = value.match(/^Review (.+) workflow: incomplete plans exceeded completed plans after (\d+) uses\.$/);
    if (workflowLesson) return `复核${formatTaskType(workflowLesson[1])}工作流：累计 ${workflowLesson[2]} 次使用后，未完成计划多于已完成计划。`;
    if (recommendationLabels[value]) return recommendationLabels[value];
    const reason = formatReason(value);
    if (reason !== value) return reason;
    return displayLabel(value);
  }
  if (Array.isArray(value)) {
    if (value.length === 0) return "无";
    return value.map((item) => typeof item === "object" ? JSON.stringify(item) : String(formatRecordValue(item))).join("，");
  }
  if (typeof value === "object") {
    return (
      <div className="mt-1 rounded-md border border-slate-200 bg-slate-50 p-2">
        <LocalizedRecordRows data={value as Record<string, unknown>} />
      </div>
    );
  }
  return String(value);
}

function LocalizedRecordRows({ data }: { data: Record<string, unknown> }) {
  const entries = Object.entries(data);
  if (entries.length === 0) return <div className="text-xs text-slate-500">无内容</div>;
  return (
    <div className="space-y-1">
      {entries.map(([key, value]) => (
        <div key={key} className="grid gap-1 text-xs text-slate-700 sm:grid-cols-[7rem_1fr]">
          <span className="font-semibold text-slate-500">{formatRecordKey(key)}</span>
          <span className="break-words">{formatRecordValue(value)}</span>
        </div>
      ))}
    </div>
  );
}

function LocalizedRecord({ data }: { data: Record<string, unknown> }) {
  return (
    <div className="mt-3 rounded-md bg-white p-3">
      <LocalizedRecordRows data={data} />
    </div>
  );
}

function LocalizedRecordList({ items }: { items: Record<string, unknown>[] }) {
  return (
    <div className="max-h-80 space-y-2 overflow-auto text-xs leading-5 text-slate-700">
      {items.map((item, index) => (
        <div key={index} className="rounded-md border border-slate-200 bg-white p-3">
          <LocalizedRecordRows data={item} />
        </div>
      ))}
    </div>
  );
}

function hasImpact(suggestion: ImprovementSuggestion) {
  return Boolean(
    suggestion.evaluation_delta && Object.keys(suggestion.evaluation_delta).length > 0
    || suggestion.evaluation_before && Object.keys(suggestion.evaluation_before).length > 0
    || suggestion.evaluation_after && Object.keys(suggestion.evaluation_after).length > 0
    || suggestion.baseline_evaluation_run_id
    || suggestion.candidate_evaluation_run_id
    || suggestion.evaluation_comparison && Object.keys(suggestion.evaluation_comparison).length > 0
  );
}

function EvaluationComparisonPanel({
  comparison,
  baselineReplay,
  candidateReplay
}: {
  comparison?: EvaluationComparison | null;
  baselineReplay?: ReplaySummary;
  candidateReplay?: ReplaySummary;
}) {
  const aggregateDelta = comparison?.aggregate_delta;
  const aggregateSignals = aggregateDelta?.review_signals ?? {};
  const caseDeltas = comparison?.case_deltas ?? [];
  if (!comparison && !baselineReplay && !candidateReplay) return null;

  return (
    <div className="mt-4 rounded-md border border-slate-200 bg-white p-3">
      <div className="mb-2 text-xs font-semibold uppercase tracking-normal text-slate-500">运行对比</div>
      {aggregateDelta ? (
        <div className="grid gap-2 text-xs text-slate-600 sm:grid-cols-4">
          <Metric label="完成率" value={formatDelta(aggregateDelta.completion_rate, "rate")} />
          <Metric label="计划" value={formatDelta(aggregateDelta.plan_completion_rate, "rate")} />
          <Metric label="证据" value={formatDelta(aggregateDelta.average_evidence_count)} />
          <Metric label="信号" value={`技能 ${aggregateSignals.skill ?? 0} / 记忆 ${aggregateSignals.memory ?? 0} / 经验 ${aggregateSignals.workflow_lesson ?? 0} / 计划 ${aggregateSignals.plan ?? 0}`} />
        </div>
      ) : (
        <div className="text-xs text-slate-500">先运行基线和候选评估，再进行对比查看整体变化。</div>
      )}
      {caseDeltas.length > 0 ? (
        <div className="mt-3 space-y-2">
          {caseDeltas.slice(0, 5).map((item, index) => (
            <div key={`${item.case_id ?? "case"}-${index}`} className="rounded-md border border-slate-200 bg-slate-50 px-3 py-2 text-xs text-slate-600">
              <div className="flex flex-wrap items-center gap-2">
                <StatusPill label={String(item.status ?? "unchanged")} tone={comparisonTone(item.status)} />
                <span className="font-semibold text-ink">{item.case_id ?? "用例"}</span>
              </div>
              <div className="mt-1">
                {displayLabel(item.baseline_plan_status)} -&gt; {displayLabel(item.candidate_plan_status)}；证据 {item.baseline_evidence_count ?? 0} -&gt; {item.candidate_evidence_count ?? 0}
              </div>
            </div>
          ))}
          {caseDeltas.length > 5 ? <div className="text-xs text-slate-500">另有 {caseDeltas.length - 5} 条用例变化</div> : null}
        </div>
      ) : null}
      {baselineReplay || candidateReplay ? (
        <div className="mt-3">
          <div className="mb-2 text-xs font-semibold uppercase tracking-normal text-slate-500">回放审计</div>
          <div className="grid gap-3 lg:grid-cols-2">
            <ReplaySummaryPanel label="基线" summary={baselineReplay} />
            <ReplaySummaryPanel label="候选" summary={candidateReplay} />
          </div>
        </div>
      ) : null}
    </div>
  );
}

function SuggestionImpact({ suggestion }: { suggestion: ImprovementSuggestion }) {
  if (!hasImpact(suggestion)) return null;
  const before = suggestion.evaluation_before ?? {};
  const after = suggestion.evaluation_after ?? {};
  const delta = suggestion.evaluation_delta ?? {};
  const signals = delta.review_signals ?? {};
  const comparison = suggestion.evaluation_comparison;
  const aggregateDelta = comparison?.aggregate_delta;
  const aggregateSignals = aggregateDelta?.review_signals ?? {};
  const caseDeltas = comparison?.case_deltas ?? [];
  const baselineReplay = before.replay_summary;
  const candidateReplay = after.replay_summary;

  return (
    <div className="mt-3 rounded-md border border-slate-200 bg-white p-3">
      <div className="mb-2 text-xs font-semibold uppercase tracking-normal text-slate-500">评估影响</div>
      <div className="grid gap-2 text-xs text-slate-600 sm:grid-cols-3">
        <Metric label="完成率变化" value={formatDelta(delta.completion_rate, "rate")} />
        <Metric label="计划变化" value={formatDelta(delta.plan_completion_rate, "rate")} />
        <Metric label="证据变化" value={formatDelta(delta.average_evidence_count)} />
        <Metric label="应用前任务" value={before.task_count ?? "-"} />
        <Metric label="应用后任务" value={after.task_count ?? "-"} />
        <Metric label="信号变化" value={`技能 ${signals.skill ?? 0} / 记忆 ${signals.memory ?? 0} / 计划 ${signals.plan ?? 0}`} />
      </div>
      {suggestion.baseline_evaluation_run_id || suggestion.candidate_evaluation_run_id ? (
        <div className="mt-3 grid gap-2 text-xs text-slate-600 md:grid-cols-2">
          <Metric label="基线运行" value={shortId(suggestion.baseline_evaluation_run_id)} />
          <Metric label="候选运行" value={shortId(suggestion.candidate_evaluation_run_id)} />
        </div>
      ) : null}
      {aggregateDelta ? (
        <div className="mt-3 grid gap-2 text-xs text-slate-600 sm:grid-cols-4">
          <Metric label="运行完成率" value={formatDelta(aggregateDelta.completion_rate, "rate")} />
          <Metric label="运行计划" value={formatDelta(aggregateDelta.plan_completion_rate, "rate")} />
          <Metric label="运行证据" value={formatDelta(aggregateDelta.average_evidence_count)} />
          <Metric label="运行信号" value={`技能 ${aggregateSignals.skill ?? 0} / 记忆 ${aggregateSignals.memory ?? 0} / 计划 ${aggregateSignals.plan ?? 0}`} />
        </div>
      ) : null}
      {caseDeltas.length > 0 ? (
        <div className="mt-3 space-y-2">
          {caseDeltas.slice(0, 3).map((item, index) => (
            <div key={`${item.case_id ?? "case"}-${index}`} className="rounded-md border border-slate-200 bg-slate-50 px-3 py-2 text-xs text-slate-600">
              <div className="flex flex-wrap items-center gap-2">
                <StatusPill label={String(item.status ?? "unchanged")} tone={comparisonTone(item.status)} />
                <span className="font-semibold text-ink">{item.case_id ?? "用例"}</span>
              </div>
              <div className="mt-1">
                {displayLabel(item.baseline_plan_status)} -&gt; {displayLabel(item.candidate_plan_status)}；证据 {item.baseline_evidence_count ?? 0} -&gt; {item.candidate_evidence_count ?? 0}
              </div>
            </div>
          ))}
        </div>
      ) : null}
      {baselineReplay || candidateReplay ? (
        <div className="mt-3">
          <div className="mb-2 text-xs font-semibold uppercase tracking-normal text-slate-500">回放审计</div>
          <div className="grid gap-3 lg:grid-cols-2">
            <ReplaySummaryPanel label="基线" summary={baselineReplay} />
            <ReplaySummaryPanel label="候选" summary={candidateReplay} />
          </div>
        </div>
      ) : null}
    </div>
  );
}

function ReplaySummaryPanel({ label, summary }: { label: string; summary?: ReplaySummary }) {
  const replayed = summary?.replayed_cases ?? [];
  const skipped = summary?.skipped_cases ?? [];
  const cases = [...replayed, ...skipped];
  if (!summary) {
    return (
      <div className="rounded-md border border-dashed border-slate-200 bg-slate-50 px-3 py-2 text-xs text-slate-500">
        {label}：暂无回放数据
      </div>
    );
  }
  return (
    <div className="rounded-md border border-slate-200 bg-slate-50 p-3">
      <div className="flex flex-wrap items-center gap-2 text-xs">
        <span className="font-semibold text-ink">{label}</span>
        <StatusPill label={`已回放 ${replayed.length}`} tone="green" />
        <StatusPill label={`已跳过 ${skipped.length}`} tone={skipped.length > 0 ? "amber" : "slate"} />
      </div>
      {cases.length === 0 ? (
        <div className="mt-2 text-xs text-slate-500">暂无已记录的回放用例。</div>
      ) : (
        <div className="mt-2 space-y-2">
          {cases.slice(0, 5).map((item, index) => (
            <div key={`${label}-${item.case_id ?? "case"}-${index}`} className="rounded-md border border-slate-200 bg-white px-3 py-2 text-xs text-slate-600">
              <div className="flex flex-wrap items-center gap-2">
                <StatusPill label={String(item.replay_status ?? "unknown")} tone={replayTone(item.replay_status)} />
                <span className="font-semibold text-ink">{item.case_id ?? "用例"}</span>
                {item.task_type ? <span>{formatTaskType(item.task_type)}</span> : null}
              </div>
              <div className="mt-1">
                计划 {displayLabel(item.plan_status)}；证据 {item.evidence_count ?? 0}；任务 {displayLabel(item.task_status)}
              </div>
              {item.reason ? <div className="mt-1 text-slate-500">{formatReason(item.reason)}</div> : null}
            </div>
          ))}
          {cases.length > 5 ? <div className="text-xs text-slate-500">另有 {cases.length - 5} 条回放用例</div> : null}
        </div>
      )}
    </div>
  );
}

function SuggestionRevisions({
  revisions,
  restoringRevisionId,
  onRestore
}: {
  revisions: HermesRevision[];
  restoringRevisionId: string;
  onRestore: (revision: HermesRevision) => void;
}) {
  if (revisions.length === 0) return null;
  return (
    <div className="mt-3 rounded-md border border-slate-200 bg-white p-3">
      <div className="mb-2 text-xs font-semibold uppercase tracking-normal text-slate-500">修订历史</div>
      <div className="space-y-2">
        {revisions.slice(-4).map((revision) => (
          <div key={revision.id} className="rounded-md border border-slate-200 bg-slate-50 px-3 py-2 text-xs text-slate-600">
            <div className="flex flex-wrap items-center gap-2">
              <StatusPill label={`#${revision.sequence}`} tone="slate" />
              <span className="font-semibold text-ink">{displayLabel(revision.action)}</span>
              {revision.policy_decision?.status ? <StatusPill label={revision.policy_decision.status} tone={statusTone(revision.policy_decision.status)} /> : null}
              {revision.created_at ? <span>{new Date(revision.created_at).toLocaleString()}</span> : null}
              {canRestoreRevision(revision) ? (
                <button
                  onClick={() => onRestore(revision)}
                  className="inline-flex items-center rounded-md border border-slate-200 bg-white px-2 py-1 text-xs font-semibold text-slate-700 hover:border-moss/50"
                >
                  {restoringRevisionId === revision.id ? "恢复中" : "恢复"}
                </button>
              ) : null}
            </div>
            <div className="mt-1 break-words text-slate-500">{revisionSummary(revision)}</div>
          </div>
        ))}
      </div>
    </div>
  );
}

function canRestoreRevision(revision: HermesRevision) {
  return ["memory", "skill"].includes(revision.target_type) && revision.action !== "manual_rollback";
}

function revisionSummary(revision: HermesRevision) {
  const snapshot = revision.snapshot ?? {};
  if (typeof snapshot.rolled_back_id === "string") {
    return `已回滚 ${shortId(snapshot.rolled_back_id)}`;
  }
  if (typeof snapshot.content === "string") {
    return snapshot.content;
  }
  if (typeof snapshot.description === "string") {
    return snapshot.description;
  }
  if (typeof snapshot.name === "string") {
    return snapshot.name;
  }
  if (typeof snapshot.id === "string") {
    return shortId(snapshot.id);
  }
  return "已记录快照";
}

function shortId(value?: string | null) {
  return value ? value.slice(0, 8) : "-";
}

function comparisonTone(status?: string) {
  if (status === "improved") return "green";
  if (status === "regressed") return "red";
  return "slate";
}

function replayTone(status?: string) {
  if (status === "replayed") return "green";
  if (status === "skipped") return "amber";
  return "slate";
}

function suggestionKey(suggestion: ImprovementSuggestion) {
  return suggestion.id || `${suggestion.target_type}-${suggestion.target_id}-${suggestion.suggestion_type}`;
}

function SkillCandidateCard({
  skill,
  onApprove,
  onReject,
  onArchive,
  onSave
}: {
  skill: Skill;
  onApprove: () => void;
  onReject: () => void;
  onArchive: () => void;
  onSave: (draft: SkillEditDraft) => Promise<void>;
}) {
  const [isEditing, setIsEditing] = useState(false);
  const [draft, setDraft] = useState<SkillEditDraft>(() => ({
    description: skill.description,
    promptTemplate: skill.prompt_template,
    triggerPatterns: Array.isArray(skill.metadata_json.trigger_patterns)
      ? skill.metadata_json.trigger_patterns.join(", ")
      : "",
    steps: Array.isArray(skill.metadata_json.steps) ? skill.metadata_json.steps.join(", ") : ""
  }));
  const [isSaving, setIsSaving] = useState(false);

  async function save() {
    setIsSaving(true);
    try {
      await onSave(draft);
      setIsEditing(false);
    } finally {
      setIsSaving(false);
    }
  }

  if (!isEditing) {
    return (
      <CandidateCard
        title={skill.name}
        body={skill.description || skill.prompt_template}
        metadata={skill.metadata_json}
        onApprove={onApprove}
        onReject={onReject}
        onArchive={onArchive}
        onEdit={() => setIsEditing(true)}
        footer={<ReviewHistory metadata={skill.metadata_json} />}
      />
    );
  }

  return (
    <article className="rounded-lg border border-moss/30 bg-white p-4">
      <div className="font-semibold text-ink">{skill.name}</div>
      <div className="mt-4 space-y-3">
        <Field label="描述" value={draft.description} onChange={(description) => setDraft({ ...draft, description })} />
        <Field label="触发模式" value={draft.triggerPatterns} onChange={(triggerPatterns) => setDraft({ ...draft, triggerPatterns })} />
        <Field label="执行步骤" value={draft.steps} onChange={(steps) => setDraft({ ...draft, steps })} />
        <label className="block text-sm font-medium text-slate-700">
          提示词模板
          <textarea
            value={draft.promptTemplate}
            onChange={(event) => setDraft({ ...draft, promptTemplate: event.target.value })}
            className="mt-1 min-h-28 w-full rounded-md border border-slate-200 bg-white px-3 py-2 text-sm text-slate-800 outline-none focus:border-moss"
          />
        </label>
      </div>
      <div className="mt-4 flex flex-wrap gap-2">
        <ActionButton label={isSaving ? "保存中" : "保存"} icon={<Check className="h-4 w-4" />} onClick={save} />
        <ActionButton label="取消" icon={<X className="h-4 w-4" />} onClick={() => setIsEditing(false)} />
      </div>
    </article>
  );
}

function WorkflowLessonCandidateCard({
  memory,
  onApprove,
  onReject,
  onArchive,
  onSave
}: {
  memory: Memory;
  onApprove: () => void;
  onReject: () => void;
  onArchive: () => void;
  onSave: (draft: WorkflowLessonDraft) => Promise<void>;
}) {
  const [isEditing, setIsEditing] = useState(false);
  const [draft, setDraft] = useState<WorkflowLessonDraft>(() => ({ content: memory.content }));
  const [isSaving, setIsSaving] = useState(false);

  async function save() {
    setIsSaving(true);
    try {
      await onSave(draft);
      setIsEditing(false);
    } finally {
      setIsSaving(false);
    }
  }

  if (!isEditing) {
    return (
      <CandidateCard
        title="工作流经验"
        body={memory.content}
        metadata={memory.metadata_json}
        onApprove={onApprove}
        onReject={onReject}
        onArchive={onArchive}
        onEdit={() => setIsEditing(true)}
        footer={<ReviewHistory metadata={memory.metadata_json} />}
      />
    );
  }

  return (
    <article className="rounded-lg border border-moss/30 bg-white p-4">
      <div className="font-semibold text-ink">工作流经验</div>
      <label className="mt-4 block text-sm font-medium text-slate-700">
        经验内容
        <textarea
          value={draft.content}
          onChange={(event) => setDraft({ content: event.target.value })}
          className="mt-1 min-h-28 w-full rounded-md border border-slate-200 bg-white px-3 py-2 text-sm text-slate-800 outline-none focus:border-moss"
        />
      </label>
      <div className="mt-4 flex flex-wrap gap-2">
        <ActionButton label={isSaving ? "保存中" : "保存"} icon={<Check className="h-4 w-4" />} onClick={save} />
        <ActionButton label="取消" icon={<X className="h-4 w-4" />} onClick={() => setIsEditing(false)} />
      </div>
    </article>
  );
}

function Field({ label, value, onChange }: { label: string; value: string; onChange: (value: string) => void }) {
  return (
    <label className="block text-sm font-medium text-slate-700">
      {label}
      <input
        value={value}
        onChange={(event) => onChange(event.target.value)}
        className="mt-1 w-full rounded-md border border-slate-200 bg-white px-3 py-2 text-sm text-slate-800 outline-none focus:border-moss"
      />
    </label>
  );
}

function CandidateCard({
  title,
  body,
  metadata,
  onApprove,
  onReject,
  onArchive,
  onEdit,
  footer
}: {
  title: string;
  body: string;
  metadata: Record<string, unknown>;
  onApprove: () => void;
  onReject: () => void;
  onArchive: () => void;
  onEdit?: () => void;
  footer?: React.ReactNode;
}) {
  const status = String(metadata.status ?? "active");
  const confidence = metadata.confidence === undefined ? "-" : Number(metadata.confidence).toFixed(2);
  return (
    <article className="rounded-lg border border-slate-200 bg-slate-50 p-4">
      <div className="flex items-start justify-between gap-3">
        <div className="min-w-0">
          <div className="truncate font-semibold text-ink">{title}</div>
          <div className="mt-1 flex flex-wrap gap-2 text-xs text-slate-500">
            <StatusPill label={status} tone={statusTone(status)} />
            <span>置信度 {confidence}</span>
            {metadata.source_task_id ? <span>任务 {String(metadata.source_task_id).slice(0, 8)}</span> : null}
          </div>
        </div>
      </div>
      <p className="mt-3 line-clamp-4 whitespace-pre-wrap text-sm leading-6 text-slate-700">{body}</p>
      {metadata.reason ? <p className="mt-2 text-xs leading-5 text-slate-500">{formatReason(String(metadata.reason))}</p> : null}
      <div className="mt-4 flex flex-wrap gap-2">
        <ActionButton label="通过" icon={<Check className="h-4 w-4" />} onClick={onApprove} />
        <ActionButton label="拒绝" icon={<X className="h-4 w-4" />} onClick={onReject} />
        <ActionButton label="归档" icon={<History className="h-4 w-4" />} onClick={onArchive} />
        {onEdit ? <ActionButton label="编辑" icon={<ListChecks className="h-4 w-4" />} onClick={onEdit} /> : null}
      </div>
      {footer ? <div className="mt-4">{footer}</div> : null}
    </article>
  );
}

function ReviewHistory({ metadata }: { metadata: Record<string, unknown> }) {
  const history = Array.isArray(metadata.review_history)
    ? (metadata.review_history as ReviewHistoryEntry[]).slice(-3).reverse()
    : [];
  if (history.length === 0) {
    return <div className="rounded-md border border-dashed border-slate-200 bg-white px-3 py-2 text-xs text-slate-500">暂无审核历史。</div>;
  }
  return (
    <div className="rounded-md border border-slate-200 bg-white p-3">
      <div className="mb-2 text-xs font-semibold uppercase tracking-normal text-slate-500">审核历史</div>
      <div className="space-y-2">
        {history.map((entry, index) => (
          <div key={`${entry.reviewed_at ?? "history"}-${index}`} className="text-xs leading-5 text-slate-600">
            <div className="flex flex-wrap items-center gap-2">
              <StatusPill label={String(entry.action ?? "review")} tone="slate" />
              <span>{entry.reviewed_by ? `审核人 ${entry.reviewed_by}` : "审核人未知"}</span>
              {entry.reviewed_at ? <span>{new Date(entry.reviewed_at).toLocaleString()}</span> : null}
            </div>
            <div className="mt-1 text-slate-500">{formatHistoryDetail(entry)}</div>
          </div>
        ))}
      </div>
    </div>
  );
}

function formatHistoryDetail(entry: ReviewHistoryEntry) {
  if (entry.action === "status_update") {
    return `${displayLabel(entry.from_status)} -> ${displayLabel(entry.to_status)}`;
  }
  if (entry.action === "content_update") {
    return `已修改 ${entry.changed_fields?.join(", ") || "技能字段"}`;
  }
  return "已记录审核事件";
}

function parseList(value: string) {
  return value.split(",").map((item) => item.trim()).filter(Boolean);
}

function ActionButton({ label, icon, onClick }: { label: string; icon: React.ReactNode; onClick: () => void }) {
  return (
    <button onClick={onClick} className="inline-flex items-center gap-2 rounded-md border border-slate-200 bg-white px-3 py-1.5 text-xs font-semibold text-slate-700 hover:border-moss/50">
      {icon}
      {label}
    </button>
  );
}

function LoadingBox() {
  return <div className="rounded-lg border border-dashed border-slate-300 bg-slate-50 p-8 text-center text-sm text-slate-500">正在加载候选项...</div>;
}

function PageHeader({
  title,
  description,
  action,
  icon
}: {
  title: string;
  description: string;
  action?: React.ReactNode;
  icon?: React.ReactNode;
}) {
  return (
    <div className="flex flex-col gap-4 rounded-lg border border-slate-200 bg-white p-5 shadow-sm md:flex-row md:items-center md:justify-between">
      <div className="flex min-w-0 items-start gap-4">
        {icon ? <div className="grid h-11 w-11 shrink-0 place-items-center rounded-md bg-moss/10 text-moss [&_svg]:h-5 [&_svg]:w-5">{icon}</div> : null}
        <div className="min-w-0">
          <h1 className="text-2xl font-semibold tracking-normal text-ink md:text-3xl">{title}</h1>
          <p className="mt-2 max-w-3xl text-sm leading-6 text-slate-600">{description}</p>
        </div>
      </div>
      {action ? <div className="shrink-0">{action}</div> : null}
    </div>
  );
}

function StatCard({
  label,
  value,
  icon,
  tone = "moss"
}: {
  label: string;
  value: string | number;
  icon: React.ReactNode;
  tone?: "moss" | "rust" | "blue" | "slate";
}) {
  const toneClass = {
    moss: "bg-moss/10 text-moss",
    rust: "bg-rust/10 text-rust",
    blue: "bg-bluegray/10 text-bluegray",
    slate: "bg-slate-100 text-slate-600"
  }[tone];

  return (
    <div className="rounded-lg border border-slate-200 bg-white p-4 shadow-sm">
      <div className={`mb-3 grid h-9 w-9 place-items-center rounded-md ${toneClass} [&_svg]:h-4 [&_svg]:w-4`}>{icon}</div>
      <div className="text-xs font-medium text-slate-500">{label}</div>
      <div className="mt-1 truncate text-xl font-semibold text-ink">{value}</div>
    </div>
  );
}

function StatusPill({ label, tone = "slate" }: { label: string; tone?: "green" | "amber" | "red" | "slate" }) {
  const toneClass = {
    green: "border-emerald-200 bg-emerald-50 text-emerald-700",
    amber: "border-amber-200 bg-amber-50 text-amber-700",
    red: "border-red-200 bg-red-50 text-red-700",
    slate: "border-slate-200 bg-slate-50 text-slate-600"
  }[tone];

  return <span className={`inline-flex items-center rounded-md border px-2 py-1 text-xs font-semibold ${toneClass}`}>{displayLabel(label)}</span>;
}

function EmptyState({ title, description, icon }: { title: string; description: string; icon: React.ReactNode }) {
  return (
    <div className="flex min-h-48 flex-col items-center justify-center rounded-lg border border-dashed border-slate-300 bg-slate-50 p-8 text-center">
      <div className="mb-4 grid h-12 w-12 place-items-center rounded-md bg-white text-slate-500 shadow-sm [&_svg]:h-6 [&_svg]:w-6">{icon}</div>
      <h2 className="text-base font-semibold text-ink">{title}</h2>
      <p className="mt-2 max-w-md text-sm leading-6 text-slate-600">{description}</p>
    </div>
  );
}

function statusTone(status: string) {
  if (status === "active") return "green";
  if (status === "draft") return "amber";
  if (status === "rejected") return "red";
  return "slate";
}
