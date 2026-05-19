import { useState } from "react";
import { Link } from "react-router";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { motion } from "motion/react";
import {
  Search,
  Loader2,
  Eye,
  Trash2,
  ChevronLeft,
  ChevronRight,
  Filter,
} from "lucide-react";
import { toast } from "sonner";
import { getDiscussions, deleteDiscussion } from "../api/admin";

const statusOptions = [
  { value: "", label: "全部状态" },
  { value: "running", label: "进行中" },
  { value: "completed", label: "已完成" },
  { value: "error", label: "错误" },
];

export function DiscussionMonitor() {
  const [page, setPage] = useState(1);
  const [search, setSearch] = useState("");
  const [searchInput, setSearchInput] = useState("");
  const [status, setStatus] = useState("");
  const [username, setUsername] = useState("");
  const [usernameInput, setUsernameInput] = useState("");
  const pageSize = 15;
  const qc = useQueryClient();

  const { data, isLoading, error } = useQuery({
    queryKey: ["admin-discussions", { page, search, status, username }],
    queryFn: () => getDiscussions({ page: String(page), page_size: String(pageSize), search, status, username }),
  });

  const deleteMutation = useMutation({
    mutationFn: (id: string) => deleteDiscussion(id),
    onSuccess: () => { qc.invalidateQueries({ queryKey: ["admin-discussions"] }); toast.success("讨论已删除"); },
    onError: (err: any) => toast.error(err?.response?.data?.message || "删除失败"),
  });

  const handleSearch = (e: React.FormEvent) => {
    e.preventDefault();
    setPage(1);
    setSearch(searchInput);
  };

  const handleUsernameFilter = () => {
    setPage(1);
    setUsername(usernameInput);
  };

  const statusBadge = (s: string) => {
    const map: Record<string, { label: string; cls: string }> = {
      running: { label: "进行中", cls: "bg-green-100 text-green-700" },
      completed: { label: "已完成", cls: "bg-blue-100 text-blue-700" },
      error: { label: "错误", cls: "bg-red-100 text-red-700" },
    };
    const m = map[s] || { label: s, cls: "bg-slate-100 text-slate-600" };
    return <span className={`px-2.5 py-1 rounded-full text-xs font-medium ${m.cls}`}>{m.label}</span>;
  };

  const discussions = data?.items || [];
  const total = data?.total || 0;
  const totalPages = Math.max(1, Math.ceil(total / pageSize));

  return (
    <motion.div initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }} className="p-8 max-w-6xl mx-auto space-y-6">
      <h1 className="text-2xl font-bold text-slate-900">讨论监控</h1>

      <div className="flex flex-wrap gap-3 items-center">
        <form onSubmit={handleSearch} className="flex gap-3 flex-1">
          <div className="relative flex-1 max-w-md">
            <Search size={16} className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-400" />
            <input
              type="text"
              value={searchInput}
              onChange={(e) => setSearchInput(e.target.value)}
              placeholder="搜索主题..."
              className="w-full pl-9 border border-slate-200 rounded-xl px-4 py-3 focus:ring-2 focus:ring-indigo-500 outline-none text-sm"
            />
          </div>
          <button
            type="submit"
            className="bg-indigo-600 hover:bg-indigo-700 text-white rounded-xl px-5 py-3 font-semibold text-sm transition-colors"
          >
            搜索
          </button>
        </form>

        <div className="relative">
          <Filter size={16} className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-400" />
          <select
            value={status}
            onChange={(e) => { setStatus(e.target.value); setPage(1); }}
            className="pl-9 pr-8 border border-slate-200 rounded-xl px-4 py-3 focus:ring-2 focus:ring-indigo-500 outline-none text-sm appearance-none bg-white"
          >
            {statusOptions.map((opt) => (
              <option key={opt.value} value={opt.value}>{opt.label}</option>
            ))}
          </select>
        </div>

        <div className="flex gap-2">
          <input
            type="text"
            value={usernameInput}
            onChange={(e) => setUsernameInput(e.target.value)}
            placeholder="按用户名筛选..."
            className="border border-slate-200 rounded-xl px-4 py-3 focus:ring-2 focus:ring-indigo-500 outline-none text-sm w-40"
            onKeyDown={(e) => { if (e.key === 'Enter') handleUsernameFilter(); }}
          />
          <button
            onClick={handleUsernameFilter}
            className="bg-slate-100 hover:bg-slate-200 text-slate-600 rounded-xl px-4 py-3 font-medium text-sm transition-colors"
          >
            筛选
          </button>
          {username && (
            <button
              onClick={() => { setUsername(""); setUsernameInput(""); setPage(1); }}
              className="text-xs text-red-500 hover:text-red-700 px-2"
            >
              清除
            </button>
          )}
        </div>
      </div>

      {isLoading ? (
        <div className="flex items-center justify-center py-20">
          <Loader2 className="animate-spin text-indigo-400" size={28} />
        </div>
      ) : error ? (
        <div className="bg-red-50 border border-red-200 rounded-2xl p-6 text-red-600">{(error as any)?.message || "加载失败"}</div>
      ) : (
        <>
          <div className="bg-white border border-slate-200 rounded-2xl overflow-hidden shadow-sm">
            <table className="w-full text-sm table-fixed">
              <thead>
                <tr className="border-b border-slate-200 bg-slate-50/50">
                  <th className="text-left px-4 py-3 text-xs font-medium text-slate-500 uppercase w-[20%]">讨论主题</th>
                  <th className="text-left px-3 py-3 text-xs font-medium text-slate-500 uppercase w-[11%]">创建者</th>
                  <th className="text-center px-3 py-3 text-xs font-medium text-slate-500 uppercase w-[10%]">智能体数</th>
                  <th className="text-center px-3 py-3 text-xs font-medium text-slate-500 uppercase w-[9%]">轮次</th>
                  <th className="text-center px-3 py-3 text-xs font-medium text-slate-500 uppercase w-[12%]">状态</th>
                  <th className="text-right px-3 py-3 text-xs font-medium text-slate-500 uppercase w-[10%]">Token</th>
                  <th className="text-left px-4 py-3 text-xs font-medium text-slate-500 uppercase w-[18%]">开始时间</th>
                  <th className="text-right px-4 py-3 text-xs font-medium text-slate-500 uppercase w-[10%]">操作</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100">
                {discussions.length === 0 ? (
                  <tr>
                    <td colSpan={8} className="px-6 py-12 text-center text-slate-400">暂无讨论记录</td>
                  </tr>
                ) : (
                  discussions.map((d: any) => (
                    <tr key={d.id} className="hover:bg-slate-50/50 transition-colors">
                      <td className="px-4 py-3.5 font-medium text-slate-900 truncate">{d.topic}</td>
                      <td className="px-3 py-3.5 text-slate-500 text-xs truncate">{d.owner_username || "-"}</td>
                      <td className="px-3 py-3.5 text-slate-700 text-center">{d.agent_count ?? d.agents?.length ?? "-"}</td>
                      <td className="px-3 py-3.5 text-slate-700 text-center">{d.round_count ?? "-"}</td>
                      <td className="px-3 py-3.5 text-center">{statusBadge(d.status)}</td>
                      <td className="px-3 py-3.5 text-slate-500 text-right text-xs">
                        {d.token_usage != null ? d.token_usage.toLocaleString() : "-"}
                      </td>
                      <td className="px-4 py-3.5 text-slate-500 text-xs whitespace-nowrap">
                        {new Date(d.created_at).toLocaleString("zh-CN")}
                      </td>
                      <td className="px-4 py-3.5 text-right">
                        <div className="flex items-center justify-end gap-2">
                          <Link
                            to={`/discussions/${d.id}`}
                            className="p-1.5 text-slate-400 hover:text-indigo-600 hover:bg-indigo-50 rounded-lg transition-colors"
                            title="查看详情"
                          >
                            <Eye size={16} />
                          </Link>
                          <button
                            onClick={() => { if (window.confirm("确定要删除这个讨论吗？此操作不可撤销。")) deleteMutation.mutate(d.id); }}
                            disabled={deleteMutation.isPending}
                            className="p-1.5 text-slate-400 hover:text-red-600 hover:bg-red-50 rounded-lg transition-colors disabled:opacity-50"
                            title="删除"
                          >
                            <Trash2 size={16} />
                          </button>
                        </div>
                      </td>
                    </tr>
                  ))
                )}
              </tbody>
            </table>
          </div>

          {totalPages > 1 && (
            <div className="flex items-center justify-between">
              <span className="text-sm text-slate-500">共 {total} 个讨论</span>
              <div className="flex items-center gap-2">
                <button onClick={() => setPage((p) => Math.max(1, p - 1))} disabled={page <= 1} className="p-2 text-slate-400 hover:text-indigo-600 disabled:opacity-30 transition-colors">
                  <ChevronLeft size={18} />
                </button>
                <span className="text-sm text-slate-600">第 {page} / {totalPages} 页</span>
                <button onClick={() => setPage((p) => Math.min(totalPages, p + 1))} disabled={page >= totalPages} className="p-2 text-slate-400 hover:text-indigo-600 disabled:opacity-30 transition-colors">
                  <ChevronRight size={18} />
                </button>
              </div>
            </div>
          )}
        </>
      )}
    </motion.div>
  );
}
