"use client";

import { FormEvent, useEffect, useMemo, useState } from "react";
import {
  AlertTriangle,
  BrainCircuit,
  CheckCircle2,
  ChevronRight,
  Clock3,
  Database,
  History,
  ListChecks,
  RefreshCw,
  Search,
  Wrench,
  XCircle
} from "lucide-react";
import { EmptyState, PageHeader, StatCard, StatusPill } from "@/components/PageChrome";
import { Panel } from "@/components/Panel";
import { AgentTask, TraceStep, api } from "@/lib/api";

export default function TracesPage() {
  const [taskId, setTaskId] = useState("");
  const [tasks, setTasks] = useState<AgentTask[]>([]);
  const [task, setTask] = useState<AgentTask | null>(null);
  const [steps, setSteps] = useState<TraceStep[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [isLoadingTasks, setIsLoadingTasks] = useState(true);
  const [error, setError] = useState("");

  async function refreshTasks() {
    setIsLoadingTasks(true);
    try {
      const result = await api.agentTasks(20);
      setTasks(result);
      setTaskId((current) => current || result[0]?.id || "");
    } catch {
      setTasks([]);
    } finally {
      setIsLoadingTasks(false);
    }
  }

  async function loadTraceById(id: string) {
    const trimmed = id.trim();
    if (!trimmed) {
      setError("请先从最近任务中选择一个任务，或手动输入追踪编号。");
      return;
    }
    setIsLoading(true);
    setError("");
    try {
      const [nextTask, nextSteps] = await Promise.all([api.agentTask(trimmed), api.agentTrace(trimmed)]);
      setTask(nextTask);
      setSteps(nextSteps);
      setTaskId(trimmed);
    } catch (caught) {
      setTask(null);
      setSteps([]);
      setError(formatTraceError(caught));
    } finally {
      setIsLoading(false);
    }
  }

  async function loadTrace(event?: FormEvent<HTMLFormElement>) {
    event?.preventDefault();
    await loadTraceById(taskId);
  }

  useEffect(() => {
    refreshTasks();
  }, []);

  const stats = useMemo(() => {
    const retrieved = steps.reduce((total, step) => total + step.retrieved_chunks.length, 0);
    const failed = steps.filter((step) => step.status !== "success").length;
    const tools = steps.reduce((total, step) => total + step.tool_calls.length, 0);
    return { retrieved, failed, tools };
  }, [steps]);

  return (
    <div className="space-y-6">
      <PageHeader
        title="执行追踪"
        description="查看一次论文 Agent 任务的规划、检索、工具调用和反思链路。可以从最近任务中直接选择，也可以手动输入追踪编号。"
        icon={<History />}
      />

      <div className="grid gap-4 md:grid-cols-4">
        <StatCard label="最近任务" value={tasks.length} icon={<ListChecks />} tone="moss" />
        <StatCard label="当前任务" value={task ? taskTypeLabel(task.task_type) : "未选择"} icon={<BrainCircuit />} tone="blue" />
        <StatCard label="执行步骤" value={steps.length} icon={<History />} tone="rust" />
        <StatCard label="证据片段" value={stats.retrieved} icon={<Database />} tone="slate" />
      </div>

      <div className="grid gap-6 xl:grid-cols-[0.85fr_1.15fr]">
        <Panel
          title="最近任务"
          action={
            <button onClick={refreshTasks} className="inline-flex items-center gap-2 text-sm font-semibold text-moss hover:text-moss/80">
              <RefreshCw className="h-4 w-4" />
              刷新
            </button>
          }
        >
          {isLoadingTasks ? (
            <div className="rounded-lg border border-dashed border-slate-300 bg-slate-50 p-8 text-center text-sm text-slate-500">正在加载最近任务...</div>
          ) : tasks.length === 0 ? (
            <EmptyState title="还没有可追踪任务" description="先在论文问答、论文分析或上传流程中执行一次任务，完成后这里会出现追踪入口。" icon={<ListChecks />} />
          ) : (
            <div className="space-y-3">
              {tasks.map((item) => (
                <button
                  key={item.id}
                  onClick={() => loadTraceById(item.id)}
                  className={`w-full rounded-lg border p-4 text-left transition hover:border-moss/40 hover:bg-white ${
                    item.id === taskId ? "border-moss/50 bg-moss/5" : "border-slate-200 bg-slate-50"
                  }`}
                >
                  <div className="flex items-start justify-between gap-3">
                    <div className="min-w-0">
                      <div className="font-semibold text-ink">{taskTypeLabel(item.task_type)}</div>
                      <div className="mt-1 line-clamp-1 text-sm text-slate-600">{item.input_text || "无输入摘要"}</div>
                    </div>
                    <StatusPill label={statusLabel(item.status)} tone={item.status === "completed" || item.status === "success" ? "green" : "slate"} />
                  </div>
                  <div className="mt-3 flex flex-wrap items-center gap-3 text-xs text-slate-500">
                    <span>追踪编号 {item.id.slice(0, 8)}</span>
                    <span>{formatDate(item.updated_at)}</span>
                  </div>
                </button>
              ))}
            </div>
          )}
        </Panel>

        <div className="space-y-6">
          <Panel title="手动加载">
            <form onSubmit={loadTrace} className="flex flex-col gap-3 md:flex-row">
              <input
                value={taskId}
                onChange={(event) => setTaskId(event.target.value)}
                className="min-w-0 flex-1 rounded-md border border-slate-300 px-3 py-2 text-sm outline-none focus:border-moss"
                placeholder="输入追踪编号"
              />
              <button
                type="submit"
                disabled={isLoading}
                className="inline-flex h-10 items-center justify-center gap-2 rounded-md bg-moss px-4 text-sm font-semibold text-white disabled:cursor-not-allowed disabled:opacity-60"
              >
                <Search className="h-4 w-4" />
                {isLoading ? "加载中" : "加载追踪"}
              </button>
            </form>
          </Panel>

          {error ? (
            <div className="flex items-start gap-2 rounded-md border border-red-200 bg-red-50 p-3 text-sm text-red-700">
              <AlertTriangle className="mt-0.5 h-4 w-4 shrink-0" />
              <span className="break-all">{error}</span>
            </div>
          ) : null}

          {task ? (
            <div className="grid gap-4 md:grid-cols-3">
              <Metric label="任务类型" value={taskTypeLabel(task.task_type)} icon={<BrainCircuit className="h-4 w-4" />} />
              <Metric label="执行状态" value={statusLabel(task.status)} icon={<CheckCircle2 className="h-4 w-4" />} />
              <Metric label="追踪编号" value={task.id.slice(0, 8)} icon={<History className="h-4 w-4" />} />
            </div>
          ) : null}
        </div>
      </div>

      <Panel title="执行链路">
        {steps.length === 0 ? (
          <div className="flex min-h-64 items-center justify-center rounded-md border border-dashed border-slate-300 text-sm text-slate-500">
            从最近任务中选择一项，或输入追踪编号后加载执行追踪。
          </div>
        ) : (
          <div className="space-y-4">
            <div className="grid gap-3 text-sm md:grid-cols-3">
              <SummaryCell label="工具调用" value={stats.tools} />
              <SummaryCell label="失败步骤" value={stats.failed} />
              <SummaryCell label="最近更新" value={formatDate(steps[steps.length - 1]?.created_at)} />
            </div>
            <div className="relative space-y-4 pl-6">
              <div className="absolute bottom-0 left-[0.68rem] top-0 w-px bg-slate-200" />
              {steps.map((step, index) => (
                <TraceStepCard key={step.id} step={step} index={index} />
              ))}
            </div>
          </div>
        )}
      </Panel>
    </div>
  );
}

function Metric({ label, value, icon }: { label: string; value: string; icon: React.ReactNode }) {
  return (
    <div className="rounded-lg border border-slate-200 bg-white p-4 shadow-sm">
      <div className="mb-2 flex items-center gap-2 text-xs font-medium text-slate-500">
        {icon}
        {label}
      </div>
      <div className="truncate text-base font-semibold text-ink">{value}</div>
    </div>
  );
}

function SummaryCell({ label, value }: { label: string; value: string | number }) {
  return (
    <div className="rounded-md border border-slate-200 px-3 py-2">
      <div className="text-xs text-slate-500">{label}</div>
      <div className="mt-1 font-semibold text-ink">{value}</div>
    </div>
  );
}

function TraceStepCard({ step, index }: { step: TraceStep; index: number }) {
  const isSuccess = step.status === "success";
  return (
    <article className="relative rounded-md border border-slate-200 bg-white p-4">
      <div className="absolute -left-[1.57rem] top-5 flex h-6 w-6 items-center justify-center rounded-full border border-slate-200 bg-white">
        {isSuccess ? <CheckCircle2 className="h-4 w-4 text-moss" /> : <XCircle className="h-4 w-4 text-red-500" />}
      </div>
      <div className="flex flex-col gap-3 lg:flex-row lg:items-start lg:justify-between">
        <div className="min-w-0">
          <div className="flex flex-wrap items-center gap-2">
            <span className="rounded-md bg-slate-100 px-2 py-1 text-xs font-semibold text-slate-600">第 {index + 1} 步</span>
            <h2 className="text-base font-semibold text-ink">{agentLabel(step.agent_name)}</h2>
            <ChevronRight className="h-4 w-4 text-slate-400" />
            <span className="break-all text-sm font-medium text-slate-700">{stepLabel(step.step_name)}</span>
          </div>
          <div className="mt-2 flex flex-wrap items-center gap-3 text-xs text-slate-500">
            <span className="inline-flex items-center gap-1">
              <Clock3 className="h-3.5 w-3.5" />
              {formatDate(step.created_at)}
            </span>
            <span>耗时 {step.latency_ms} ms</span>
            <span className={isSuccess ? "text-moss" : "text-red-600"}>{statusLabel(step.status)}</span>
          </div>
        </div>
        <div className="flex flex-wrap gap-2 text-xs">
          {step.tool_calls.map((tool, toolIndex) => (
            <span key={`${step.id}-tool-${toolIndex}`} className="inline-flex items-center gap-1 rounded-md border border-slate-200 px-2 py-1 text-slate-600">
              <Wrench className="h-3.5 w-3.5" />
              {String(tool.tool ?? tool.name ?? "工具")}
            </span>
          ))}
          <span className="inline-flex items-center gap-1 rounded-md border border-slate-200 px-2 py-1 text-slate-600">
            <Database className="h-3.5 w-3.5" />
            {step.retrieved_chunks.length} 个证据片段
          </span>
        </div>
      </div>

      {step.error ? <div className="mt-3 rounded-md bg-red-50 p-3 text-sm text-red-700">{step.error}</div> : null}

      <div className="mt-4 grid gap-3 lg:grid-cols-2">
        <JsonBlock title="输入详情" value={step.input_json} />
        <JsonBlock title="输出详情" value={step.output_json} />
      </div>

      {step.retrieved_chunks.length > 0 ? (
        <div className="mt-4 space-y-2">
          <div className="text-xs font-semibold text-slate-500">检索证据</div>
          {step.retrieved_chunks.slice(0, 4).map((chunk, chunkIndex) => (
            <div key={`${step.id}-chunk-${chunkIndex}`} className="rounded-md border border-slate-200 p-3 text-sm">
              <div className="mb-1 flex flex-wrap items-center gap-2 text-xs text-slate-500">
                <span>{String(chunk.section_title ?? "未知章节")}</span>
                {chunk.score !== undefined ? <span>相关度 {Number(chunk.score).toFixed(3)}</span> : null}
              </div>
              <p className="line-clamp-3 text-slate-700">{String(chunk.text ?? "")}</p>
            </div>
          ))}
        </div>
      ) : null}
    </article>
  );
}

function JsonBlock({ title, value }: { title: string; value: Record<string, unknown> }) {
  return (
    <details className="min-w-0 rounded-md bg-slate-50 p-3">
      <summary className="cursor-pointer text-xs font-semibold text-slate-500">{title}</summary>
      <pre className="mt-2 max-h-52 overflow-auto whitespace-pre-wrap break-words text-xs leading-5 text-slate-700">
        {JSON.stringify(value, null, 2)}
      </pre>
    </details>
  );
}

function formatDate(value?: string) {
  if (!value) return "-";
  return new Intl.DateTimeFormat("zh-CN", {
    month: "2-digit",
    day: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
    second: "2-digit"
  }).format(new Date(value));
}

function statusLabel(value: string) {
  const labels: Record<string, string> = {
    completed: "已完成",
    success: "成功",
    failed: "失败",
    pending: "等待中",
    running: "运行中"
  };
  return labels[value] ?? value;
}

function taskTypeLabel(value: string) {
  const labels: Record<string, string> = {
    paper_question_answering: "论文问答",
    paper_summary: "论文总结",
    summary: "论文总结",
    method: "方法分析",
    experiments: "实验分析",
    novelty: "创新点分析",
    limitations: "局限性分析",
    paper_method: "方法分析",
    paper_experiments: "实验分析",
    paper_novelty: "创新点分析",
    paper_limitations: "局限性分析",
    paper_ingestion: "论文入库"
  };
  return labels[value] ?? value;
}

function agentLabel(value: string) {
  const labels: Record<string, string> = {
    QAAgent: "问答 Agent",
    MethodAgent: "方法分析 Agent",
    ExperimentReaderAgent: "实验分析 Agent",
    NoveltyAgent: "创新点 Agent",
    LimitationAgent: "局限性 Agent",
    ReflectionAgent: "反思校验 Agent",
    PaperIndexer: "论文索引器",
    PDFLoader: "PDF 解析器",
    PaperParser: "论文结构解析器"
  };
  return labels[value] ?? value;
}

function stepLabel(value: string) {
  const labels: Record<string, string> = {
    answer_question: "生成问答结果",
    analyze_method: "分析核心方法",
    analyze_experiments: "分析实验设计",
    analyze_novelty: "分析创新贡献",
    analyze_limitations: "分析局限不足",
    check_answer_grounding: "检查回答依据",
    parse_pdf_text: "解析 PDF 文本",
    extract_metadata_and_sections: "抽取元数据和章节",
    chunk_and_index_paper: "分块并写入索引"
  };
  return labels[value] ?? value;
}

function formatTraceError(error: unknown) {
  const message = error instanceof Error ? error.message : String(error);
  if (message.includes("Task not found") || message.includes("404")) {
    return "没有找到这个任务。请从最近任务中选择，或确认追踪编号是否完整。";
  }
  return message || "执行追踪加载失败";
}
