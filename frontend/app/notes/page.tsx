import Link from "next/link";
import { BookOpen, FileText, MessageSquare, Sparkles } from "lucide-react";
import { PageHeader, StatCard, StatusPill } from "@/components/PageChrome";
import { Panel } from "@/components/Panel";

const noteSections = ["论文背景", "核心方法", "实验设计", "关键结论", "局限与后续问题"];

export default function NotesPage() {
  return (
    <div className="space-y-6">
      <PageHeader
        title="阅读笔记"
        description="阅读笔记能力由论文分析接口和技能模板共同支撑。当前页面提供笔记结构和操作入口，生成内容时请先进入论文问答或论文详情页。"
        icon={<BookOpen />}
        action={
          <Link href="/chat" className="inline-flex items-center gap-2 rounded-md bg-moss px-4 py-2 text-sm font-semibold text-white">
            <MessageSquare className="h-4 w-4" />
            进入论文问答
          </Link>
        }
      />

      <div className="grid gap-4 md:grid-cols-3">
        <StatCard label="笔记结构" value="5 段" icon={<BookOpen />} tone="moss" />
        <StatCard label="内容来源" value="论文证据" icon={<FileText />} tone="blue" />
        <StatCard label="生成方式" value="Agent 分析" icon={<Sparkles />} tone="rust" />
      </div>

      <div className="grid gap-6 xl:grid-cols-[0.9fr_1.1fr]">
        <Panel title="推荐笔记结构">
          <div className="space-y-3">
            {noteSections.map((section, index) => (
              <div key={section} className="flex items-center gap-3 rounded-lg border border-slate-200 bg-slate-50 p-3">
                <span className="grid h-8 w-8 place-items-center rounded-md bg-white text-sm font-semibold text-moss shadow-sm">{index + 1}</span>
                <span className="font-medium text-ink">{section}</span>
              </div>
            ))}
          </div>
        </Panel>

        <Panel title="落地方式" action={<StatusPill label="待接入独立笔记接口" tone="amber" />}>
          <div className="space-y-4 text-sm leading-6 text-slate-700">
            <p>目前项目已经具备论文上传、检索问答、分析技能和执行追踪能力。阅读笔记可以先通过论文问答生成，再结合研究记忆保存个人偏好。</p>
            <div className="rounded-lg border border-slate-200 bg-slate-50 p-4">
              <div className="font-semibold text-ink">建议提问模板</div>
              <p className="mt-2 text-slate-600">请基于论文上下文生成结构化阅读笔记，包含背景、方法、实验、结论、局限性，并给出依据。</p>
            </div>
            <div className="flex flex-wrap gap-3">
              <Link href="/papers" className="rounded-md border border-slate-300 px-4 py-2 font-semibold text-slate-700 hover:bg-white">
                选择论文
              </Link>
              <Link href="/skills" className="rounded-md border border-slate-300 px-4 py-2 font-semibold text-slate-700 hover:bg-white">
                配置技能模板
              </Link>
            </div>
          </div>
        </Panel>
      </div>
    </div>
  );
}
