import { Link } from "react-router";
import { Clock, MessageSquare, Play, Plus, Trash2, Users } from "lucide-react";
import { motion } from "motion/react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { getDiscussions, deleteDiscussion } from "../api/discussions";
import { toast } from "sonner";

function statusMeta(status: string) {
  const map: Record<string, { label: string; tone: string; dot: string }> = {
    running: { label: "进行中", tone: "border-[#207362]/25 bg-[#207362]/10 text-[#185f51]", dot: "bg-[#207362] animate-pulse" },
    completed: { label: "已完成", tone: "border-[#d8cbb7] bg-[#f9f4e9] text-[#6d6254]", dot: "bg-[#9a8b76]" },
    starting: { label: "启动中", tone: "border-[#db9a34]/35 bg-[#db9a34]/12 text-[#8a5c16]", dot: "bg-[#db9a34] animate-pulse" },
    error: { label: "错误", tone: "border-rose-300 bg-rose-50 text-rose-700", dot: "bg-rose-500" },
  };
  return map[status] || { label: status || "未知", tone: "border-[#d8cbb7] bg-[#f9f4e9] text-[#6d6254]", dot: "bg-[#9a8b76]" };
}

function minutes(duration?: number) {
  return Math.max(1, Math.floor((duration || 0) / 60));
}

export function Discussions() {
  const queryClient = useQueryClient();
  const { data: discussions = [], isLoading } = useQuery({
    queryKey: ["discussions"],
    queryFn: () => getDiscussions().then((d) => d.items || []),
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

  return (
    <div className="relative min-h-full overflow-hidden bg-[#f6f3ec] text-[#1d1a16]">
      <div className="pointer-events-none absolute inset-0 bg-[linear-gradient(90deg,rgba(29,26,22,0.045)_1px,transparent_1px),linear-gradient(rgba(29,26,22,0.045)_1px,transparent_1px)] bg-[size:48px_48px]" />
      <div className="relative mx-auto flex w-full max-w-7xl flex-col gap-6 px-4 py-6 sm:px-6 lg:px-8">
        <header className="flex flex-col justify-between gap-4 border-b border-[#d8cbb7] pb-6 md:flex-row md:items-end">
          <div>
            <p className="text-xs font-semibold uppercase tracking-[0.24em] text-[#8a6b37]">Roundtable Sessions</p>
            <h1 className="mt-2 font-['Noto_Serif_SC'] text-3xl font-semibold leading-tight md:text-4xl">圆桌讨论</h1>
            <p className="mt-2 max-w-2xl text-sm leading-6 text-[#6d6254]">查看实时讨论、历史回放和每场圆桌的参与角色。</p>
          </div>
          <Link
            to="/discussions/new"
            className="inline-flex h-11 w-fit items-center gap-2 rounded-lg bg-[#207362] px-4 text-sm font-semibold text-white shadow-[0_10px_24px_rgba(32,115,98,0.24)] transition hover:-translate-y-0.5 hover:bg-[#185f51]"
          >
            <Plus size={18} />
            新建讨论
          </Link>
        </header>

        {isLoading ? (
          <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
            {[1, 2, 3].map((item) => (
              <div key={item} className="h-56 animate-pulse rounded-lg border border-[#d8cbb7] bg-[#fffdf7]" />
            ))}
          </div>
        ) : discussions.length === 0 ? (
          <section className="rounded-lg border border-dashed border-[#cdbfa9] bg-[#fffdf7] p-10 text-center shadow-[0_16px_44px_rgba(53,45,32,0.07)]">
            <MessageSquare className="mx-auto text-[#db9a34]" size={34} />
            <h2 className="mt-4 text-xl font-semibold">暂无讨论</h2>
            <p className="mt-2 text-sm text-[#6d6254]">创建第一场圆桌讨论，把角色拉到同一张桌上。</p>
          </section>
        ) : (
          <section className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
            {discussions.map((disc: any, index: number) => {
              const meta = statusMeta(disc.status);
              return (
                <motion.article
                  key={disc.id}
                  initial={{ opacity: 0, y: 12 }}
                  animate={{ opacity: 1, y: 0 }}
                  transition={{ delay: index * 0.035 }}
                  className="group rounded-lg border border-[#d8cbb7] bg-[#fffdf7] p-5 shadow-[0_14px_38px_rgba(53,45,32,0.08)] transition hover:-translate-y-0.5 hover:border-[#252018]"
                >
                  <div className="flex items-start justify-between gap-4">
                    <span className={`inline-flex items-center gap-2 rounded-lg border px-2.5 py-1 text-xs font-semibold ${meta.tone}`}>
                      <span className={`h-2 w-2 rounded-full ${meta.dot}`} />
                      {meta.label}
                    </span>
                    <button
                      onClick={(e) => handleDelete(e, disc.id)}
                      className="rounded-lg p-2 text-[#9a8b76] opacity-100 transition hover:bg-rose-50 hover:text-rose-600 md:opacity-0 md:group-hover:opacity-100"
                      title="删除讨论"
                    >
                      <Trash2 size={16} />
                    </button>
                  </div>
                  <h2 className="mt-5 line-clamp-2 min-h-[3.5rem] text-lg font-semibold leading-7">{disc.topic}</h2>
                  <div className="mt-4 grid gap-2 text-sm text-[#6d6254]">
                    <div className="flex items-center gap-2">
                      <Users size={16} className="text-[#8a6b37]" />
                      {disc.agents?.length || 0} 个参与智能体
                    </div>
                    <div className="flex items-center gap-2">
                      <Clock size={16} className="text-[#8a6b37]" />
                      时长：{minutes(disc.duration)} 分钟
                    </div>
                  </div>
                  <div className="mt-5 border-t border-[#e4dccd] pt-4">
                    <Link
                      to={`/discussions/${disc.id}`}
                      className="inline-flex h-10 w-full items-center justify-center gap-2 rounded-lg bg-[#1d1a16] text-sm font-semibold text-white transition hover:bg-[#2f281f]"
                    >
                      <Play size={17} />
                      {disc.status === "running" ? "加入实时会议" : "会议回放"}
                    </Link>
                  </div>
                </motion.article>
              );
            })}
          </section>
        )}
      </div>
    </div>
  );
}
