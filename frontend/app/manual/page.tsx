import Link from "next/link";
import {
  BookOpen,
  BrainCircuit,
  CheckCircle2,
  CircleHelp,
  FileText,
  History,
  Library,
  ListChecks,
  MessageSquare,
  Network,
  Puzzle,
  Search,
  UploadCloud
} from "lucide-react";
import { PageHeader, StatCard, StatusPill } from "@/components/PageChrome";
import { Panel } from "@/components/Panel";

const workflow = [
  {
    title: "上传并索引论文",
    href: "/papers/upload",
    action: "进入上传论文",
    icon: UploadCloud,
    steps: [
      "选择 PDF 文件并提交上传。",
      "等待系统解析正文、抽取章节，并写入向量索引。",
      "上传完成后到论文库确认状态为已解析。"
    ],
    note: "只有完成解析和索引的论文，后续问答、分析和追踪才会有足够证据。"
  },
  {
    title: "查看论文资产",
    href: "/papers",
    action: "进入论文库",
    icon: Library,
    steps: [
      "在论文库查看已上传论文、解析状态和入库时间。",
      "点击论文卡片进入详情页，检查标题、作者、摘要和章节内容。",
      "如果章节为空或摘要异常，优先重新上传或检查 PDF 质量。"
    ],
    note: "论文详情页是确认解析质量的第一入口。"
  },
  {
    title: "基于论文提问",
    href: "/chat",
    action: "进入论文问答",
    icon: MessageSquare,
    steps: [
      "选择一篇已解析论文。",
      "输入具体问题，例如总结、方法分析、实验核查、创新点或局限性。",
      "点击开始问答，等待系统检索证据并生成回答。"
    ],
    note: "问题越明确，系统越容易匹配正确的分析技能。"
  },
  {
    title: "审计执行过程",
    href: "/traces",
    action: "进入执行追踪",
    icon: History,
    steps: [
      "在问答结果中点击查看执行追踪，或直接进入执行追踪页面。",
      "检查 SkillManager 是否选中了预期技能。",
      "查看分析 Agent、反思校验、学习沉淀和候选技能生成情况。"
    ],
    note: "执行追踪用于判断回答是否有证据、技能是否生效、学习是否可靠。"
  }
];

const modules = [
  {
    name: "分析大屏",
    href: "/dashboard",
    icon: Search,
    purpose: "查看论文资产、索引状态和常用入口。",
    use: "适合每天开始工作时快速判断系统是否有论文、索引是否完成、下一步该进入哪个模块。"
  },
  {
    name: "上传论文",
    href: "/papers/upload",
    icon: UploadCloud,
    purpose: "把 PDF 论文写入系统，生成可检索的论文资产。",
    use: "上传后等待解析完成，再进入论文库确认状态。建议优先上传文字可复制的 PDF。"
  },
  {
    name: "论文库",
    href: "/papers",
    icon: Library,
    purpose: "管理已入库论文，进入论文详情。",
    use: "用于确认论文是否解析成功，检查摘要和章节，选择需要分析的论文。"
  },
  {
    name: "论文问答",
    href: "/chat",
    icon: MessageSquare,
    purpose: "围绕单篇论文发起基于证据的问答和分析。",
    use: "输入带有 summary、method、experiments、novelty、limitations、related work 等关键词的问题，可以触发对应分析技能。"
  },
  {
    name: "阅读笔记",
    href: "/notes",
    icon: BookOpen,
    purpose: "组织论文背景、方法、实验、结论和局限等笔记结构。",
    use: "当前页面提供笔记工作入口，实际内容建议先从论文问答生成，再整理到个人笔记中。"
  },
  {
    name: "相关工作",
    href: "/related-work",
    icon: Network,
    purpose: "为相关工作综述和论文对比做准备。",
    use: "适合围绕主题提取方法差异、数据集差异、指标差异和技术脉络。"
  },
  {
    name: "研究记忆",
    href: "/memories",
    icon: BrainCircuit,
    purpose: "保存偏好、常用分析要求和可复用研究事实。",
    use: "例如保存“优先中文回答”“回答中标注依据”“先讲方法再讲实验和局限”等偏好。"
  },
  {
    name: "分析技能",
    href: "/skills",
    icon: Puzzle,
    purpose: "管理可复用论文分析提示词模板。",
    use: "技能使用 {input} 作为变量。active 技能会在问答时按任务类型自动匹配，并影响 Agent 的回答结构。"
  },
  {
    name: "学习审核",
    href: "/learning",
    icon: ListChecks,
    purpose: "审核系统自动学习出来的记忆、技能和改进建议。",
    use: "自动生成的候选项默认是 draft，建议人工确认后再批准为 active。"
  },
  {
    name: "执行追踪",
    href: "/traces",
    icon: History,
    purpose: "查看每次问答或分析的 Agent 执行链路。",
    use: "用于定位技能是否匹配、证据是否足够、反思校验是否通过、是否产生新的学习候选。"
  }
];

