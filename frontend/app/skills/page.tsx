"use client";

import { useEffect, useState } from "react";
import { Plus, Puzzle, Sparkles, Wrench } from "lucide-react";
import { EmptyState, PageHeader, StatCard, StatusPill } from "@/components/PageChrome";
import { Panel } from "@/components/Panel";
import { Skill, api } from "@/lib/api";

export default function SkillsPage() {
  const [skills, setSkills] = useState<Skill[]>([]);
  const [name, setName] = useState("paper_summary");
  const [template, setTemplate] = useState("Summarize this paper input: {input}");
  const [isSaving, setIsSaving] = useState(false);

  async function refresh() {
    try {
      setSkills(await api.skills("active"));
    } catch {
      setSkills([]);
    }
  }

  async function create() {
    if (!name.trim() || !template.trim()) return;
    setIsSaving(true);
    try {
      await api.createSkill({ name: name.trim(), description: "Reusable paper reading workflow", prompt_template: template.trim() });
      await refresh();
    } finally {
      setIsSaving(false);
    }
  }

  useEffect(() => {
    refresh();
  }, []);

  const totalUsage = skills.reduce((total, skill) => total + skill.usage_count, 0);

  return (
    <div className="space-y-6">
      <PageHeader
        title="分析技能"
        description="把常用论文阅读提示词沉淀成技能模板，后续可以复用到总结、方法分析、实验解读等流程。"
        icon={<Puzzle />}
      />

      <div className="grid gap-4 md:grid-cols-3">
        <StatCard label="技能数量" value={skills.length} icon={<Puzzle />} tone="moss" />
        <StatCard label="累计使用" value={totalUsage} icon={<Sparkles />} tone="blue" />
        <StatCard label="模板变量" value="{input}" icon={<Wrench />} tone="rust" />
      </div>

      <div className="grid gap-6 xl:grid-cols-[0.9fr_1.1fr]">
        <Panel title="创建技能">
          <div className="space-y-4">
            <div>
              <label className="mb-2 block text-sm font-semibold text-ink">技能名称</label>
              <input
                className="w-full rounded-md border border-slate-300 px-3 py-2 text-sm outline-none focus:border-moss"
                value={name}
                onChange={(event) => setName(event.target.value)}
                placeholder="paper_summary"
              />
            </div>
            <div>
              <label className="mb-2 block text-sm font-semibold text-ink">提示词模板</label>
              <textarea
                className="min-h-40 w-full rounded-md border border-slate-300 px-3 py-2 text-sm leading-6 outline-none focus:border-moss"
                value={template}
                onChange={(event) => setTemplate(event.target.value)}
                placeholder="请基于输入内容完成论文分析：{input}"
              />
            </div>
            <button
              onClick={create}
              disabled={!name.trim() || !template.trim() || isSaving}
              className="inline-flex items-center justify-center gap-2 rounded-md bg-moss px-4 py-2 text-sm font-semibold text-white disabled:cursor-not-allowed disabled:bg-slate-400"
            >
              <Plus className="h-4 w-4" />
              {isSaving ? "创建中" : "创建技能"}
            </button>
          </div>
        </Panel>

        <Panel title="技能库">
          {skills.length === 0 ? (
            <EmptyState title="暂无技能模板" description="创建一个技能后，可以在这里查看模板和使用次数。" icon={<Puzzle />} />
          ) : (
            <div className="grid gap-3 md:grid-cols-2">
              {skills.map((skill) => (
                <article key={skill.id} className="rounded-lg border border-slate-200 bg-slate-50 p-4">
                  <div className="mb-3 flex items-start justify-between gap-3">
                    <div className="min-w-0">
                      <div className="flex items-center gap-2 font-semibold text-ink">
                        <Puzzle className="h-4 w-4 text-rust" />
                        <span className="truncate">{skill.name}</span>
                      </div>
                      <p className="mt-2 text-sm leading-6 text-slate-600">{skill.description || "论文分析技能模板"}</p>
                    </div>
                    <StatusPill label={`${skill.usage_count} 次`} />
                  </div>
                  <div className="line-clamp-4 rounded-md bg-white p-3 text-xs leading-5 text-slate-600">{skill.prompt_template}</div>
                </article>
              ))}
            </div>
          )}
        </Panel>
      </div>
    </div>
  );
}
