"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { FileText, MessageSquare, Search, Send } from "lucide-react";
import { EmptyState, PageHeader, StatCard, StatusPill } from "@/components/PageChrome";
import { Panel } from "@/components/Panel";
import { Paper, api } from "@/lib/api";

function paperLabel(paper: Paper) {
  return paper.title || paper.original_filename || paper.id;
}

export default function ChatPage() {
  const [paperId, setPaperId] = useState("");
  const [papers, setPapers] = useState<Paper[]>([]);
  const [isLoadingPapers, setIsLoadingPapers] = useState(true);
  const [paperError, setPaperError] = useState("");
  const [question, setQuestion] = useState("");
  const [answer, setAnswer] = useState("");
  const [traceId, setTraceId] = useState("");
  const [isAsking, setIsAsking] = useState(false);
  const selectedPaper = papers.find((paper) => paper.id === paperId);
  const canAsk = Boolean(paperId && question.trim() && !isAsking);

  useEffect(() => {
    let isMounted = true;

    async function loadPapers() {
      try {
        const result = await api.papers();
        if (!isMounted) return;
        setPapers(result);
        setPaperId((currentPaperId) => currentPaperId || result[0]?.id || "");
      } catch (error) {
        if (!isMounted) return;
        setPaperError(error instanceof Error ? error.message : "论文列表加载失败");
      } finally {
        if (isMounted) setIsLoadingPapers(false);
      }
    }

    loadPapers();

    return () => {
      isMounted = false;
    };
  }, []);

  async function ask() {
    if (!canAsk) return;

    setIsAsking(true);
    setTraceId("");
    setAnswer("正在检索论文证据并调用分析 Agent...");
    try {
      const result = await api.askPaper(paperId, question);
      setTraceId(result.task_id);
      setAnswer(result.answer);
    } catch (error) {
      setAnswer(error instanceof Error ? error.message : "请求失败");
    } finally {
      setIsAsking(false);
    }
  }

  return (
    <div className="space-y-6">
      <PageHeader
        title="论文问答"
        description="选择一篇已索引论文，围绕方法、实验、局限性或结论提问。系统会先检索原文证据，再调用分析 Agent 生成回答。"
        icon={<MessageSquare />}
      />

      <div className="grid gap-4 md:grid-cols-3">
        <StatCard label="可问答论文" value={papers.length} icon={<FileText />} tone="moss" />
        <StatCard label="当前状态" value={isAsking ? "生成中" : "待提问"} icon={<Search />} tone="blue" />
        <StatCard label="证据来源" value="论文上下文" icon={<MessageSquare />} tone="rust" />
      </div>

      {papers.length === 0 && !isLoadingPapers ? (
        <EmptyState
          title="还没有可问答的论文"
          description="请先上传 PDF 并等待解析索引完成，然后回到这里选择论文提问。"
          icon={<FileText />}
          action={
            <Link href="/papers/upload" className="rounded-md bg-moss px-4 py-2 text-sm font-semibold text-white">
              上传论文
            </Link>
          }
        />
      ) : (
        <div className="grid gap-6 xl:grid-cols-[0.9fr_1.1fr]">
          <Panel title="提问区">
            <div className="space-y-4">
              <div>
                <label className="mb-2 block text-sm font-semibold text-ink">选择论文</label>
                <select
                  value={paperId}
                  onChange={(event) => setPaperId(event.target.value)}
                  disabled={isLoadingPapers || papers.length === 0}
                  className="w-full rounded-md border border-slate-300 bg-white px-3 py-2 text-sm outline-none focus:border-moss disabled:cursor-not-allowed disabled:bg-slate-100 disabled:text-slate-500"
                >
                  {isLoadingPapers ? <option>正在加载论文...</option> : null}
                  {papers.map((paper) => (
                    <option key={paper.id} value={paper.id}>
                      {paperLabel(paper)}
                    </option>
                  ))}
                </select>
                {selectedPaper ? (
                  <div className="mt-3 rounded-md border border-slate-200 bg-slate-50 p-3 text-xs text-slate-600">
                    <div className="font-semibold text-ink">{paperLabel(selectedPaper)}</div>
                    <div className="mt-1">追踪编号前缀：{selectedPaper.id.slice(0, 8)}</div>
                  </div>
                ) : null}
                {paperError ? <p className="mt-2 text-sm text-rust">{paperError}</p> : null}
              </div>

              <div>
                <label className="mb-2 block text-sm font-semibold text-ink">问题</label>
                <textarea
                  value={question}
                  onChange={(event) => setQuestion(event.target.value)}
                  placeholder="例如：请用中文总结这篇论文的主要方法，并说明依据来自哪些上下文。"
                  className="min-h-40 w-full rounded-md border border-slate-300 px-3 py-2 text-sm leading-6 outline-none focus:border-moss"
                />
              </div>

              <button
                onClick={ask}
                disabled={!canAsk}
                className="inline-flex w-full items-center justify-center gap-2 rounded-md bg-moss px-4 py-2.5 text-sm font-semibold text-white disabled:cursor-not-allowed disabled:bg-slate-400 md:w-auto"
              >
                <Send className="h-4 w-4" />
                {isAsking ? "正在生成" : "开始问答"}
              </button>
            </div>
          </Panel>

          <Panel
            title="回答结果"
            action={traceId ? <StatusPill label={`追踪编号 ${traceId.slice(0, 8)}`} tone="green" /> : <StatusPill label="等待回答" />}
          >
            <div className="min-h-80 rounded-lg border border-slate-200 bg-slate-50 p-4">
              <pre className="whitespace-pre-wrap break-words text-sm leading-7 text-slate-700">{answer || "暂无回答。"}</pre>
            </div>
            {traceId ? (
              <div className="mt-4 flex justify-end">
                <Link href="/traces" className="inline-flex items-center gap-2 text-sm font-semibold text-moss hover:text-moss/80">
                  查看执行追踪
                  <Search className="h-4 w-4" />
                </Link>
              </div>
            ) : null}
          </Panel>
        </div>
      )}
    </div>
  );
}
