import { useState } from "react";
import { Link } from "react-router";
import { useQuery } from "@tanstack/react-query";
import { motion } from "motion/react";
import {
  Loader2,
  Shield,
  AlertTriangle,
  Info,
  FileText,
  ChevronDown,
  ChevronUp,
  Search,
  Filter,
} from "lucide-react";
import { getAuditEvents } from "../api/admin";

const eventTypeOptions = [
  { value: "", label: "全部类型" },
  { value: "user.register", label: "用户注册" },
  { value: "user.login", label: "用户登录" },
  { value: "user.login_failed", label: "登录失败" },
  { value: "skill.generate", label: "角色生成" },
  { value: "skill.generate_complete", label: "角色生成完成" },
  { value: "skill.generate_error", label: "角色生成错误" },
  { value: "skill.create", label: "角色创建" },
  { value: "skill.update", label: "角色更新" },
  { value: "skill.delete", label: "角色删除" },
  { value: "skill.copy", label: "角色复制" },
  { value: "discussion.create", label: "讨论创建" },
  { value: "discussion.error", label: "讨论错误" },
  { value: "host_intro", label: "主持开场" },
  { value: "host_summary", label: "主持总结" },
  { value: "round_start", label: "轮次开始" },
  { value: "agent_speak_chunk", label: "智能体发言" },
  { value: "discussion_end", label: "讨论结束" },
  { value: "system.error", label: "系统错误" },
];

const levelOptions = [
  { value: "", label: "全部级别" },
  { value: "P0", label: "P0 严重" },
  { value: "P1", label: "P1 重要" },
  { value: "P2", label: "P2 一般" },
];

const iconMap: Record<string, { icon: React.ReactNode; color: string }> = {
  P0: { icon: <AlertTriangle size={16} />, color: "text-red-500 bg-red-50" },
  P1: { icon: <Info size={16} />, color: "text-orange-500 bg-orange-50" },
  P2: { icon: <FileText size={16} />, color: "text-slate-500 bg-slate-100" },
};

function getEventIcon(evt: any) {
  const level = evt.level || "P2";
  return iconMap[level] || iconMap.P2;
}

function hasPayload(evt: any) {
  if (!evt.payload) return false;
  if (typeof evt.payload === "object" && Object.keys(evt.payload).length === 0) return false;
  return true;
}

