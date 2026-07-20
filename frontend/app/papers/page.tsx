import Link from "next/link";
import { CheckCircle2, FileText, Library, UploadCloud } from "lucide-react";
import { EmptyState, PageHeader, StatCard, StatusPill } from "@/components/PageChrome";
import { Panel } from "@/components/Panel";
import { Paper, api } from "@/lib/api";

function paperTitle(paper: Paper) {
  return paper.title || paper.original_filename || "未命名论文";
}

function statusLabel(status: string) {
  return status === "parsed" ? "已解析" : status || "待处理";
}

export default async function PapersPage() {
  let papers: Paper[] = [];
  try {
    papers = await api.papers();
  } catch {
    papers = [];
  }

  const parsedCount = papers.filter((paper) => paper.status === "parsed").length;
  const authorCount = new Set(papers.flatMap((paper) => paper.authors || []).filter(Boolean)).size;

  return (
    <div className="space-y-6">
      <PageHeader
        title="论文库"
        description="集中管理已经上传、解析和索引的论文资产。进入详情页可以查看摘要、章节结构，并继续发起问答或分析。"
        icon={<Library />}
        action={
          <Link href="/papers/upload" className="inline-flex items-center gap-2 rounded-md bg-moss px-4 py-2 text-sm font-semibold text-white hover:bg-moss/90">
            <UploadCloud className="h-4 w-4" />
            上传论文
          </Link>
        }
      />

      <div className="grid gap-4 md:grid-cols-3">
        <StatCard label="入库论文" value={papers.length} icon={<FileText />} tone="moss" />
        <StatCard label="完成索引" value={parsedCount} icon={<CheckCircle2 />} tone="blue" />
        <StatCard label="作者覆盖" value={authorCount} icon={<Library />} tone="rust" />
      </div>

      <Panel title="论文资产列表">
        {papers.length === 0 ? (
          <EmptyState
            title="还没有论文资产"
            description="先上传一份 PDF，系统会自动解析正文、抽取章节并写入向量索引。"
            icon={<FileText />}
            action={
              <Link href="/papers/upload" className="inline-flex items-center gap-2 rounded-md bg-moss px-4 py-2 text-sm font-semibold text-white">
                <UploadCloud className="h-4 w-4" />
                上传第一篇论文
              </Link>
            }
          />
        ) : (
          <div className="grid gap-3 xl:grid-cols-2">
            {papers.map((paper) => (
              <Link
                href={`/papers/${paper.id}`}
                key={paper.id}
                className="group rounded-lg border border-slate-200 bg-slate-50/60 p-4 transition hover:border-moss/40 hover:bg-white hover:shadow-sm"
              >
                <div className="flex items-start justify-between gap-4">
                  <div className="min-w-0">
                    <div className="line-clamp-2 text-base font-semibold text-ink group-hover:text-moss">{paperTitle(paper)}</div>
                    <div className="mt-2 line-clamp-1 text-sm text-slate-600">
                      {(paper.authors || []).join(", ") || paper.original_filename || "作者信息待补充"}
                    </div>
                  </div>
                  <StatusPill label={statusLabel(paper.status)} tone={paper.status === "parsed" ? "green" : "amber"} />
                </div>
                <div className="mt-4 flex flex-wrap items-center gap-3 text-xs text-slate-500">
                  <span>编号 {paper.id.slice(0, 8)}</span>
                  {paper.created_at ? <span>入库 {new Date(paper.created_at).toLocaleDateString("zh-CN")}</span> : null}
                </div>
              </Link>
            ))}
          </div>
        )}
      </Panel>
    </div>
  );
}
