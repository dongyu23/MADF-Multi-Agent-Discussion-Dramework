import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { motion } from "motion/react";
import {
  Loader2,
  Plus,
  Trash2,
  Edit3,
  X,
  Shield,
} from "lucide-react";
import { toast } from "sonner";
import { getAdmins, createAdmin, updateAdmin, deleteAdmin } from "../api/admin";

export function AdminManagement() {
  const [showAdd, setShowAdd] = useState(false);
  const [editingId, setEditingId] = useState<string | null>(null);
  const qc = useQueryClient();

  const { data: admins, isLoading, error } = useQuery({
    queryKey: ["admin-admins"],
    queryFn: getAdmins,
  });

  const createMutation = useMutation({
    mutationFn: (data: { username: string; password: string; display_name?: string; role: string }) => createAdmin(data),
    onSuccess: () => { qc.invalidateQueries({ queryKey: ["admin-admins"] }); setShowAdd(false); toast.success("管理员已创建"); },
    onError: (err: any) => toast.error(err?.response?.data?.message || "创建失败"),
  });

  const updateMutation = useMutation({
    mutationFn: ({ id, data }: { id: string; data: Record<string, any> }) => updateAdmin(id, data),
    onSuccess: () => { qc.invalidateQueries({ queryKey: ["admin-admins"] }); setEditingId(null); toast.success("已更新"); },
    onError: (err: any) => toast.error(err?.response?.data?.message || "更新失败"),
  });

  const deleteMutation = useMutation({
    mutationFn: (id: string) => deleteAdmin(id),
    onSuccess: () => { qc.invalidateQueries({ queryKey: ["admin-admins"] }); toast.success("管理员已删除"); },
    onError: (err: any) => toast.error(err?.response?.data?.message || "删除失败"),
  });

  const adminList = admins?.items || admins || [];

  return (
    <motion.div initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }} className="p-8 max-w-6xl mx-auto space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold text-slate-900">管理员管理</h1>
        <button
          onClick={() => setShowAdd(true)}
          className="flex items-center gap-2 bg-indigo-600 hover:bg-indigo-700 text-white rounded-xl px-4 py-2.5 font-semibold text-sm transition-colors"
        >
          <Plus size={16} /> 添加管理员
        </button>
      </div>

      {showAdd && (
        <AddAdminForm
          onSubmit={(data) => createMutation.mutate(data)}
          onCancel={() => setShowAdd(false)}
          loading={createMutation.isPending}
        />
      )}

      {isLoading ? (
        <div className="flex items-center justify-center py-20">
          <Loader2 className="animate-spin text-indigo-400" size={28} />
        </div>
      ) : error ? (
        <div className="bg-red-50 border border-red-200 rounded-2xl p-6 text-red-600">{(error as any)?.message || "加载失败"}</div>
      ) : adminList.length === 0 ? (
        <div className="bg-white border border-slate-200 rounded-2xl shadow-sm p-12 text-center">
          <Shield size={40} className="mx-auto text-slate-300 mb-3" />
          <p className="text-slate-400">暂无管理员</p>
        </div>
      ) : (
        <div className="bg-white border border-slate-200 rounded-2xl overflow-hidden shadow-sm">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-slate-200 bg-slate-50/50">
                <th className="text-left px-6 py-3 text-xs font-medium text-slate-500 uppercase">用户名</th>
                <th className="text-left px-6 py-3 text-xs font-medium text-slate-500 uppercase">显示名称</th>
                <th className="text-left px-6 py-3 text-xs font-medium text-slate-500 uppercase">角色</th>
                <th className="text-left px-6 py-3 text-xs font-medium text-slate-500 uppercase">状态</th>
                <th className="text-left px-6 py-3 text-xs font-medium text-slate-500 uppercase">最后登录</th>
                <th className="text-right px-6 py-3 text-xs font-medium text-slate-500 uppercase">操作</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100">
              {adminList.map((a: any) => (
                <tr key={a.id} className="hover:bg-slate-50/50 transition-colors">
                  <td className="px-6 py-4 font-medium text-slate-900">{a.username}</td>
                  <td className="px-6 py-4 text-slate-500">{a.display_name || "-"}</td>
                  <td className="px-6 py-4">
                    <span className={`px-2 py-0.5 rounded-full text-xs font-medium ${
                      a.role === "super_admin" ? "bg-purple-100 text-purple-700" : "bg-blue-100 text-blue-700"
                    }`}>
                      {a.role === "super_admin" ? "超级管理员" : a.role === "admin" ? "管理员" : a.role}
                    </span>
                  </td>
                  <td className="px-6 py-4">
                    <span className={`px-2 py-0.5 rounded-full text-xs font-medium ${
                      a.is_active !== false ? "bg-green-100 text-green-700" : "bg-red-100 text-red-700"
                    }`}>
                      {a.is_active !== false ? "正常" : "已禁用"}
                    </span>
                  </td>
                  <td className="px-6 py-4 text-slate-500 text-xs">
                    {a.last_login ? new Date(a.last_login).toLocaleString("zh-CN") : "-"}
                  </td>
                  <td className="px-6 py-4 text-right">
                    <div className="flex items-center justify-end gap-2">
                      <button
                        onClick={() => setEditingId(a.id)}
                        className="p-1.5 text-slate-400 hover:text-indigo-600 hover:bg-indigo-50 rounded-lg transition-colors"
                        title="编辑"
                      >
                        <Edit3 size={16} />
                      </button>
                      <button
                        onClick={() => { if (window.confirm("确定要删除这个管理员吗？")) deleteMutation.mutate(a.id); }}
                        disabled={deleteMutation.isPending}
                        className="p-1.5 text-slate-400 hover:text-red-600 hover:bg-red-50 rounded-lg transition-colors disabled:opacity-50"
                        title="删除"
                      >
                        <Trash2 size={16} />
                      </button>
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {editingId && (
        <EditAdminModal
          admin={adminList.find((a: any) => a.id === editingId)}
          onSubmit={(data) => updateMutation.mutate({ id: editingId, data })}
          onCancel={() => setEditingId(null)}
          loading={updateMutation.isPending}
        />
      )}
    </motion.div>
  );
}

function AddAdminForm({
  onSubmit,
  onCancel,
  loading,
}: {
  onSubmit: (data: { username: string; password: string; display_name?: string; role: string }) => void;
  onCancel: () => void;
  loading: boolean;
}) {
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [displayName, setDisplayName] = useState("");
  const [role, setRole] = useState("admin");

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!username.trim() || !password.trim()) { toast.error("请填写必填字段"); return; }
    onSubmit({ username, password, display_name: displayName || undefined, role });
  };

  return (
    <motion.div
      initial={{ opacity: 0, scale: 0.98 }}
      animate={{ opacity: 1, scale: 1 }}
      className="bg-white border border-slate-200 rounded-2xl shadow-sm p-6 space-y-4"
    >
      <div className="flex items-center justify-between">
        <h2 className="text-lg font-semibold text-slate-900">添加管理员</h2>
        <button onClick={onCancel} className="p-1 text-slate-400 hover:text-slate-600"><X size={18} /></button>
      </div>
      <form onSubmit={handleSubmit} className="space-y-4">
        <div className="grid grid-cols-2 gap-4">
          <div>
            <label className="block text-sm font-medium text-slate-700 mb-1.5">用户名 *</label>
            <input
              type="text" value={username} onChange={(e) => setUsername(e.target.value)}
              placeholder="用户名"
              className="w-full border border-slate-200 rounded-xl px-4 py-3 focus:ring-2 focus:ring-indigo-500 outline-none text-sm"
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-slate-700 mb-1.5">密码 *</label>
            <input
              type="password" value={password} onChange={(e) => setPassword(e.target.value)}
              placeholder="密码"
              className="w-full border border-slate-200 rounded-xl px-4 py-3 focus:ring-2 focus:ring-indigo-500 outline-none text-sm"
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-slate-700 mb-1.5">显示名称</label>
            <input
              type="text" value={displayName} onChange={(e) => setDisplayName(e.target.value)}
              placeholder="显示名称（可选）"
              className="w-full border border-slate-200 rounded-xl px-4 py-3 focus:ring-2 focus:ring-indigo-500 outline-none text-sm"
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-slate-700 mb-1.5">角色</label>
            <select
              value={role} onChange={(e) => setRole(e.target.value)}
              className="w-full border border-slate-200 rounded-xl px-4 py-3 focus:ring-2 focus:ring-indigo-500 outline-none text-sm appearance-none bg-white"
            >
              <option value="admin">管理员</option>
              <option value="super_admin">超级管理员</option>
            </select>
          </div>
        </div>
        <div className="flex justify-end gap-3 pt-2">
          <button type="button" onClick={onCancel} className="px-4 py-2 text-sm font-medium text-slate-600 hover:bg-slate-50 rounded-xl transition-colors">取消</button>
          <button type="submit" disabled={loading} className="px-4 py-2 bg-indigo-600 hover:bg-indigo-700 text-white rounded-xl text-sm font-semibold transition-colors disabled:opacity-50">{loading ? "创建中..." : "创建"}</button>
        </div>
      </form>
    </motion.div>
  );
}

function EditAdminModal({
  admin,
  onSubmit,
  onCancel,
  loading,
}: {
  admin: any;
  onSubmit: (data: Record<string, any>) => void;
  onCancel: () => void;
  loading: boolean;
}) {
  const [displayName, setDisplayName] = useState(admin?.display_name || "");
  const [role, setRole] = useState(admin?.role || "admin");
  const [isActive, setIsActive] = useState(admin?.is_active !== false);
  const [newPassword, setNewPassword] = useState("");

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    const data: Record<string, any> = { display_name: displayName || undefined, role, is_active: isActive };
    if (newPassword.trim()) data.password = newPassword;
    onSubmit(data);
  };

  return (
    <div className="fixed inset-0 bg-black/20 flex items-center justify-center z-50">
      <motion.div
        initial={{ opacity: 0, scale: 0.95 }}
        animate={{ opacity: 1, scale: 1 }}
        className="bg-white border border-slate-200 rounded-2xl shadow-xl p-6 w-full max-w-md space-y-4"
      >
        <div className="flex items-center justify-between">
          <h2 className="text-lg font-semibold text-slate-900">编辑管理员 - {admin?.username}</h2>
          <button onClick={onCancel} className="p-1 text-slate-400 hover:text-slate-600"><X size={18} /></button>
        </div>
        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label className="block text-sm font-medium text-slate-700 mb-1.5">显示名称</label>
            <input
              type="text" value={displayName} onChange={(e) => setDisplayName(e.target.value)}
              className="w-full border border-slate-200 rounded-xl px-4 py-3 focus:ring-2 focus:ring-indigo-500 outline-none text-sm"
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-slate-700 mb-1.5">角色</label>
            <select
              value={role} onChange={(e) => setRole(e.target.value)}
              className="w-full border border-slate-200 rounded-xl px-4 py-3 focus:ring-2 focus:ring-indigo-500 outline-none text-sm appearance-none bg-white"
            >
              <option value="admin">管理员</option>
              <option value="super_admin">超级管理员</option>
            </select>
          </div>
          <div>
            <label className="block text-sm font-medium text-slate-700 mb-1.5">新密码（留空不修改）</label>
            <input
              type="password" value={newPassword} onChange={(e) => setNewPassword(e.target.value)}
              placeholder="输入新密码"
              className="w-full border border-slate-200 rounded-xl px-4 py-3 focus:ring-2 focus:ring-indigo-500 outline-none text-sm"
            />
          </div>
          <label className="flex items-center gap-3 cursor-pointer">
            <input
              type="checkbox" checked={isActive} onChange={(e) => setIsActive(e.target.checked)}
              className="w-4 h-4 rounded border-slate-300 text-indigo-600 focus:ring-indigo-500"
            />
            <span className="text-sm text-slate-700">账号启用</span>
          </label>
          <div className="flex justify-end gap-3 pt-2">
            <button type="button" onClick={onCancel} className="px-4 py-2 text-sm font-medium text-slate-600 hover:bg-slate-50 rounded-xl transition-colors">取消</button>
            <button type="submit" disabled={loading} className="px-4 py-2 bg-indigo-600 hover:bg-indigo-700 text-white rounded-xl text-sm font-semibold transition-colors disabled:opacity-50">{loading ? "保存中..." : "保存"}</button>
          </div>
        </form>
      </motion.div>
    </div>
  );
}
