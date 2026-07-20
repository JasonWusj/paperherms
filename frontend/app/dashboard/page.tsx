import Link from "next/link";
import {
  Activity,
  BarChart3,
  BrainCircuit,
  Database,
  FileText,
  Gauge,
  ListChecks,
  MessageSquare,
  Radar,
  Search,
  Sparkles,
  UploadCloud
} from "lucide-react";
import { type AgentTask, type Paper, api } from "@/lib/api";

const quickActions = [
  { href: "/papers/upload", label: "上传论文", icon: UploadCloud, desc: "解析并建立索引" },
  { href: "/chat", label: "论文问答", icon: MessageSquare, desc: "基于证据回答" },
  { href: "/papers", label: "论文库", icon: FileText, desc: "查看已入库论文" },
  { href: "/traces", label: "执行追踪", icon: Search, desc: "审计 Agent 链路" }
];

export default async function DashboardPage() {
  let papers: Paper[] = [];
  let tasks: AgentTask[] = [];
  try {
    papers = await api.papers();
  } catch {
    papers = [];
  }
  try {
    tasks = await api.agentTasks(20);
  } catch {
    tasks = [];
  }

  const indexed = papers.filter((paper) => paper.status === "parsed").length;
  const latest = papers.slice(0, 4);
  const readiness = papers.length === 0 ? 0 : Math.round((indexed / papers.length) * 100);
  const completedTasks = tasks.filter((task) => task.status === "completed").length;
  const failedTasks = tasks.filter((task) => task.status === "failed").length;
  const activeTasks = tasks.filter((task) => !["completed", "failed"].includes(task.status)).length;
  const taskRows = [
    { label: "已完成", value: completedTasks, className: "bg-emerald-300" },
    { label: "进行中 / 待处理", value: activeTasks, className: "bg-cyan-300" },
    { label: "失败", value: failedTasks, className: "bg-rose-300" }
  ];

  return (
    <div className="min-h-[calc(100vh-6rem)] overflow-hidden rounded-xl bg-[#07111f] p-5 text-slate-100 shadow-2xl ring-1 ring-slate-900/10">
      <div className="pointer-events-none absolute inset-0 -z-10 bg-[#07111f]" />
      <section className="grid gap-5 xl:grid-cols-[1.05fr_1.4fr_1.05fr]">
        <div className="space-y-5">
          <BigPanel title="平台概览" icon={<Gauge className="h-4 w-4" />}>
            <div className="space-y-4">
              <MetricBlock label="已入库论文" value={String(papers.length)} tone="cyan" />
              <MetricBlock label="索引完成率" value={`${readiness}%`} tone="emerald" />
              <MetricBlock label="运行模式" value="本地工程化" tone="amber" />
            </div>
          </BigPanel>

          <BigPanel title="快捷入口" icon={<Sparkles className="h-4 w-4" />}>
            <div className="grid gap-3">
              {quickActions.map((action) => (
                <Link
                  key={action.href}
                  href={action.href}
                  className="group flex items-center gap-3 rounded-lg border border-cyan-400/10 bg-white/[0.04] p-3 transition hover:border-cyan-300/40 hover:bg-cyan-300/10"
                >
                  <span className="grid h-10 w-10 place-items-center rounded-md bg-cyan-300/10 text-cyan-200">
                    <action.icon className="h-5 w-5" />
                  </span>
                  <span className="min-w-0">
                    <span className="block text-sm font-semibold text-white">{action.label}</span>
                    <span className="text-xs text-slate-400">{action.desc}</span>
                  </span>
                </Link>
              ))}
            </div>
          </BigPanel>
        </div>

        <div className="space-y-5">
          <div className="rounded-xl border border-cyan-300/20 bg-[radial-gradient(circle_at_top,#123457,transparent_55%),linear-gradient(180deg,rgba(15,23,42,.96),rgba(7,17,31,.96))] p-5 shadow-[0_0_45px_rgba(34,211,238,.08)]">
            <div className="flex flex-col gap-4 lg:flex-row lg:items-start lg:justify-between">
              <div>
                <div className="mb-3 inline-flex items-center gap-2 rounded-full border border-cyan-300/30 bg-cyan-300/10 px-3 py-1 text-xs font-semibold text-cyan-100">
                  <Activity className="h-3.5 w-3.5" />
                  PaperHermes 论文智能分析大屏
                </div>
                <h1 className="text-3xl font-semibold tracking-normal text-white md:text-4xl">科研论文态势驾驶舱</h1>
                <p className="mt-3 max-w-2xl text-sm leading-6 text-slate-300">
                  监控论文入库、向量索引、RAG 检索和 Agent 分析链路，把上传、检索、问答和追踪集中到一个工作台视图。
                </p>
              </div>
              <div className="rounded-lg border border-cyan-300/20 bg-cyan-300/10 px-4 py-3 text-right">
                <div className="text-xs text-cyan-100">统计范围</div>
                <div className="mt-1 text-sm font-semibold text-cyan-100">
                  论文库 / 最近 {tasks.length} 条任务
                </div>
              </div>
            </div>

            <div className="mt-8 grid gap-4 md:grid-cols-3">
              <HeroMetric icon={<FileText />} label="论文资产" value={papers.length} unit="篇" />
              <HeroMetric icon={<Database />} label="已解析索引" value={indexed} unit="篇" />
              <HeroMetric icon={<BrainCircuit />} label="分析能力" value={5} unit="类" />
            </div>

            <div className="mt-8 grid gap-5 lg:grid-cols-[1.15fr_.85fr]">
              <div className="rounded-xl border border-slate-700/70 bg-slate-950/40 p-4">
                <div className="mb-4 flex items-center justify-between">
                  <div className="flex items-center gap-2 text-sm font-semibold text-white">
                    <ListChecks className="h-4 w-4 text-cyan-300" /> 最近分析任务
                  </div>
                  <span className="text-xs text-slate-400">最近 {tasks.length} 条 Trace</span>
                </div>
                {tasks.length === 0 ? (
                  <div className="rounded-lg border border-dashed border-slate-700 p-5 text-sm text-slate-400">
                    暂无分析任务记录。运行论文问答或分析后，这里会显示真实任务状态分布。
                  </div>
                ) : (
                  <div className="space-y-4">
                    {taskRows.map((item) => (
                      <TaskStatusRow key={item.label} label={item.label} value={item.value} total={tasks.length} className={item.className} />
                    ))}
                    <div className="grid grid-cols-3 gap-2 pt-1 text-center text-xs">
                      <MiniTaskMetric label="总任务" value={tasks.length} />
                      <MiniTaskMetric label="完成" value={completedTasks} />
                      <MiniTaskMetric label="异常" value={failedTasks} />
                    </div>
                  </div>
                )}
              </div>

              <div className="rounded-xl border border-slate-700/70 bg-slate-950/40 p-4">
                <div className="mb-4 flex items-center gap-2 text-sm font-semibold text-white">
                  <Radar className="h-4 w-4 text-emerald-300" /> 能力雷达
                </div>
                <div className="grid aspect-square place-items-center rounded-full border border-cyan-300/20 bg-[radial-gradient(circle,rgba(34,211,238,.2),transparent_62%)]">
                  <div className="grid h-4/5 w-4/5 place-items-center rounded-full border border-emerald-300/20">
                    <div className="grid h-3/5 w-3/5 place-items-center rounded-full border border-cyan-300/30 bg-cyan-300/10 text-center">
                      <span className="text-2xl font-semibold text-white">RAG</span>
                      <span className="text-xs text-cyan-100">可信问答</span>
                    </div>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>

        <div className="space-y-5">
          <BigPanel title="最近入库" icon={<FileText className="h-4 w-4" />}>
            <div className="space-y-3">
              {latest.length === 0 ? (
                <div className="rounded-lg border border-dashed border-slate-700 p-5 text-sm text-slate-400">暂无论文，先上传 PDF 建立分析资产。</div>
              ) : (
                latest.map((paper) => (
                  <Link key={paper.id} href={`/papers/${paper.id}`} className="block rounded-lg border border-slate-700/70 bg-white/[0.03] p-3 hover:border-cyan-300/40">
                    <div className="line-clamp-2 text-sm font-semibold text-white">{paper.title || paper.original_filename}</div>
                    <div className="mt-2 flex items-center justify-between text-xs text-slate-400">
                      <span>{paper.status === "parsed" ? "已解析" : paper.status}</span>
                      <span>{paper.id.slice(0, 8)}</span>
                    </div>
                  </Link>
                ))
              )}
            </div>
          </BigPanel>

          <BigPanel title="系统状态" icon={<BarChart3 className="h-4 w-4" />}>
            <div className="space-y-3 text-sm">
              <StatusRow label="PostgreSQL" value="持久化存储" />
              <StatusRow label="Qdrant" value="向量检索" />
              <StatusRow label="LLM" value="OpenAI 兼容" />
              <StatusRow label="Trace" value="全链路记录" />
            </div>
          </BigPanel>
        </div>
      </section>
    </div>
  );
}

