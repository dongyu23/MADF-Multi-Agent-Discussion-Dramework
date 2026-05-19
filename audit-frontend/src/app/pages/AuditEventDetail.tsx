import { useParams, useNavigate } from "react-router";
import { useQuery } from "@tanstack/react-query";
import { motion } from "motion/react";
import { ArrowLeft, Loader2, Clock, User, Tag, AlertTriangle } from "lucide-react";
import { getAuditEventDetail } from "../api/admin";

const levelBadge = (level: string) => {
  const map: Record<string, { label: string; cls: string }> = {
    P0: { label: "P0 严重", cls: "bg-red-100 text-red-700" },
    P1: { label: "P1 重要", cls: "bg-orange-100 text-orange-700" },
    P2: { label: "P2 一般", cls: "bg-slate-100 text-slate-600" },
  };
  const m = map[level] || { label: level, cls: "bg-slate-100 text-slate-600" };
  return <span className={`px-2 py-0.5 rounded text-xs font-medium ${m.cls}`}>{m.label}</span>;
};

export function AuditEventDetail() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();

  const { data: event, isLoading, error } = useQuery({
    queryKey: ["audit-event", id],
    queryFn: () => getAuditEventDetail(id!),
    enabled: !!id,
  });

  if (isLoading) return <div className="flex items-center justify-center py-20"><Loader2 className="animate-spin text-indigo-400" size={28} /></div>;
  if (error) return <div className="p-8 max-w-6xl mx-auto"><div className="bg-red-50 border border-red-200 rounded-2xl p-6 text-red-600">{(error as any)?.message || "加载失败"}</div></div>;
  if (!event) return <div className="p-8 max-w-6xl mx-auto"><div className="bg-white border border-slate-200 rounded-2xl p-12 text-center text-slate-400">事件不存在</div></div>;

  return (
    <motion.div initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }} className="p-8 max-w-3xl mx-auto space-y-6">
      <button onClick={() => navigate("/audit")} className="flex items-center gap-2 text-sm text-slate-500 hover:text-indigo-600 transition-colors">
        <ArrowLeft size={16} /> 返回审计日志
      </button>

      <div className="bg-white border border-slate-200 rounded-2xl shadow-sm p-6 space-y-4">
        <div className="flex items-center gap-3">
          {event.level === "P0" && <AlertTriangle size={20} className="text-red-500" />}
          <h1 className="text-xl font-bold text-slate-900">{event.event_type}</h1>
          {event.level && levelBadge(event.level)}
        </div>

        <div className="grid grid-cols-2 gap-4 text-sm">
          <div>
            <span className="flex items-center gap-1 text-slate-500"><Clock size={14} /> 时间</span>
            <p className="text-slate-900 mt-1">{new Date(event.created_at).toLocaleString("zh-CN")}</p>
          </div>
          {event.user_id && (
            <div>
              <span className="flex items-center gap-1 text-slate-500"><User size={14} /> 用户ID</span>
              <p className="text-slate-900 font-mono text-xs mt-1">{event.user_id}</p>
            </div>
          )}
          {event.discussion_id && (
            <div>
              <span className="flex items-center gap-1 text-slate-500"><Tag size={14} /> 讨论ID</span>
              <p className="text-slate-900 font-mono text-xs mt-1">{event.discussion_id}</p>
            </div>
          )}
        </div>

        {event.payload && (
          <div className="pt-4 border-t border-slate-100">
            <span className="text-sm font-medium text-slate-500">事件详情</span>
            <pre className="mt-2 bg-slate-50 border border-slate-200 rounded-xl p-4 text-xs text-slate-700 overflow-auto max-h-96">
              {JSON.stringify(event.payload, null, 2)}
            </pre>
          </div>
        )}
      </div>
    </motion.div>
  );
}
