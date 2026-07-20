import Link from "next/link";
import { BookOpen, FileText, MessageSquare } from "lucide-react";
import { EmptyState, PageHeader, StatCard, StatusPill } from "@/components/PageChrome";
import { Panel } from "@/components/Panel";
import { resolveApiBase } from "@/lib/api";

type PaperDetail = {
  id: string;
  title?: string;
  authors?: string[];
  abstract?: string;
  original_filename?: string;
  status?: string;
  sections?: { id: string; title: string; content: string }[];
};

async function getPaper(id: string): Promise<PaperDetail | null> {
  const response = await fetch(`${resolveApiBase()}/papers/${id}`, { cache: "no-store" });
  if (!response.ok) return null;
  return response.json();
}

export default async function PaperDetailPage({ params }: { params: { paper_id: string } }) {
  const paper = await getPaper(params.paper_id);

  if (!paper) {
    return <EmptyState title="未找到论文" description="论文不存在，或后端服务当前不可用。" icon={<FileText />} />;
  }

  const title = paper.title || paper.original_filename || "未命名论文";
  const sections = paper.sections || [];

  return (
    <div className="space-y-6">
      <PageHeader
        title={title}
        description={(paper.authors || []).join(", ") || paper.original_filename || "作者信息待补充"}
        icon={<FileText />}
        action={
          <Link href="/chat" className="inline-flex items-center gap-2 rounded-md bg-moss px-4 py-2 text-sm font-semibold text-white">
            <MessageSquare className="h-4 w-4" />
            去提问
          </Link>
        }
      />

      <div className="grid gap-4 md:grid-cols-3">
        <StatCard label="解析状态" value={paper.status === "parsed" ? "已解析" : paper.status || "未知"} icon={<BookOpen />} tone="moss" />
        <StatCard label="章节数量" value={sections.length} icon={<FileText />} tone="blue" />
        <StatCard label="论文编号" value={paper.id.slice(0, 8)} icon={<FileText />} tone="rust" />
      </div>

      <Panel title="摘要" action={<StatusPill label={paper.abstract ? "已抽取" : "待补充"} tone={paper.abstract ? "green" : "amber"} />}>
        <p className="text-sm leading-7 text-slate-700">{paper.abstract || "暂未抽取到摘要。"}</p>
      </Panel>

      <Panel title="章节内容">
        {sections.length === 0 ? (
          <EmptyState title="暂无章节内容" description="如果论文已上传但没有章节，请检查 PDF 解析结果或重新上传。" icon={<BookOpen />} />
        ) : (
          <div className="space-y-3">
            {sections.map((section, index) => (
              <details key={section.id || `${section.title}-${index}`} className="rounded-lg border border-slate-200 bg-slate-50 p-4 open:bg-white">
                <summary className="cursor-pointer text-sm font-semibold text-ink">
                  {index + 1}. {section.title || "未命名章节"}
                </summary>
                <p className="mt-3 line-clamp-6 text-sm leading-7 text-slate-700">{section.content}</p>
              </details>
            ))}
          </div>
        )}
      </Panel>
    </div>
  );
}
