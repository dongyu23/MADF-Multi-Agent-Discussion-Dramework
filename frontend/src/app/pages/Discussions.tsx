import { Link } from "react-router";
import { Plus, Users, Play, Clock, Trash2 } from "lucide-react";
import { motion } from "motion/react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { getDiscussions, deleteDiscussion } from "../api/discussions";
import { toast } from "sonner";

export function Discussions() {
  const queryClient = useQueryClient();
  const { data: discussions = [], isLoading } = useQuery({
    queryKey: ["discussions"],
    queryFn: () => getDiscussions().then(d => d.items || []),
    staleTime: 10_000,
  });

  const deleteMutation = useMutation({
    mutationFn: deleteDiscussion,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["discussions"] });
      toast.success("讨论已删除");
    },
    onError: (err: any) => toast.error(err.response?.data?.message || "删除失败"),
  });

  const handleDelete = (e: React.MouseEvent, id: string) => {
    e.preventDefault();
    e.stopPropagation();
    if (!confirm("确定要删除这场讨论吗？")) return;
    deleteMutation.mutate(id);
  };

  const statusLabel = (s: string) => {
    const map: Record<string, string> = { running: "进行中", completed: "已完成", starting: "启动中", error: "错误" };
    return map[s] || s;
  };

  if (isLoading) {
    return (
      <div className="p-8 max-w-7xl mx-auto">
        <div className="animate-pulse grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {[1, 2, 3].map((i) => (
            <div key={i} className="h-48 bg-slate-200 rounded-2xl" />
          ))}
        </div>
      </div>
    );
  }

  return (
    <div className="p-8 max-w-7xl mx-auto space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-slate-900">圆桌讨论</h1>
          <p className="text-slate-500 mt-1">管理并查看智能体圆桌会议</p>
        </div>
        <Link
          to="/discussions/new"
          className="flex items-center gap-2 bg-indigo-600 text-white px-5 py-2.5 rounded-xl font-medium hover:bg-indigo-700 transition-colors shadow-sm"
        >
          <Plus size={18} />
          新建讨论
        </Link>
      </div>

      {discussions.length === 0 ? (
        <div className="text-center py-16 text-slate-400">
          <p className="text-lg mb-2">暂无讨论</p>
          <p>创建你的第一场圆桌讨论吧</p>
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {discussions.map((disc: any, i: number) => (
            <motion.div
              key={disc.id}
              initial={{ opacity: 0, y: 10 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: i * 0.05 }}
              className="bg-white border border-slate-200 rounded-2xl p-6 hover:shadow-md transition-shadow group"
            >
              <div className="flex items-start justify-between mb-4">
                <span className={`px-2.5 py-1 rounded-full text-xs font-medium flex items-center gap-1.5 ${
                  disc.status === "running" ? "bg-emerald-100 text-emerald-700" : "bg-slate-100 text-slate-700"
                }`}>
                  {disc.status === "running" && <span className="w-1.5 h-1.5 rounded-full bg-emerald-500 animate-pulse" />}
                  {statusLabel(disc.status)}
                </span>
                <button
                  onClick={(e) => handleDelete(e, disc.id)}
                  className="p-1.5 text-slate-300 hover:text-red-500 hover:bg-red-50 rounded-lg transition-colors opacity-0 group-hover:opacity-100"
                  title="删除讨论"
                >
                  <Trash2 size={16} />
                </button>
              </div>
              <h3 className="font-bold text-lg text-slate-900 mb-4 line-clamp-2">{disc.topic}</h3>
              <div className="space-y-2 mb-6">
                <div className="flex items-center gap-2 text-sm text-slate-500">
                  <Users size={16} className="text-slate-400" />
                  {disc.agents?.length || 0} 个参与智能体
                </div>
                <div className="flex items-center gap-2 text-sm text-slate-500">
                  <Clock size={16} className="text-slate-400" />
                  时长: {Math.floor((disc.duration || 0) / 60)} 分钟
                </div>
              </div>
              <div className="pt-4 border-t border-slate-100">
                <Link
                  to={`/discussions/${disc.id}`}
                  className="w-full flex items-center justify-center gap-2 bg-slate-50 hover:bg-indigo-50 text-slate-700 hover:text-indigo-700 font-semibold py-2.5 rounded-xl transition-colors"
                >
                  <Play size={18} />
                  {disc.status === "running" ? "加入实时会议" : "会议回放"}
                </Link>
              </div>
            </motion.div>
          ))}
        </div>
      )}
    </div>
  );
}
