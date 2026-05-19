import { useState } from "react";
import { useParams, useNavigate } from "react-router";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { motion } from "motion/react";
import { ArrowLeft, Loader2, CheckCircle, XCircle, Pencil, Check, X } from "lucide-react";
import { toast } from "sonner";
import { getUserDetail, updateUserStatus, updateUsername, resetPassword } from "../api/admin";
import { adminClient } from "../api/client";

export function UserDetail() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const qc = useQueryClient();

  const [editingUsername, setEditingUsername] = useState(false);
  const [editingPhone, setEditingPhone] = useState(false);
  const [editingPassword, setEditingPassword] = useState(false);
  const [newUsername, setNewUsername] = useState("");
  const [newPhone, setNewPhone] = useState("");
  const [newPassword, setNewPassword] = useState("");

  const { data: user, isLoading, error } = useQuery({
    queryKey: ["admin-user", id],
    queryFn: () => getUserDetail(id!),
    enabled: !!id,
  });

  const toggleStatus = useMutation({
    mutationFn: (newStatus: string) => updateUserStatus(id!, newStatus === "active"),
    onSuccess: () => { qc.invalidateQueries({ queryKey: ["admin-user", id] }); toast.success("状态已更新"); },
    onError: (err: any) => toast.error(err?.response?.data?.message || "操作失败"),
  });

  const usernameMutation = useMutation({
    mutationFn: (username: string) => updateUsername(id!, username),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["admin-user", id] });
      toast.success("用户名已更新");
      setEditingUsername(false);
    },
    onError: (err: any) => toast.error(err?.response?.data?.message || "更新失败"),
  });

  const phoneMutation = useMutation({
    mutationFn: (phone: string) => adminClient.put(`/users/${id}/phone`, { phone }).then(r => r.data.data),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["admin-user", id] });
      toast.success("手机号已更新");
      setEditingPhone(false);
    },
    onError: (err: any) => toast.error(err?.response?.data?.message || "更新失败"),
  });

  const passwordMutation = useMutation({
    mutationFn: (password: string) => resetPassword(id!, password),
    onSuccess: () => {
      toast.success("密码已重置");
      setEditingPassword(false);
      setNewPassword("");
    },
    onError: (err: any) => toast.error(err?.response?.data?.message || "重置失败"),
  });

  if (isLoading) return <div className="flex items-center justify-center py-20"><Loader2 className="animate-spin text-indigo-400" size={28} /></div>;
  if (error) return <div className="p-8 max-w-6xl mx-auto"><div className="bg-red-50 border border-red-200 rounded-2xl p-6 text-red-600">{(error as any)?.message || "加载失败"}</div></div>;
  if (!user) return <div className="p-8 max-w-6xl mx-auto"><div className="bg-white border border-slate-200 rounded-2xl p-12 text-center text-slate-400">用户不存在</div></div>;

  return (
    <motion.div initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }} className="p-8 max-w-3xl mx-auto space-y-6">
      <button onClick={() => navigate("/users")} className="flex items-center gap-2 text-sm text-slate-500 hover:text-indigo-600 transition-colors">
        <ArrowLeft size={16} /> 返回用户列表
      </button>

      <div className="bg-white border border-slate-200 rounded-2xl shadow-sm p-6 space-y-4">
        <div className="flex items-center gap-3">
          <h1 className="text-2xl font-bold text-slate-900">{user.username}</h1>
          <span className={`inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-medium ${user.status === "active" ? "bg-green-100 text-green-700" : "bg-red-100 text-red-700"}`}>
            {user.status === "active" ? <CheckCircle size={12} /> : <XCircle size={12} />}
            {user.status === "active" ? "正常" : "已禁用"}
          </span>
        </div>

        <div className="grid grid-cols-2 gap-4 text-sm">
          <div><span className="text-slate-500">用户ID</span><p className="text-slate-900 font-mono text-xs mt-1">{user.id}</p></div>
          <div><span className="text-slate-500">注册时间</span><p className="text-slate-900 mt-1">{new Date(user.registered_at).toLocaleString("zh-CN")}</p></div>
          {user.discussion_count !== undefined && (
            <div><span className="text-slate-500">讨论数量</span><p className="text-slate-900 mt-1">{user.discussion_count}</p></div>
          )}
          {user.character_count !== undefined && (
            <div><span className="text-slate-500">角色数量</span><p className="text-slate-900 mt-1">{user.character_count}</p></div>
          )}
          {user.token_usage_summary && (
            <div><span className="text-slate-500">Token 用量</span><p className="text-slate-900 mt-1">{user.token_usage_summary.total_llm_events?.toLocaleString() ?? 0} 次 LLM 调用</p></div>
          )}
        </div>

        {/* Editable Fields */}
        <div className="border-t border-slate-100 pt-4 space-y-4">
          <h2 className="text-sm font-semibold text-slate-700">编辑信息</h2>

          {/* Username */}
          <div className="flex items-center gap-3">
            <span className="text-sm text-slate-500 w-16 shrink-0">用户名</span>
            {editingUsername ? (
              <div className="flex items-center gap-2 flex-1">
                <input
                  type="text"
                  value={newUsername}
                  onChange={(e) => setNewUsername(e.target.value)}
                  className="flex-1 border border-slate-200 rounded-lg px-3 py-2 text-sm focus:ring-2 focus:ring-indigo-500 outline-none"
                  placeholder={user.username}
                />
                <button onClick={() => usernameMutation.mutate(newUsername)} disabled={usernameMutation.isPending || !newUsername} className="p-2 text-emerald-600 hover:bg-emerald-50 rounded-lg disabled:opacity-50">
                  <Check size={16} />
                </button>
                <button onClick={() => setEditingUsername(false)} className="p-2 text-slate-400 hover:bg-slate-50 rounded-lg">
                  <X size={16} />
                </button>
              </div>
            ) : (
              <div className="flex items-center gap-2 flex-1">
                <span className="text-sm text-slate-900">{user.username}</span>
                <button onClick={() => { setEditingUsername(true); setNewUsername(user.username); }} className="p-1 text-slate-400 hover:text-indigo-600">
                  <Pencil size={14} />
                </button>
              </div>
            )}
          </div>

          {/* Phone */}
          <div className="flex items-center gap-3">
            <span className="text-sm text-slate-500 w-16 shrink-0">手机号</span>
            {editingPhone ? (
              <div className="flex items-center gap-2 flex-1">
                <input
                  type="text"
                  value={newPhone}
                  onChange={(e) => setNewPhone(e.target.value)}
                  className="flex-1 border border-slate-200 rounded-lg px-3 py-2 text-sm focus:ring-2 focus:ring-indigo-500 outline-none"
                  placeholder={user.phone || "输入手机号"}
                />
                <button onClick={() => phoneMutation.mutate(newPhone)} disabled={phoneMutation.isPending || !newPhone} className="p-2 text-emerald-600 hover:bg-emerald-50 rounded-lg disabled:opacity-50">
                  <Check size={16} />
                </button>
                <button onClick={() => setEditingPhone(false)} className="p-2 text-slate-400 hover:bg-slate-50 rounded-lg">
                  <X size={16} />
                </button>
              </div>
            ) : (
              <div className="flex items-center gap-2 flex-1">
                <span className="text-sm text-slate-900">{user.phone || "未设置"}</span>
                <button onClick={() => { setEditingPhone(true); setNewPhone(user.phone || ""); }} className="p-1 text-slate-400 hover:text-indigo-600">
                  <Pencil size={14} />
                </button>
              </div>
            )}
          </div>

          {/* Password */}
          <div className="flex items-center gap-3">
            <span className="text-sm text-slate-500 w-16 shrink-0">密码</span>
            {editingPassword ? (
              <div className="flex items-center gap-2 flex-1">
                <input
                  type="password"
                  value={newPassword}
                  onChange={(e) => setNewPassword(e.target.value)}
                  className="flex-1 border border-slate-200 rounded-lg px-3 py-2 text-sm focus:ring-2 focus:ring-indigo-500 outline-none"
                  placeholder="输入新密码 (至少6位)"
                />
                <button onClick={() => passwordMutation.mutate(newPassword)} disabled={passwordMutation.isPending || newPassword.length < 6} className="p-2 text-emerald-600 hover:bg-emerald-50 rounded-lg disabled:opacity-50">
                  <Check size={16} />
                </button>
                <button onClick={() => { setEditingPassword(false); setNewPassword(""); }} className="p-2 text-slate-400 hover:bg-slate-50 rounded-lg">
                  <X size={16} />
                </button>
              </div>
            ) : (
              <div className="flex items-center gap-2 flex-1">
                <span className="text-sm text-slate-400">••••••••</span>
                <button onClick={() => setEditingPassword(true)} className="p-1 text-slate-400 hover:text-indigo-600">
                  <Pencil size={14} />
                </button>
              </div>
            )}
          </div>
        </div>

        <div className="flex gap-3 pt-4 border-t border-slate-100">
          <button
            onClick={() => toggleStatus.mutate(user.status === "active" ? "disabled" : "active")}
            disabled={toggleStatus.isPending}
            className={`px-4 py-2 rounded-xl text-sm font-medium transition-colors disabled:opacity-50 ${
              user.status === "active"
                ? "bg-red-50 text-red-600 hover:bg-red-100"
                : "bg-green-50 text-green-600 hover:bg-green-100"
            }`}
          >
            {toggleStatus.isPending ? "处理中..." : user.status === "active" ? "禁用账号" : "启用账号"}
          </button>
        </div>
      </div>
    </motion.div>
  );
}
