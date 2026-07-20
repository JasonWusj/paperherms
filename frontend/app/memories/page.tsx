"use client";

import { useEffect, useState } from "react";
import { BrainCircuit, Clock3, Plus, Save } from "lucide-react";
import { EmptyState, PageHeader, StatCard, StatusPill } from "@/components/PageChrome";
import { Panel } from "@/components/Panel";
import { Memory, api } from "@/lib/api";

function memoryTypeLabel(type: string) {
  return type === "research_preference" ? "研究偏好" : type;
}

export default function MemoriesPage() {
  const [memories, setMemories] = useState<Memory[]>([]);
  const [content, setContent] = useState("");
  const [isSaving, setIsSaving] = useState(false);

  async function refresh() {
    try {
      setMemories(await api.memories());
    } catch {
      setMemories([]);
    }
  }

  async function create() {
    const trimmed = content.trim();
    if (!trimmed) return;
    setIsSaving(true);
    try {
      await api.createMemory({ user_id: "default", memory_type: "research_preference", content: trimmed });
      setContent("");
      await refresh();
    } finally {
      setIsSaving(false);
    }
  }

  useEffect(() => {
    refresh();
  }, []);

  return (
    <div className="space-y-6">
      <PageHeader
        title="研究记忆"
        description="记录长期偏好、阅读习惯和可复用上下文。后续分析论文时，可以把这些偏好作为个性化输入。"
        icon={<BrainCircuit />}
      />

      <div className="grid gap-4 md:grid-cols-3">
        <StatCard label="记忆条目" value={memories.length} icon={<BrainCircuit />} tone="moss" />
        <StatCard label="默认用户" value="default" icon={<Save />} tone="blue" />
        <StatCard label="当前类型" value="研究偏好" icon={<Clock3 />} tone="rust" />
      </div>

      <div className="grid gap-6 xl:grid-cols-[0.9fr_1.1fr]">
        <Panel title="写入记忆">
          <div className="space-y-4">
            <textarea
              className="min-h-36 w-full rounded-md border border-slate-300 px-3 py-2 text-sm leading-6 outline-none focus:border-moss"
              value={content}
              onChange={(event) => setContent(event.target.value)}
              placeholder="例如：优先用中文回答；总结论文时先讲方法，再讲实验和局限性；回答中标注依据。"
            />
            <div className="flex flex-col gap-3 md:flex-row md:items-center md:justify-between">
              <span className="text-xs text-slate-500">当前会以“研究偏好”类型保存。</span>
              <button
                onClick={create}
                disabled={!content.trim() || isSaving}
                className="inline-flex items-center justify-center gap-2 rounded-md bg-moss px-4 py-2 text-sm font-semibold text-white disabled:cursor-not-allowed disabled:bg-slate-400"
              >
                <Plus className="h-4 w-4" />
                {isSaving ? "保存中" : "保存记忆"}
              </button>
            </div>
          </div>
        </Panel>

        <Panel title="已保存记忆">
          {memories.length === 0 ? (
            <EmptyState title="暂无研究记忆" description="写入一条偏好后，它会出现在这里，便于后续复用。" icon={<BrainCircuit />} />
          ) : (
            <div className="space-y-3">
              {memories.map((memory) => (
                <article key={memory.id} className="rounded-lg border border-slate-200 bg-slate-50 p-4">
                  <div className="mb-2 flex flex-wrap items-center justify-between gap-2">
                    <div className="flex items-center gap-2 font-semibold text-ink">
                      <BrainCircuit className="h-4 w-4 text-moss" />
                      {memoryTypeLabel(memory.memory_type)}
                    </div>
                    <StatusPill label={memory.created_at ? new Date(memory.created_at).toLocaleDateString("zh-CN") : "已保存"} />
                  </div>
                  <p className="whitespace-pre-wrap text-sm leading-6 text-slate-700">{memory.content}</p>
                </article>
              ))}
            </div>
          )}
        </Panel>
      </div>
    </div>
  );
}