export function AuditTrail() {
  const [page, setPage] = useState(1);
  const [eventType, setEventType] = useState("");
  const [level, setLevel] = useState("");
  const [userId, setUserId] = useState("");
  const [expandedIds, setExpandedIds] = useState<Set<string>>(new Set());
  const pageSize = 20;

  const { data, isLoading, error } = useQuery({
    queryKey: ["admin-audit", { page, eventType, level, userId }],
    queryFn: () => {
      const params: Record<string, string> = { page: String(page), page_size: String(pageSize) };
      if (eventType) params.event_type = eventType;
      if (level) params.level = level;
      if (userId) params.user_id = userId;
      return getAuditEvents(params);
    },
  });

  const toggleExpand = (id: string) => {
    setExpandedIds((prev) => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });
  };

  const events = data?.items || [];
  const total = data?.total || 0;
  const totalPages = Math.max(1, Math.ceil(total / pageSize));

  return (
    <motion.div initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }} className="p-8 max-w-6xl mx-auto space-y-6">
      <h1 className="text-2xl font-bold text-slate-900">审计日志</h1>

      <div className="flex flex-wrap gap-3 items-center">
        <div className="relative">
          <Filter size={16} className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-400" />
          <select
            value={eventType}
            onChange={(e) => { setEventType(e.target.value); setPage(1); }}
            className="pl-9 pr-8 border border-slate-200 rounded-xl px-4 py-3 focus:ring-2 focus:ring-indigo-500 outline-none text-sm appearance-none bg-white"
          >
            {eventTypeOptions.map((opt) => (
              <option key={opt.value} value={opt.value}>{opt.label}</option>
            ))}
          </select>
        </div>

        <div className="relative">
          <Filter size={16} className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-400" />
          <select
            value={level}
            onChange={(e) => { setLevel(e.target.value); setPage(1); }}
            className="pl-9 pr-8 border border-slate-200 rounded-xl px-4 py-3 focus:ring-2 focus:ring-indigo-500 outline-none text-sm appearance-none bg-white"
          >
            {levelOptions.map((opt) => (
              <option key={opt.value} value={opt.value}>{opt.label}</option>
            ))}
          </select>
        </div>

        <div className="relative max-w-xs">
          <Search size={16} className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-400" />
          <input
            type="text"
            value={userId}
            onChange={(e) => setUserId(e.target.value)}
            placeholder="用户ID..."
            onKeyDown={(e) => { if (e.key === "Enter") { setPage(1); setUserId(userId.trim()); } }}
            className="w-48 pl-9 border border-slate-200 rounded-xl px-4 py-3 focus:ring-2 focus:ring-indigo-500 outline-none text-sm"
          />
        </div>

        <button
          onClick={() => { setPage(1); }}
          className="bg-indigo-600 hover:bg-indigo-700 text-white rounded-xl px-5 py-3 font-semibold text-sm transition-colors"
        >
          筛选
        </button>
      </div>

      {isLoading ? (
        <div className="flex items-center justify-center py-20">
          <Loader2 className="animate-spin text-indigo-400" size={28} />
        </div>
      ) : error ? (
        <div className="bg-red-50 border border-red-200 rounded-2xl p-6 text-red-600">{(error as any)?.message || "加载失败"}</div>
      ) : events.length === 0 ? (
        <div className="bg-white border border-slate-200 rounded-2xl shadow-sm p-12 text-center">
          <Shield size={40} className="mx-auto text-slate-300 mb-3" />
          <p className="text-slate-400">暂无审计事件</p>
        </div>
      ) : (
        <>
          <div className="space-y-3">
            {events.map((evt: any, i: number) => {
              const iconCfg = getEventIcon(evt);
              const isExpanded = expandedIds.has(evt.id || String(i));
              return (
                <motion.div
                  key={evt.id || i}
                  initial={{ opacity: 0, y: 8 }}
                  animate={{ opacity: 1, y: 0 }}
                  transition={{ delay: i * 0.02 }}
                  className="bg-white border border-slate-200 rounded-2xl shadow-sm overflow-hidden"
                >
                  <div className="px-5 py-4 flex items-center gap-4">
                    <div className={`p-2 rounded-xl shrink-0 ${iconCfg.color}`}>
                      {iconCfg.icon}
                    </div>
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center gap-2">
                        <span className="text-sm font-medium text-slate-900 truncate">{evt.event_type}</span>
                        {evt.level && (
                          <span className={`px-1.5 py-0.5 rounded text-[10px] font-medium shrink-0 ${
                            evt.level === "P0" ? "bg-red-100 text-red-700" :
                            evt.level === "P1" ? "bg-orange-100 text-orange-700" :
                            "bg-slate-100 text-slate-600"
                          }`}>{evt.level}</span>
                        )}
                      </div>
                      <div className="flex items-center gap-3 mt-1 text-xs text-slate-400">
                        <span>{new Date(evt.created_at).toLocaleString("zh-CN")}</span>
                        {evt.user_id && <span>用户: {evt.user_id.slice(0, 8)}...</span>}
                        {evt.discussion_id && <span>讨论: {evt.discussion_id.slice(0, 8)}...</span>}
                      </div>
                    </div>
                    <div className="flex items-center gap-2">
                      {hasPayload(evt) && (
                        <button
                          onClick={() => toggleExpand(evt.id || String(i))}
                          className="p-1.5 text-slate-400 hover:text-indigo-600 hover:bg-indigo-50 rounded-lg transition-colors"
                        >
                          {isExpanded ? <ChevronUp size={16} /> : <ChevronDown size={16} />}
                        </button>
                      )}
                      <Link
                        to={`/audit/${evt.id}`}
                        className="text-xs text-indigo-600 hover:text-indigo-700 font-medium transition-colors"
                      >
                        详情
                      </Link>
                    </div>
                  </div>
                  {isExpanded && hasPayload(evt) && (
                    <div className="px-5 pb-4 border-t border-slate-100">
                      <pre className="mt-3 bg-slate-50 border border-slate-100 rounded-xl p-3 text-xs text-slate-600 overflow-auto max-h-60">
                        {JSON.stringify(evt.payload, null, 2)}
                      </pre>
                    </div>
                  )}
                </motion.div>
              );
            })}
          </div>

          <div className="flex items-center justify-between">
            <span className="text-sm text-slate-500">共 {total} 条记录</span>
            <div className="flex items-center gap-3">
              <button
                onClick={() => setPage((p) => Math.min(totalPages, p + 1))}
                disabled={page >= totalPages}
                className="px-4 py-2 bg-white border border-slate-200 rounded-xl text-sm font-medium text-slate-600 hover:bg-slate-50 transition-colors disabled:opacity-40"
              >
                加载更多 (第 {page}/{totalPages} 页)
              </button>
            </div>
          </div>
        </>
      )}
    </motion.div>
  );
}