function BigPanel({ title, icon, children }: { title: string; icon: React.ReactNode; children: React.ReactNode }) {
  return (
    <section className="rounded-xl border border-slate-700/80 bg-slate-950/60 p-4 shadow-[inset_0_1px_0_rgba(255,255,255,.04)]">
      <div className="mb-4 flex items-center justify-between">
        <h2 className="flex items-center gap-2 text-sm font-semibold text-slate-100">{icon}{title}</h2>
        <span className="h-2 w-2 rounded-full bg-cyan-300 shadow-[0_0_16px_rgba(103,232,249,.9)]" />
      </div>
      {children}
    </section>
  );
}

function MetricBlock({ label, value, tone }: { label: string; value: string; tone: "cyan" | "emerald" | "amber" }) {
  const toneClass = tone === "cyan" ? "text-cyan-200" : tone === "emerald" ? "text-emerald-200" : "text-amber-200";
  return (
    <div className="rounded-lg border border-slate-700/80 bg-white/[0.04] p-4">
      <div className="text-xs text-slate-400">{label}</div>
      <div className={`mt-2 text-3xl font-semibold ${toneClass}`}>{value}</div>
    </div>
  );
}

function HeroMetric({ icon, label, value, unit }: { icon: React.ReactNode; label: string; value: number; unit: string }) {
  return (
    <div className="rounded-xl border border-cyan-300/20 bg-cyan-300/10 p-4">
      <div className="mb-3 flex h-10 w-10 items-center justify-center rounded-md bg-cyan-300/10 text-cyan-200 [&_svg]:h-5 [&_svg]:w-5">{icon}</div>
      <div className="text-xs text-cyan-100/80">{label}</div>
      <div className="mt-1 text-3xl font-semibold text-white">{value}<span className="ml-1 text-sm text-slate-300">{unit}</span></div>
    </div>
  );
}

function StatusRow({ label, value }: { label: string; value: string }) {
  return (
    <div className="flex items-center justify-between rounded-md border border-slate-700/70 bg-white/[0.03] px-3 py-2">
      <span className="text-slate-300">{label}</span>
      <span className="text-cyan-200">{value}</span>
    </div>
  );
}

function TaskStatusRow({ label, value, total, className }: { label: string; value: number; total: number; className: string }) {
  const percent = total === 0 ? 0 : Math.round((value / total) * 100);
  return (
    <div>
      <div className="mb-1 flex items-center justify-between text-xs">
        <span className="text-slate-300">{label}</span>
        <span className="text-cyan-200">{value} / {total}</span>
      </div>
      <div className="h-2 rounded-full bg-slate-800">
        <div className={`h-2 rounded-full ${className}`} style={{ width: `${percent}%` }} />
      </div>
    </div>
  );
}

function MiniTaskMetric({ label, value }: { label: string; value: number }) {
  return (
    <div className="rounded-md border border-slate-700/70 bg-white/[0.03] px-2 py-2">
      <div className="text-slate-400">{label}</div>
      <div className="mt-1 text-base font-semibold text-white">{value}</div>
    </div>
  );
}
