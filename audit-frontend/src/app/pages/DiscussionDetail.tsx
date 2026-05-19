import { useParams, useNavigate } from "react-router";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { motion } from "motion/react";
import { ArrowLeft, Loader2, Trash2, Users, Clock, Hash } from "lucide-react";
import { toast } from "sonner";
import { getDiscussionDetail, getDiscussionMessages, deleteDiscussion } from "../api/admin";

export function DiscussionDetail() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const qc = useQueryClient();

  const { data: discussion, isLoading, error } = useQuery({
    queryKey: ["admin-discussion", id],
    queryFn: () => getDiscussionDetail(id!),
    enabled: !!id,
  });

  const { data: messages } = useQuery({
    queryKey: ["admin-discussion-messages", id],
    queryFn: () => getDiscussionMessages(id!),
    enabled: !!id,
  });

  const deleteMutation = useMutation({
    mutationFn: () => deleteDiscussion(id!),
    onSuccess: () => { toast.success("讨论已删除"); qc.invalidateQueries({ queryKey: ["admin-discussions"] }); navigate("/discussions"); },
    onError: (err: any) => toast.error(err?.response?.data?.message || "删除失败"),
  });

  const statusBadge = (s: string) => {
    const map: Record<string, { label: string; cls: string }> = {
      running: { label: "进行中", cls: "bg-green-100 text-green-700" },
      completed: { label: "已完成", cls: "bg-blue-100 text-blue-700" },
      error: { label: "错误", cls: "bg-red-100 text-red-700" },
    };
    const m = map[s] || { label: s, cls: "bg-slate-100 text-slate-600" };
    return <span className={`px-2.5 py-1 rounded-full text-xs font-medium ${m.cls}`}>{m.label}</span>;
  };

  if (isLoading) return <div className="flex items-center justify-center py-20"><Loader2 className="animate-spin text-indigo-400" size={28} /></div>;
  if (error) return <div className="p-8 max-w-6xl mx-auto"><div className="bg-red-50 border border-red-200 rounded-2xl p-6 text-red-600">{(error as any)?.message || "加载失败"}</div></div>;
  if (!discussion) return <div className="p-8 max-w-6xl mx-auto"><div className="bg-white border border-slate-200 rounded-2xl p-12 text-center text-slate-400">讨论不存在</div></div>;

  const msgItems = Array.isArray(messages) ? messages : (messages?.items || []);

  return (
    <motion.div initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }} className="p-8 max-w-4xl mx-auto space-y-6">
      <button onClick={() => navigate("/discussions")} className="flex items-center gap-2 text-sm text-slate-500 hover:text-indigo-600 transition-colors">
        <ArrowLeft size={16} /> 返回讨论列表
      </button>

      <div className="bg-white border border-slate-200 rounded-2xl shadow-sm p-6 space-y-4">
        <div className="flex items-start justify-between">
          <div>
            <h1 className="text-2xl font-bold text-slate-900">{discussion.topic}</h1>
            <div className="flex items-center gap-4 mt-2 text-sm text-slate-500">
              <span className="flex items-center gap-1"><Users size={14} /> {discussion.agent_count || discussion.agents?.length || 0} 个智能体</span>
              <span className="flex items-center gap-1"><Hash size={14} /> {discussion.round_count ?? 0} 轮</span>
              <span className="flex items-center gap-1"><Clock size={14} /> {new Date(discussion.created_at).toLocaleString("zh-CN")}</span>
              {discussion.token_usage !== undefined && discussion.token_usage > 0 && (
                <span className="text-xs text-slate-400">{discussion.token_usage?.toLocaleString()} token</span>
              )}
            </div>
          </div>
          <div className="flex items-center gap-3">
            {statusBadge(discussion.status)}
            <button
              onClick={() => { if (window.confirm("确定要删除这个讨论吗？此操作不可撤销。")) deleteMutation.mutate(); }}
              disabled={deleteMutation.isPending}
              className="p-2 text-slate-400 hover:text-red-600 hover:bg-red-50 rounded-lg transition-colors disabled:opacity-50"
              title="删除讨论"
            >
              <Trash2 size={18} />
            </button>
          </div>
        </div>

        {discussion.duration && <div className="text-sm text-slate-500">讨论时长：{discussion.duration} 秒</div>}
        {discussion.ended_at && <div className="text-sm text-slate-500">结束时间：{new Date(discussion.ended_at).toLocaleString("zh-CN")}</div>}
        {discussion.token_usage !== undefined && <div className="text-sm text-slate-500">Token 用量：{discussion.token_usage.toLocaleString()}</div>}
      </div>

      <div className="bg-white border border-slate-200 rounded-2xl overflow-hidden shadow-sm">
        <div className="px-6 py-4 border-b border-slate-100">
          <h2 className="text-lg font-semibold text-slate-900">讨论消息</h2>
          <p className="text-sm text-slate-500 mt-0.5">共 {msgItems.length} 条消息</p>
        </div>
        {msgItems.length === 0 ? (
          <div className="p-12 text-center text-slate-400">暂无消息记录</div>
        ) : (
          <div className="divide-y divide-slate-100 max-h-96 overflow-y-auto">
            {msgItems.map((msg: any, i: number) => (
              <div key={msg.id || i} className="px-6 py-4">
                <div className="flex items-center gap-3 mb-1">
                  <span className="text-xs font-medium text-indigo-600 bg-indigo-50 px-2 py-0.5 rounded">
                    {msg.message_type || msg.type}
                  </span>
                  {msg.agent_name && <span className="text-sm font-medium text-slate-700">{msg.agent_name}</span>}
                  {msg.round_number !== undefined && <span className="text-xs text-slate-400">第 {msg.round_number} 轮</span>}
                </div>
                <p className="text-sm text-slate-600 whitespace-pre-wrap">{msg.content}</p>
              </div>
            ))}
          </div>
        )}
      </div>
    </motion.div>
  );
}
