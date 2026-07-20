import Link from "next/link";
import { FileText, Layers3, Library, Network } from "lucide-react";
import { PageHeader, StatCard, StatusPill } from "@/components/PageChrome";
import { Panel } from "@/components/Panel";

const workflow = [
  { title: "收集论文", desc: "先把需要比较的论文上传到论文库。" },
  { title: "逐篇分析", desc: "通过论文问答或详情分析提取方法、实验、贡献和局限。" },
  { title: "组织综述", desc: "按研究脉络、技术路线或任务场景聚类形成相关工作草稿。" }
];

export default function RelatedWorkPage() {
  return (
    <div className="space-y-6">
      <PageHeader
        title="相关工作"
        description="相关工作写作需要多论文对比。当前页面先提供工程化流程入口，后续可以在此接入批量检索、聚类和综述生成。"
        icon={<Network />}
        action={
          <Link href="/papers" className="inline-flex items-center gap-2 rounded-md bg-moss px-4 py-2 text-sm font-semibold text-white">
            <Library className="h-4 w-4" />
            查看论文库
          </Link>
        }
      />

      <div className="grid gap-4 md:grid-cols-3">
        <StatCard label="输入材料" value="多篇论文" icon={<FileText />} tone="moss" />
        <StatCard label="组织方式" value="主题聚类" icon={<Layers3 />} tone="blue" />
        <StatCard label="输出目标" value="综述草稿" icon={<Network />} tone="rust" />
      </div>

      <div className="grid gap-6 xl:grid-cols-[1.1fr_0.9fr]">
        <Panel title="工作流">
          <div className="space-y-3">
            {workflow.map((item, index) => (
              <div key={item.title} className="rounded-lg border border-slate-200 bg-slate-50 p-4">
                <div className="flex items-center gap-3">
                  <span className="grid h-8 w-8 place-items-center rounded-md bg-white text-sm font-semibold text-moss shadow-sm">{index + 1}</span>
                  <div>
                    <div className="font-semibold text-ink">{item.title}</div>
                    <div className="mt-1 text-sm text-slate-600">{item.desc}</div>
                  </div>
                </div>
              </div>
            ))}
          </div>
        </Panel>

        <Panel title="当前状态" action={<StatusPill label="规划中" tone="amber" />}>
          <div className="space-y-4 text-sm leading-6 text-slate-700">
            <p>项目目前已经有单篇论文分析和技能模板管理。要形成工程级相关工作模块，下一步需要接入多论文选择、批量摘要和主题归并。</p>
            <div className="rounded-lg border border-slate-200 bg-slate-50 p-4">
              <div className="font-semibold text-ink">可先使用的替代流程</div>
              <p className="mt-2 text-slate-600">在论文库中逐篇查看论文，使用论文问答提取贡献和局限，再把结果汇总为相关工作段落。</p>
            </div>
            <Link href="/chat" className="inline-flex items-center gap-2 rounded-md border border-slate-300 px-4 py-2 font-semibold text-slate-700 hover:bg-white">
              进入论文问答
            </Link>
          </div>
        </Panel>
      </div>
    </div>
  );
}
