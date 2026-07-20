"use client";

import { useCallback, useEffect, useState } from "react";
import { Activity, BrainCircuit, RefreshCw, Scale, TrendingUp } from "lucide-react";
import { Panel } from "@/components/Panel";
import { PageHeader, StatCard, StatusPill } from "@/components/PageChrome";
import { PolicyReplay, PolicySummary, RewardSummary, api } from "@/lib/api";

const actionLabels: Record<string, string> = {
  economy: "经济策略",
  balanced: "均衡策略",
  deep: "深度策略"
};

export default function PolicyPage() {
  const [summary, setSummary] = useState<PolicySummary | null>(null);
  const [rewards, setRewards] = useState<RewardSummary | null>(null);
  const [replay, setReplay] = useState<PolicyReplay | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  const load = useCallback(async () => {
    setLoading(true);
    setError("");
    try {
      const [policyResult, rewardResult] = await Promise.all([api.policySummary(), api.rewardSummary()]);
      setSummary(policyResult);
      setRewards(rewardResult);
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "策略指标加载失败");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    load();
  }, [load]);

  async function runReplay() {
    setLoading(true);
    setError("");
    try {
      setReplay(await api.replayPolicy());
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "离线回放失败");
    } finally {
      setLoading(false);
    }
  }

  const maximumCount = Math.max(...Object.values(summary?.counts ?? {}), 1);

  return (
    <div className="space-y-6">
      <PageHeader
        title="策略学习"
        description="查看 Contextual Bandit 的探索、策略分布、Reward 与离线反事实回放。每次决策都可通过任务追踪审计。"
        icon={<TrendingUp />}
        action={
          <button onClick={load} disabled={loading} className="inline-flex items-center gap-2 rounded-md border border-slate-300 bg-white px-3 py-2 text-sm font-semibold text-slate-700 disabled:opacity-50">
            <RefreshCw className={`h-4 w-4 ${loading ? "animate-spin" : ""}`} />
            刷新
          </button>
        }
      />

      <div className="grid gap-4 md:grid-cols-4">
        <StatCard label="当前策略" value={summary?.policy_name ?? "-"} icon={<BrainCircuit />} tone="moss" />
        <StatCard label="策略更新" value={summary?.total_updates ?? 0} icon={<Activity />} tone="blue" />
        <StatCard label="人工反馈" value={rewards?.feedback_count ?? 0} icon={<Scale />} tone="rust" />
        <StatCard label="最终 Reward" value={(rewards?.average_final_reward ?? 0).toFixed(3)} icon={<TrendingUp />} tone="slate" />
      </div>

      {error ? <div className="rounded-md border border-red-200 bg-red-50 p-3 text-sm text-red-700">{error}</div> : null}

      <div className="grid gap-6 xl:grid-cols-2">
        <Panel title="Action 分布" action={<StatusPill label={summary?.policy_version ?? "等待数据"} tone="green" />}>
          <div className="space-y-5">
            {(summary?.actions ?? ["economy", "balanced", "deep"]).map((action) => {
              const count = summary?.counts[action] ?? 0;
              const width = `${Math.max((count / maximumCount) * 100, count ? 4 : 0)}%`;
              return (
                <div key={action}>
                  <div className="mb-2 flex justify-between text-sm">
                    <span className="font-semibold text-ink">{actionLabels[action] ?? action}</span>
                    <span className="text-slate-500">{count} 次 · Reward {(summary?.average_reward_by_action[action] ?? 0).toFixed(3)}</span>
                  </div>
                  <div className="h-2 rounded-full bg-slate-100"><div className="h-2 rounded-full bg-moss" style={{ width }} /></div>
                </div>
              );
            })}
          </div>
        </Panel>

        <Panel title="离线策略回放" action={<button onClick={runReplay} disabled={loading} className="rounded-md bg-moss px-3 py-2 text-xs font-semibold text-white disabled:bg-slate-400">运行 IPS 回放</button>}>
          {replay ? (
            <div className="space-y-3">
              {Object.entries(replay.policies).map(([name, result]) => (
                <div key={name} className="flex items-center justify-between rounded-md border border-slate-200 bg-slate-50 p-3 text-sm">
                  <span className="font-semibold text-ink">{name}</span>
                  <span className="text-slate-600">Reward {result.estimated_reward.toFixed(3)} · 样本 {result.matched_samples}</span>
                </div>
              ))}
              <div className="text-xs leading-5 text-slate-500">累计遗憾：{replay.cumulative_regret.toFixed(3)}。{replay.warning}</div>
            </div>
          ) : <p className="text-sm leading-6 text-slate-500">运行 capped inverse propensity scoring，对比固定、随机和日志策略。探索样本不足时结果仅用于诊断。</p>}
        </Panel>
      </div>
    </div>
  );
}
