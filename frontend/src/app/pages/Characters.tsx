import { Link, useNavigate } from "react-router";
import { Plus, Trash2, Globe } from "lucide-react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { getMyCharacters, deleteCharacter, updateCharacter, type CharacterItem } from "../api/characters";
import { toast } from "sonner";

export function Characters() {
  const navigate = useNavigate();
  const queryClient = useQueryClient();

  const { data: characters = [], isLoading } = useQuery({
    queryKey: ["characters"],
    queryFn: () => getMyCharacters().then(d => d.items || []),
    staleTime: 20_000,
  });

  const deleteMutation = useMutation({
    mutationFn: deleteCharacter,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["characters"] });
      queryClient.invalidateQueries({ queryKey: ["gallery"] });
      toast.success("已删除");
    },
    onError: (err: any) => toast.error(err.response?.data?.message || "删除失败"),
  });

  const togglePublicMutation = useMutation({
    mutationFn: ({ id, isPublic }: { id: string; isPublic: boolean }) =>
      updateCharacter(id, { is_public: isPublic }),
    onSuccess: (_data, vars) => {
      queryClient.invalidateQueries({ queryKey: ["characters"] });
      queryClient.invalidateQueries({ queryKey: ["gallery"] });
      toast.success(vars.isPublic ? "已公开到画廊" : "已取消公开");
    },
    onError: (err: any) => toast.error(err.response?.data?.message || "操作失败"),
  });

  const statusLabel = (s: string) => {
    const map: Record<string, string> = { ready: "就绪", generating: "生成中", error: "错误" };
    return map[s] || s;
  };

  if (isLoading) {
    return (
      <div className="p-8 max-w-7xl mx-auto">
        <div className="animate-pulse space-y-4">
          <div className="h-8 bg-slate-200 rounded w-48" />
          <div className="h-64 bg-slate-200 rounded-2xl" />
        </div>
      </div>
    );
  }

  return (
    <div className="p-8 max-w-7xl mx-auto space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-slate-900">我的角色</h1>
          <p className="text-slate-500 mt-1">管理您自定义的智能体技能</p>
        </div>
        <Link
          to="/characters/generate"
          className="flex items-center gap-2 bg-indigo-600 text-white px-5 py-2.5 rounded-xl font-medium hover:bg-indigo-700 transition-colors shadow-sm"
        >
          <Plus size={18} />
          生成新角色
        </Link>
      </div>

      <div className="bg-white border border-slate-200 rounded-2xl overflow-hidden shadow-sm">
        {characters.length === 0 ? (
          <div className="p-12 text-center text-slate-400">
            <p className="text-lg mb-2">还没有角色</p>
            <p>点击"生成新角色"开始创建你的第一个 AI 角色</p>
          </div>
        ) : (
          <table className="w-full text-left border-collapse">
            <thead>
              <tr className="bg-slate-50 text-sm font-medium text-slate-500">
                <th className="p-4">名称</th>
                <th className="p-4">描述</th>
                <th className="p-4">状态</th>
                <th className="p-4">公开</th>
                <th className="p-4 text-right">操作</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100">
              {characters.map((char: CharacterItem) => (
                <tr
                  key={char.id}
                  className="hover:bg-slate-50 transition-colors group cursor-pointer"
                  onClick={() => navigate(`/characters/${char.id}`)}
                >
                  <td className="p-4">
                    <div className="font-semibold text-slate-900 flex items-center gap-3 hover:text-indigo-600 transition-colors">
                      <div className="w-8 h-8 rounded-lg bg-indigo-100 text-indigo-700 flex items-center justify-center text-xs font-bold">
                        {char.name.charAt(0)}
                      </div>
                      {char.name}
                    </div>
                  </td>
                  <td className="p-4 text-slate-500 text-sm max-w-xs truncate">{char.description || "-"}</td>
                  <td className="p-4">
                    <span className={`inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-medium ${
                      char.status === "ready" ? "bg-green-100 text-green-700"
                      : char.status === "generating" ? "bg-amber-100 text-amber-700"
                      : "bg-red-100 text-red-700"
                    }`}>
                      {char.status === "generating" && <span className="w-2 h-2 rounded-full bg-amber-500 animate-pulse" />}
                      {statusLabel(char.status)}
                    </span>
                  </td>
                  <td className="p-4 text-sm text-slate-500">{char.is_public ? "公开" : "私有"}</td>
                  <td className="p-4 text-right">
                    <div className="flex items-center justify-end gap-2 opacity-0 group-hover:opacity-100 transition-opacity" onClick={(e) => e.stopPropagation()}>
                      <button
                        className="p-2 text-slate-400 hover:text-indigo-600 hover:bg-indigo-50 rounded-lg transition-colors"
                        title={char.is_public ? "取消公开" : "公开到画廊"}
                        onClick={() => togglePublicMutation.mutate({ id: char.id, isPublic: !char.is_public })}
                      >
                        <Globe size={18} />
                      </button>
                      <button
                        className="p-2 text-slate-400 hover:text-red-600 hover:bg-red-50 rounded-lg transition-colors"
                        title="删除"
                        onClick={() => { if (confirm("确定要删除？")) deleteMutation.mutate(char.id); }}
                      >
                        <Trash2 size={18} />
                      </button>
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>
    </div>
  );
}
