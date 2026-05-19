import { useState } from "react";
import { Link } from "react-router";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { motion } from "motion/react";
import {
  Search,
  Loader2,
  CheckCircle,
  XCircle,
  ChevronLeft,
  ChevronRight,
  Eye,
  Trash2,
  UserPlus,
} from "lucide-react";
import { toast } from "sonner";
import { getUsers, updateUserStatus, deleteUser, createUser } from "../api/admin";

export function UserManagement() {
  const [page, setPage] = useState(1);
  const [search, setSearch] = useState("");
  const [showCreate, setShowCreate] = useState(false);
  const [newUsername, setNewUsername] = useState("");
  const [newPassword, setNewPassword] = useState("");
  const [newPhone, setNewPhone] = useState("");
  const [searchInput, setSearchInput] = useState("");
  const pageSize = 15;
  const qc = useQueryClient();

  const { data, isLoading, error } = useQuery({
    queryKey: ["admin-users", { page, search }],
    queryFn: () => getUsers({ page: String(page), page_size: String(pageSize), search }),
  });

  const toggleStatus = useMutation({
    mutationFn: ({ id, newStatus }: { id: string; newStatus: string }) => updateUserStatus(id, newStatus === "active"),
    onSuccess: () => { qc.invalidateQueries({ queryKey: ["admin-users"] }); toast.success("状态已更新"); },
    onError: (err: any) => toast.error(err?.response?.data?.message || "操作失败"),
  });

  const deleteMutation = useMutation({
    mutationFn: (id: string) => deleteUser(id),
    onSuccess: () => { qc.invalidateQueries({ queryKey: ["admin-users"] }); toast.success("用户已删除"); },
    onError: (err: any) => toast.error(err?.response?.data?.message || "删除失败"),
  });

  const createMutation = useMutation({
    mutationFn: (data: { username: string; password: string; phone?: string }) => createUser(data),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["admin-users"] });
      toast.success("用户已创建");
      setShowCreate(false);
      setNewUsername("");
      setNewPassword("");
      setNewPhone("");
    },
    onError: (err: any) => toast.error(err?.response?.data?.message || "创建失败"),
  });

  const handleSearch = (e: React.FormEvent) => {
    e.preventDefault();
    setPage(1);
    setSearch(searchInput);
  };

  const users = data?.items || [];
  const total = data?.total || 0;
  const totalPages = Math.max(1, Math.ceil(total / pageSize));

  return (
    <motion.div initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }} className="p-8 max-w-6xl mx-auto space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold text-slate-900">用户管理</h1>
        <div className="flex items-center gap-4">
          <span className="text-sm text-slate-500">共 {total} 个用户</span>
          <button
            onClick={() => setShowCreate(true)}
            className="flex items-center gap-2 bg-indigo-600 hover:bg-indigo-700 text-white rounded-xl px-4 py-2.5 font-semibold text-sm transition-colors"
          >
            <UserPlus size={16} /> 创建用户
          </button>
        </div>
      </div>

      {showCreate && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/30">
          <motion.div initial={{ opacity: 0, scale: 0.95 }} animate={{ opacity: 1, scale: 1 }} className="bg-white rounded-2xl shadow-xl p-6 w-full max-w-md space-y-4">
            <h2 className="text-lg font-semibold text-slate-900">创建新用户</h2>
            <div className="space-y-3">
              <div>
                <label className="text-sm font-medium text-slate-600">用户名</label>
                <input
                  type="text"
                  value={newUsername}
                  onChange={(e) => setNewUsername(e.target.value)}
                  className="w-full mt-1 border border-slate-200 rounded-lg px-3 py-2 text-sm focus:ring-2 focus:ring-indigo-500 outline-none"
                  placeholder="2-64 个字符"
                />
              </div>
              <div>
                <label className="text-sm font-medium text-slate-600">密码</label>
                <input
                  type="password"
                  value={newPassword}
                  onChange={(e) => setNewPassword(e.target.value)}
                  className="w-full mt-1 border border-slate-200 rounded-lg px-3 py-2 text-sm focus:ring-2 focus:ring-indigo-500 outline-none"
                  placeholder="至少 6 位"
                />
              </div>
              <div>
                <label className="text-sm font-medium text-slate-600">手机号 <span className="text-slate-400">(可选)</span></label>
                <input
                  type="text"
                  value={newPhone}
                  onChange={(e) => setNewPhone(e.target.value)}
                  className="w-full mt-1 border border-slate-200 rounded-lg px-3 py-2 text-sm focus:ring-2 focus:ring-indigo-500 outline-none"
                  placeholder="选填"
                />
              </div>
            </div>
            <div className="flex gap-3 justify-end pt-2">
              <button
                onClick={() => { setShowCreate(false); setNewUsername(""); setNewPassword(""); setNewPhone(""); }}
                className="px-4 py-2 text-sm font-medium text-slate-600 hover:bg-slate-50 rounded-xl transition-colors"
              >
                取消
              </button>
              <button
                onClick={() => createMutation.mutate({ username: newUsername, password: newPassword, phone: newPhone || undefined })}
                disabled={createMutation.isPending || newUsername.length < 2 || newPassword.length < 6}
                className="px-4 py-2 text-sm font-semibold text-white bg-indigo-600 hover:bg-indigo-700 rounded-xl transition-colors disabled:opacity-50"
              >
                {createMutation.isPending ? "创建中..." : "创建"}
              </button>
            </div>
          </motion.div>
        </div>
      )}

      <form onSubmit={handleSearch} className="flex gap-3">
        <div className="relative flex-1 max-w-md">
          <Search size={16} className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-400" />
          <input
            type="text"
            value={searchInput}
            onChange={(e) => setSearchInput(e.target.value)}
            placeholder="搜索用户名..."
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
                  <th className="text-left px-5 py-3 text-xs font-medium text-slate-500 uppercase w-[16%]">用户名</th>
                  <th className="text-left px-5 py-3 text-xs font-medium text-slate-500 uppercase w-[16%]">手机号</th>
                  <th className="text-center px-3 py-3 text-xs font-medium text-slate-500 uppercase w-[8%]">角色</th>
                  <th className="text-center px-3 py-3 text-xs font-medium text-slate-500 uppercase w-[8%]">讨论</th>
                  <th className="text-left px-5 py-3 text-xs font-medium text-slate-500 uppercase w-[20%]">注册时间</th>
                  <th className="text-center px-3 py-3 text-xs font-medium text-slate-500 uppercase w-[14%]">状态</th>
                  <th className="text-right px-5 py-3 text-xs font-medium text-slate-500 uppercase w-[18%]">操作</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100">
                {users.length === 0 ? (
                  <tr>
                    <td colSpan={7} className="px-6 py-12 text-center text-slate-400">暂无用户数据</td>
                  </tr>
                ) : (
                  users.map((u: any) => (
                    <tr key={u.id} className="hover:bg-slate-50/50 transition-colors">
                      <td className="px-5 py-3.5 font-medium text-slate-900 truncate">{u.username}</td>
                      <td className="px-5 py-3.5 text-slate-500 truncate">{u.phone || "-"}</td>
                      <td className="px-3 py-3.5 text-center text-slate-700">{u.character_count ?? "-"}</td>
                      <td className="px-3 py-3.5 text-center text-slate-700">{u.discussion_count ?? "-"}</td>
                      <td className="px-5 py-3.5 text-slate-500 text-xs whitespace-nowrap">
                        {new Date(u.registered_at).toLocaleString("zh-CN")}
                      </td>
                      <td className="px-3 py-3.5 text-center">
                        <span className={`inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-medium ${
                          u.status === "active" ? "bg-green-100 text-green-700" : "bg-red-100 text-red-700"
                        }`}>
                          {u.status === "active" ? <CheckCircle size={12} /> : <XCircle size={12} />}
                          {u.status === "active" ? "正常" : "已禁用"}
                        </span>
                      </td>
                      <td className="px-5 py-3.5">
                        <div className="flex items-center justify-end gap-1">
                          <Link
                            to={`/users/${u.id}`}
                            className="p-1.5 text-slate-400 hover:text-indigo-600 hover:bg-indigo-50 rounded-lg transition-colors"
                            title="查看详情"
                          >
                            <Eye size={16} />
                          </Link>
                          <button
                            onClick={() => toggleStatus.mutate({ id: u.id, newStatus: u.status === "active" ? "disabled" : "active" })}
                            disabled={toggleStatus.isPending}
                            className={`text-xs font-medium px-2.5 py-1 rounded-lg transition-colors disabled:opacity-50 ${
                              u.status === "active"
                                ? "text-red-600 hover:bg-red-50"
                                : "text-green-600 hover:bg-green-50"
                            }`}
                          >
                            {u.status === "active" ? "禁用" : "启用"}
                          </button>
                          <button
                            onClick={() => { if (window.confirm(`确定要删除用户 ${u.username} 吗？此操作不可撤销。`)) deleteMutation.mutate(u.id); }}
                            disabled={deleteMutation.isPending}
                            className="p-1.5 text-slate-400 hover:text-red-600 hover:bg-red-50 rounded-lg transition-colors disabled:opacity-50"
                            title="删除用户"
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
              <span className="text-sm text-slate-500">共 {total} 个用户</span>
              <div className="flex items-center gap-2">
                <button
                  onClick={() => setPage((p) => Math.max(1, p - 1))}
                  disabled={page <= 1}
                  className="p-2 text-slate-400 hover:text-indigo-600 disabled:opacity-30 transition-colors"
                >
                  <ChevronLeft size={18} />
                </button>
                <span className="text-sm text-slate-600">第 {page} / {totalPages} 页</span>
                <button
                  onClick={() => setPage((p) => Math.min(totalPages, p + 1))}
                  disabled={page >= totalPages}
                  className="p-2 text-slate-400 hover:text-indigo-600 disabled:opacity-30 transition-colors"
                >
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