const skillExamples = [
  {
    intent: "结构化总结",
    prompt: "请用 summary 的方式总结这篇论文，覆盖研究问题、方法、实验、贡献和局限。",
    skill: "summary_structured_reading"
  },
  {
    intent: "方法分析",
    prompt: "请做 method 分析，并检查关键结论是否有原文证据。",
    skill: "method_evidence_check"
  },
  {
    intent: "实验核查",
    prompt: "请分析 experiments、dataset、metric 和 ablation，判断实验是否足以支撑论文结论。",
    skill: "experiments_ablation_audit"
  },
  {
    intent: "创新点判断",
    prompt: "请分析 novelty 和 contribution，并与 prior work 对比。",
    skill: "novelty_prior_work_compare"
  },
  {
    intent: "局限性审查",
    prompt: "请分析 limitations、weakness、threats 和 future work。",
    skill: "limitations_threats_futurework"
  },
  {
    intent: "相关工作矩阵",
    prompt: "请做 related work comparison matrix，按方法、任务、数据集、指标和贡献对比。",
    skill: "related_work_comparison_matrix"
  }
];

const reviewItems = [
  {
    label: "active",
    meaning: "已经启用，会参与后续 Agent 检索和技能匹配。"
  },
  {
    label: "draft",
    meaning: "候选内容，通常由学习流程自动生成，需要人工审核后再启用。"
  },
  {
    label: "rejected",
    meaning: "不采纳，不应进入后续提示词或记忆召回。"
  },
  {
    label: "archived",
    meaning: "归档保留，默认不参与后续使用。"
  }
];

const commonIssues = [
  {
    problem: "论文问答没有返回有效内容",
    checks: [
      "确认论文库里该论文状态是已解析。",
      "确认论文详情页能看到章节内容。",
      "换一个更具体的问题，例如明确写 method、experiments 或 limitations。"
    ]
  },
  {
    problem: "技能没有被选中",
    checks: [
      "确认技能在分析技能页可见，且状态为 active。",
      "问题里加入技能相关触发词，例如 summary、method、experiments、novelty、limitations。",
      "到执行追踪里查看 SkillManager 的 select_skills 输出。"
    ]
  },
  {
    problem: "回答看起来缺少证据",
    checks: [
      "在问题里明确要求引用章节、图表、公式或实验表格。",
      "查看执行追踪里的反思校验 confidence 和 evidence_count。",
      "如果 PDF 解析质量差，重新上传更清晰的版本。"
    ]
  },
  {
    problem: "学习审核里出现很多 learned_skill",
    checks: [
      "这是系统从历史任务里自动提取的候选技能。",
      "先查看描述、触发词和模板，再决定批准或拒绝。",
      "不成熟的候选技能保持 draft 或 rejected，避免污染后续分析。"
    ]
  }
];

