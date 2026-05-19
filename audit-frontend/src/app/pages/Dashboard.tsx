import { useQuery } from "@tanstack/react-query";
import { motion } from "motion/react";
import {
  Users,
  MessageSquare,
  AlertTriangle,
  Zap,
  Database,
  Server,
  Brain,
  Radio,
  Loader2,
  Circle,
} from "lucide-react";
import { getStatsOverview, getHealthOverview, getTokenStats, getAuditEvents } from "../api/admin";

export function Dashboard() {
  const { data: stats, isLoading: statsLoading } = useQuery({
    queryKey: ["admin-stats"],
    queryFn: getStatsOverview,
    refetchInterval: 10_000,
  });

  const { data: health, isLoading: healthLoading } = useQuery({
    queryKey: ["admin-health"],
    queryFn: getHealthOverview,
    refetchInterval: 10_000,
  });

  const { data: tokenStats, isLoading: tokenLoading } = useQuery({
    queryKey: ["admin-token-stats"],
    queryFn: () => getTokenStats(),
    refetchInterval: 15_000,
  });

  const { data: p0Events, isLoading: p0Loading } = useQuery({
    queryKey: ["admin-recent-errors"],
    queryFn: () => getAuditEvents({ level: "P0", page_size: "5" }),
    refetchInterval: 10_000,
  });

  const statCards = [
    {
      label: "总用户数",
      value: stats?.total_users ?? "-",
      icon: <Users size={20} className="text-indigo-500" />,
    },
    {
      label: "活跃讨论",
      value: stats?.active_discussions ?? "-",
      icon: <MessageSquare size={20} className="text-blue-500" />,
    },
    {
      label: "今日 P0 错误",
      value: stats?.p0_errors_today ?? "-",
      icon: <AlertTriangle size={20} className="text-red-500" />,
    },
    {
      label: "今日 API 调用",
      value: stats?.api_calls_today ?? "-",
      icon: <Zap size={20} className="text-amber-500" />,
    },
  ];

  const healthComponents = [
    { label: "数据库", key: "database", icon: <Database size={18} />, color: "text-emerald-500" },
    { label: "Redis", key: "redis", icon: <Server size={18} />, color: "text-orange-500" },
    { label: "LLM API", key: "llm_api", icon: <Brain size={18} />, color: "text-purple-500" },
  ];

  const allLoading = statsLoading && healthLoading && tokenLoading && p0Loading;

  return (
    <motion.div initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }} className="p-8 max-w-6xl mx-auto space-y-6">
      <h1 className="text-2xl font-bold text-slate-900">仪表盘</h1>

      {allLoading && !stats ? (
        <div className="flex items-center justify-center py-20">
          <Loader2 className="animate-spin text-indigo-400" size={28} />
        </div>
      ) : (
        <>
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-5">
            {statCards.map((card, i) => (
              <motion.div
                key={card.label}
                initial={{ opacity: 0, y: 12 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: i * 0.08 }}
                className="bg-white border border-slate-200 rounded-2xl p-5 shadow-sm"
              >
                <div className="flex items-center gap-4">
                  <div className="p-3 bg-slate-50 rounded-xl">{card.icon}</div>
                  <div>
                    <div className="text-2xl font-semibold text-slate-900">{card.value}</div>
                    <div className="text-sm font-medium text-slate-500">{card.label}</div>
                  </div>
                </div>
              </motion.div>
            ))}
          </div>

          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            <div className="bg-white border border-slate-200 rounded-2xl shadow-sm p-6">
              <h2 className="text-lg font-semibold text-slate-900 mb-4">系统组件状态</h2>
              {health ? (
                <div className="space-y-3">
                  {healthComponents.map((c) => {
                    const comp = health?.components?.[c.key];
                    const healthy = comp?.status === "healthy" || comp?.healthy;
                    return (
                      <div key={c.key} className="flex items-center justify-between py-2 px-3 bg-slate-50 rounded-xl">
                        <div className="flex items-center gap-3">
                          <span className={c.color}>{c.icon}</span>
                          <span className="text-sm font-medium text-slate-700">{c.label}</span>
                        </div>
                        <div className="flex items-center gap-3">
                          {comp?.latency_ms !== undefined && (
                            <span className="text-xs text-slate-400">{comp.latency_ms}ms</span>
                          )}
                          <span className={`flex items-center gap-1.5 text-xs font-medium ${healthy ? "text-emerald-600" : "text-red-600"}`}>
                            <Circle size={8} fill="currentColor" className={healthy ? "text-emerald-500" : "text-red-500"} />
                            {healthy ? "正常" : "异常"}
                          </span>
                        </div>
                      </div>
                    );
                  })}
                </div>
              ) : (
                <div className="text-center py-8 text-slate-400 text-sm">暂无数据</div>
              )}
            </div>

            <div className="bg-white border border-slate-200 rounded-2xl shadow-sm p-6">
              <h2 className="text-lg font-semibold text-slate-900 mb-4">今日 Token 用量</h2>
              {tokenStats ? (
                <div className="space-y-4">
                  <div className="flex items-center justify-between py-2 px-3 bg-slate-50 rounded-xl">
                    <span className="text-sm text-slate-600">讨论 Token</span>
                    <span className="text-sm font-semibold text-slate-900">
                      {tokenStats.discussion_tokens?.toLocaleString?.() ?? tokenStats.discussion_tokens ?? "-"}
                    </span>
                  </div>
                  <div className="flex items-center justify-between py-2 px-3 bg-slate-50 rounded-xl">
                    <span className="text-sm text-slate-600">角色生成 Token</span>
                    <span className="text-sm font-semibold text-slate-900">
                      {tokenStats.character_tokens?.toLocaleString?.() ?? tokenStats.character_tokens ?? "-"}
                    </span>
                  </div>
                  <div className="flex items-center justify-between py-2 px-3 bg-slate-50 rounded-xl">
                    <span className="text-sm text-slate-600">其他 Token</span>
                    <span className="text-sm font-semibold text-slate-900">
                      {tokenStats.other_tokens?.toLocaleString?.() ?? tokenStats.other_tokens ?? "-"}
                    </span>
                  </div>
                  {tokenStats.total_tokens !== undefined && (
                    <div className="flex items-center justify-between py-2 px-3 bg-indigo-50 rounded-xl border border-indigo-100">
                      <span className="text-sm font-medium text-indigo-700">合计</span>
                      <span className="text-sm font-bold text-indigo-700">
                        {tokenStats.total_tokens?.toLocaleString?.() ?? tokenStats.total_tokens}
                      </span>
                    </div>
                  )}
                </div>
              ) : (
                <div className="text-center py-8 text-slate-400 text-sm">暂无数据</div>
              )}
            </div>
          </div>

          <div className="bg-white border border-slate-200 rounded-2xl shadow-sm overflow-hidden">
            <div className="px-6 py-4 border-b border-slate-100">
              <h2 className="text-lg font-semibold text-slate-900">最近系统错误 (P0)</h2>
            </div>
            {p0Events?.items?.length > 0 || p0Events?.length > 0 ? (
              <div className="divide-y divide-slate-100">
                {(p0Events?.items || p0Events || []).slice(0, 5).map((evt: any, i: number) => (
                  <div key={evt.id || i} className="px-6 py-4 flex items-center justify-between">
                    <div className="flex items-center gap-3 min-w-0">
                      <AlertTriangle size={16} className="text-red-400 shrink-0" />
                      <div className="min-w-0">
                        <span className="text-sm font-medium text-slate-700 truncate block">{evt.event_type}</span>
                        <span className="text-xs text-slate-400 truncate block">
                          {evt.payload?.error || evt.payload?.message || JSON.stringify(evt.payload || {}).slice(0, 100)}
                        </span>
                      </div>
                    </div>
                    <span className="text-xs text-slate-400 shrink-0 ml-4">
                      {new Date(evt.created_at).toLocaleString("zh-CN")}
                    </span>
                  </div>
                ))}
              </div>
            ) : (
              <div className="p-12 text-center text-slate-400 text-sm">暂无 P0 错误，系统运行正常</div>
            )}
          </div>
        </>
      )}
    </motion.div>
  );
}
