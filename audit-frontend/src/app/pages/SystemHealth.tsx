import { useQuery } from "@tanstack/react-query";
import { motion } from "motion/react";
import {
  Database,
  Server,
  Brain,
  Circle,
  Loader2,
  AlertTriangle,
  Cpu,
  HardDrive,
  Activity,
  Users,
  ChevronDown,
  ChevronUp,
} from "lucide-react";
import { getHealthOverview, getHealthErrors, getHealthLoad, getOrphanDiscussions } from "../api/admin";
import { useState } from "react";

export function SystemHealth() {
  const [expandedErrors, setExpandedErrors] = useState<Set<number>>(new Set());

  const { data: health, isLoading: hLoading } = useQuery({
    queryKey: ["admin-health"],
    queryFn: getHealthOverview,
    refetchInterval: 10_000,
  });

  const { data: errors, isLoading: eLoading } = useQuery({
    queryKey: ["admin-health-errors"],
    queryFn: () => getHealthErrors({ page_size: "20" }),
    refetchInterval: 15_000,
  });

  const { data: load, isLoading: lLoading } = useQuery({
    queryKey: ["admin-health-load"],
    queryFn: getHealthLoad,
    refetchInterval: 10_000,
  });

  const { data: orphans, isLoading: oLoading } = useQuery({
    queryKey: ["admin-orphans"],
    queryFn: getOrphanDiscussions,
    refetchInterval: 30_000,
  });

  const healthComponents = [
    { label: "数据库", key: "database", icon: <Database size={20} />, color: "text-emerald-500" },
    { label: "Redis", key: "redis", icon: <Server size={20} />, color: "text-orange-500" },
    { label: "LLM API", key: "llm_api", icon: <Brain size={20} />, color: "text-purple-500" },
  ];

  const errorList = Array.isArray(errors?.items) ? errors.items : Array.isArray(errors) ? errors : [];
  const orphanList = Array.isArray(orphans?.items) ? orphans.items : Array.isArray(orphans) ? orphans : [];

  const toggleError = (i: number) => {
    setExpandedErrors((prev) => {
      const next = new Set(prev);
      if (next.has(i)) next.delete(i);
      else next.add(i);
      return next;
    });
  };

  return (
    <motion.div initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }} className="p-8 max-w-6xl mx-auto space-y-6">
      <h1 className="text-2xl font-bold text-slate-900">系统健康</h1>

      {hLoading && !health ? (
        <div className="flex items-center justify-center py-20"><Loader2 className="animate-spin text-indigo-400" size={28} /></div>
      ) : (
        <>
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-5">
            {healthComponents.map((c) => {
              const comp = health?.components?.[c.key] || {};
              const healthy = comp.status === "healthy";
              return (
                <div key={c.key} className="bg-white border border-slate-200 rounded-2xl p-5 shadow-sm">
                  <div className="flex items-center justify-between mb-3">
                    <span className={c.color}>{c.icon}</span>
                    <span className={`flex items-center gap-1.5 text-xs font-medium ${healthy ? "text-emerald-600" : "text-red-600"}`}>
                      <Circle size={8} fill="currentColor" className={healthy ? "text-emerald-500" : "text-red-500"} />
                      {healthy ? "正常" : "异常"}
                    </span>
                  </div>
                  <div className="text-lg font-semibold text-slate-900">{c.label}</div>
                  {comp.latency_ms !== undefined && (
                    <div className="text-sm text-slate-500 mt-1">延迟: {comp.latency_ms}ms</div>
                  )}
                  {comp.error && (
                    <div className="text-xs text-red-500 mt-1 truncate">{comp.error}</div>
                  )}
                </div>
              );
            })}
          </div>

          <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
            <div className="lg:col-span-2 space-y-6">
              <div className="bg-white border border-slate-200 rounded-2xl overflow-hidden shadow-sm">
                <div className="px-6 py-4 border-b border-slate-100">
                  <h2 className="text-lg font-semibold text-slate-900">最近错误</h2>
                </div>
                {eLoading ? (
                  <div className="p-8 flex justify-center"><Loader2 className="animate-spin text-indigo-400" size={20} /></div>
                ) : errorList.length === 0 ? (
                  <div className="p-12 text-center text-slate-400 text-sm">暂无错误，系统运行正常</div>
                ) : (
                  <div className="divide-y divide-slate-100">
                    {errorList.map((err: any, i: number) => {
                      const isExpanded = expandedErrors.has(i);
                      return (
                        <div key={err.id || i} className="px-6 py-4">
                          <div className="flex items-start justify-between gap-3">
                            <div className="flex items-start gap-3 min-w-0">
                              <AlertTriangle size={16} className="text-red-400 shrink-0 mt-0.5" />
                              <div className="min-w-0">
                                <div className="text-sm font-medium text-slate-700">{err.event_type || "未知错误"}</div>
                                <div className="text-xs text-slate-400 mt-0.5">
                                  {new Date(err.created_at).toLocaleString("zh-CN")}
                                </div>
                                <div className="text-sm text-slate-500 mt-1 truncate">{err.message}</div>
                              </div>
                            </div>
                            {err.payload && (
                              <button
                                onClick={() => toggleError(i)}
                                className="p-1 text-slate-400 hover:text-indigo-600 shrink-0"
                              >
                                {isExpanded ? <ChevronUp size={14} /> : <ChevronDown size={14} />}
                              </button>
                            )}
                          </div>
                          {isExpanded && err.payload && (
                            <pre className="mt-3 bg-slate-900 text-green-400 rounded-xl p-4 text-xs overflow-auto max-h-40">
                              {JSON.stringify(err.payload, null, 2)}
                            </pre>
                          )}
                        </div>
                      );
                    })}
                  </div>
                )}
              </div>

              <div className="bg-white border border-slate-200 rounded-2xl overflow-hidden shadow-sm">
                <div className="px-6 py-4 border-b border-slate-100">
                  <h2 className="text-lg font-semibold text-slate-900">异常讨论（无结束事件）</h2>
                </div>
                {oLoading ? (
                  <div className="p-8 flex justify-center"><Loader2 className="animate-spin text-indigo-400" size={20} /></div>
                ) : orphanList.length === 0 ? (
                  <div className="p-12 text-center text-slate-400 text-sm">没有异常讨论</div>
                ) : (
                  <table className="w-full text-sm">
                    <thead>
                      <tr className="border-b border-slate-200 bg-slate-50/50">
                        <th className="text-left px-6 py-3 text-xs font-medium text-slate-500">主题</th>
                        <th className="text-left px-6 py-3 text-xs font-medium text-slate-500">状态</th>
                        <th className="text-left px-6 py-3 text-xs font-medium text-slate-500">开始时间</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-slate-100">
                      {orphanList.map((d: any, i: number) => (
                        <tr key={d.discussion_id || d.id || i}>
                          <td className="px-6 py-3 text-slate-900 font-medium truncate max-w-xs">{d.topic}</td>
                          <td className="px-6 py-3">
                            <span className="px-2 py-0.5 rounded-full text-xs font-medium bg-yellow-100 text-yellow-700">未结束</span>
                          </td>
                          <td className="px-6 py-3 text-slate-500 text-xs">{new Date(d.created_at).toLocaleString("zh-CN")}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                )}
              </div>
            </div>

            <div className="space-y-6">
              <div className="bg-white border border-slate-200 rounded-2xl p-5 shadow-sm">
                <h2 className="text-lg font-semibold text-slate-900 mb-4">系统负载</h2>
                {lLoading ? (
                  <div className="py-8 flex justify-center"><Loader2 className="animate-spin text-indigo-400" size={20} /></div>
                ) : load ? (
                  <div className="space-y-4">
                    {load.cpu_percent !== undefined && (
                      <div className="flex items-center justify-between py-2 px-3 bg-slate-50 rounded-xl">
                        <span className="flex items-center gap-2 text-sm text-slate-600"><Cpu size={16} className="text-slate-400" /> CPU</span>
                        <span className="text-sm font-semibold text-slate-900">{load.cpu_percent}%</span>
                      </div>
                    )}
                    {load.memory_percent !== undefined && (
                      <div className="flex items-center justify-between py-2 px-3 bg-slate-50 rounded-xl">
                        <span className="flex items-center gap-2 text-sm text-slate-600"><HardDrive size={16} className="text-slate-400" /> 内存</span>
                        <span className="text-sm font-semibold text-slate-900">{load.memory_percent}%</span>
                      </div>
                    )}
                    {load.db_pool_size !== undefined && (
                      <div className="flex items-center justify-between py-2 px-3 bg-slate-50 rounded-xl">
                        <span className="flex items-center gap-2 text-sm text-slate-600"><Database size={16} className="text-slate-400" /> DB 连接池</span>
                        <span className="text-sm font-semibold text-slate-900">{load.db_pool_size}</span>
                      </div>
                    )}
                    {load.active_discussions !== undefined && (
                      <div className="flex items-center justify-between py-2 px-3 bg-slate-50 rounded-xl">
                        <span className="flex items-center gap-2 text-sm text-slate-600"><Users size={16} className="text-slate-400" /> 活跃讨论</span>
                        <span className="text-sm font-semibold text-slate-900">{load.active_discussions}</span>
                      </div>
                    )}
                    {load.sse_connections !== undefined && (
                      <div className="flex items-center justify-between py-2 px-3 bg-slate-50 rounded-xl">
                        <span className="flex items-center gap-2 text-sm text-slate-600"><Activity size={16} className="text-slate-400" /> SSE 连接</span>
                        <span className="text-sm font-semibold text-slate-900">{load.sse_connections}</span>
                      </div>
                    )}
                  </div>
                ) : (
                  <div className="py-8 text-center text-slate-400 text-sm">暂无负载数据</div>
                )}
              </div>
            </div>
          </div>
        </>
      )}
    </motion.div>
  );
}