export default function ManualPage() {
  return (
    <div className="space-y-6">
      <PageHeader
        title="用户手册"
        description="按照从论文上传、检索问答、技能使用、学习审核到执行追踪的完整流程，帮助用户稳定使用 PaperHermes 完成论文分析。"
        icon={<CircleHelp />}
        action={
          <Link href="/papers/upload" className="inline-flex items-center gap-2 rounded-md bg-moss px-4 py-2 text-sm font-semibold text-white hover:bg-moss/90">
            <UploadCloud className="h-4 w-4" />
            开始上传论文
          </Link>
        }
      />

      <div className="grid gap-4 md:grid-cols-3">
        <StatCard label="推荐流程" value="4 步" icon={<CheckCircle2 />} tone="moss" />
        <StatCard label="核心模块" value={modules.length} icon={<Library />} tone="blue" />
        <StatCard label="技能触发词" value="{input}" icon={<Puzzle />} tone="rust" />
      </div>

      <Panel title="快速上手流程">
        <div className="grid gap-4 xl:grid-cols-4">
          {workflow.map((item, index) => (
            <section key={item.title} className="rounded-md border border-slate-200 bg-slate-50 p-4">
              <div className="mb-3 flex items-center gap-3">
                <span className="grid h-9 w-9 place-items-center rounded-md bg-moss/10 text-moss">
                  <item.icon className="h-4 w-4" />
                </span>
                <div>
                  <div className="text-xs font-semibold text-slate-500">第 {index + 1} 步</div>
                  <h2 className="text-sm font-semibold text-ink">{item.title}</h2>
                </div>
              </div>
              <ol className="space-y-2 text-sm leading-6 text-slate-700">
                {item.steps.map((step) => (
                  <li key={step} className="flex gap-2">
                    <span className="mt-2 h-1.5 w-1.5 shrink-0 rounded-full bg-moss" />
                    <span>{step}</span>
                  </li>
                ))}
              </ol>
              <p className="mt-3 border-t border-slate-200 pt-3 text-xs leading-5 text-slate-500">{item.note}</p>
              <Link href={item.href} className="mt-4 inline-flex text-sm font-semibold text-moss hover:text-moss/80">
                {item.action}
              </Link>
            </section>
          ))}
        </div>
      </Panel>

      <Panel title="功能模块说明">
        <div className="divide-y divide-slate-200">
          {modules.map((item) => (
            <div key={item.name} className="grid gap-3 py-4 first:pt-0 last:pb-0 lg:grid-cols-[220px_1fr]">
              <Link href={item.href} className="inline-flex items-center gap-3 text-sm font-semibold text-ink hover:text-moss">
                <span className="grid h-9 w-9 place-items-center rounded-md bg-slate-100 text-slate-600">
                  <item.icon className="h-4 w-4" />
                </span>
                {item.name}
              </Link>
              <div className="grid gap-2 md:grid-cols-2">
                <p className="text-sm leading-6 text-slate-700">
                  <span className="font-semibold text-ink">用途：</span>
                  {item.purpose}
                </p>
                <p className="text-sm leading-6 text-slate-700">
                  <span className="font-semibold text-ink">操作建议：</span>
                  {item.use}
                </p>
              </div>
            </div>
          ))}
        </div>
      </Panel>

      <div className="grid gap-6 xl:grid-cols-[1fr_1fr]">
        <Panel title="分析技能使用方式">
          <div className="space-y-4">
            <div className="rounded-md border border-amber-200 bg-amber-50 p-4 text-sm leading-6 text-amber-900">
              技能模板必须保留 <span className="font-semibold">{"{input}"}</span> 变量。论文问答时，系统会根据问题里的触发词选择 active 技能，并把技能模板作为回答策略传给 Agent。
            </div>
            <div className="divide-y divide-slate-200">
              {skillExamples.map((item) => (
                <div key={item.skill} className="py-3 first:pt-0 last:pb-0">
                  <div className="mb-2 flex flex-wrap items-center gap-2">
                    <span className="text-sm font-semibold text-ink">{item.intent}</span>
                    <StatusPill label={item.skill} tone="slate" />
                  </div>
                  <p className="rounded-md bg-slate-50 p-3 text-sm leading-6 text-slate-700">{item.prompt}</p>
                </div>
              ))}
            </div>
          </div>
        </Panel>

        <Panel title="学习审核与状态含义">
          <div className="space-y-4">
            <p className="text-sm leading-6 text-slate-700">
              系统会从高质量任务中提取候选记忆和候选技能。候选项不会天然可靠，建议在学习审核中查看来源任务、描述、触发词和模板后再批准。
            </p>
            <div className="divide-y divide-slate-200">
              {reviewItems.map((item) => (
                <div key={item.label} className="grid gap-2 py-3 first:pt-0 last:pb-0 md:grid-cols-[120px_1fr]">
                  <StatusPill label={item.label} tone={item.label === "active" ? "green" : item.label === "draft" ? "amber" : "slate"} />
                  <p className="text-sm leading-6 text-slate-700">{item.meaning}</p>
                </div>
              ))}
            </div>
            <Link href="/learning" className="inline-flex items-center gap-2 text-sm font-semibold text-moss hover:text-moss/80">
              <ListChecks className="h-4 w-4" />
              去学习审核
            </Link>
          </div>
        </Panel>
      </div>

      <Panel title="执行追踪怎么看">
        <div className="grid gap-4 lg:grid-cols-3">
          <TraceStep title="SkillManager / select_skills" description="查看本次问题匹配到了哪些技能。selected_count 大于 0 表示至少一个 active 技能参与了任务。" />
          <TraceStep title="分析 Agent" description="例如 MethodAgent、ExperimentReaderAgent、NoveltyAgent。这里展示具体分析输出，是回答生成的核心步骤。" />
          <TraceStep title="ReflectionAgent" description="检查回答是否有证据支撑。重点看 status、confidence、evidence_count 和 evaluate_execution 的反馈。" />
          <TraceStep title="LearningAgent" description="从本次任务中提取可复用经验，生成候选记忆、候选技能或工作流教训。" />
          <TraceStep title="record_skill_outcomes" description="记录被选中技能是否 helpful 或 needs_review。后续会影响技能统计和审核信号。" />
          <TraceStep title="create_skill_candidates" description="创建新的 draft 技能候选。候选技能需要进入学习审核确认，不建议无脑批准。" />
        </div>
      </Panel>

      <Panel title="常见问题排查">
        <div className="grid gap-4 xl:grid-cols-2">
          {commonIssues.map((item) => (
            <section key={item.problem} className="rounded-md border border-slate-200 bg-slate-50 p-4">
              <h2 className="mb-3 text-sm font-semibold text-ink">{item.problem}</h2>
              <ul className="space-y-2 text-sm leading-6 text-slate-700">
                {item.checks.map((check) => (
                  <li key={check} className="flex gap-2">
                    <CheckCircle2 className="mt-1 h-4 w-4 shrink-0 text-moss" />
                    <span>{check}</span>
                  </li>
                ))}
              </ul>
            </section>
          ))}
        </div>
      </Panel>
    </div>
  );
}

function TraceStep({ title, description }: { title: string; description: string }) {
  return (
    <section className="rounded-md border border-slate-200 bg-slate-50 p-4">
      <div className="mb-2 flex items-center gap-2 text-sm font-semibold text-ink">
        <FileText className="h-4 w-4 text-bluegray" />
        {title}
      </div>
      <p className="text-sm leading-6 text-slate-700">{description}</p>
    </section>
  );
}
