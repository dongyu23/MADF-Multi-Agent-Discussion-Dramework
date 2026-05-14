import { useState } from "react";
import { Link } from "react-router";
import { Search, Sparkles, Filter, Copy, Eye } from "lucide-react";
import { motion } from "motion/react";
import { toast } from "sonner";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { getGallery, copyCharacter } from "../api/characters";

export function Gallery() {
  const queryClient = useQueryClient();
  const [search, setSearch] = useState("");
  const [searchTerm, setSearchTerm] = useState("");

  const { data: characters = [], isLoading } = useQuery({
    queryKey: ["gallery", searchTerm],
    queryFn: () => getGallery(searchTerm || undefined).then(d => d.items || []),
    staleTime: 30_000,
  });

  const copyMutation = useMutation({
    mutationFn: copyCharacter,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["characters"] });
      toast.success("复制成功！", { description: `角色已保存到"我的角色"列表中` });
    },
    onError: (err: any) => toast.error(err.response?.data?.message || "复制失败"),
  });

  const handleSearch = (e: React.FormEvent) => {
    e.preventDefault();
    setSearchTerm(search);
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
          <h1 className="text-2xl font-bold text-slate-900">技能画廊</h1>
          <p className="text-slate-500 mt-1">发现并复制公共智能体技能</p>
        </div>
      </div>

      <form onSubmit={handleSearch} className="flex gap-4">
        <div className="relative flex-1 max-w-md">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-400 w-5 h-5" />
          <input
            type="text"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            placeholder="按名称或标签搜索角色..."
            className="w-full pl-10 pr-4 py-2 border border-slate-200 rounded-xl focus:ring-2 focus:ring-indigo-600 outline-none transition-shadow"
          />
        </div>
        <button type="submit" className="flex items-center gap-2 px-4 py-2 border border-slate-200 bg-white rounded-xl text-slate-700 hover:bg-slate-50 transition-colors font-medium">
          <Filter size={18} />
          搜索
        </button>
      </form>

      {characters.length === 0 ? (
        <div className="text-center py-16 text-slate-400">
          <p className="text-lg mb-2">画廊暂无角色</p>
          <p>去"我的角色"页面生成并公开角色吧</p>
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {characters.map((char: any, i: number) => (
            <motion.div
              key={char.id}
              initial={{ opacity: 0, scale: 0.95 }}
              animate={{ opacity: 1, scale: 1 }}
              transition={{ delay: i * 0.05 }}
              className="bg-white border border-slate-200 rounded-2xl p-6 hover:shadow-md transition-shadow group flex flex-col"
            >
              <div className="flex items-start justify-between mb-4">
                <div className="w-12 h-12 bg-indigo-50 text-indigo-600 rounded-xl flex items-center justify-center font-bold text-lg">
                  {char.name.charAt(0)}
                </div>
                <div className="flex gap-2">
                  <Link to={`/gallery/${char.id}/view`} className="p-2 text-slate-400 hover:text-indigo-600 hover:bg-indigo-50 rounded-lg transition-colors" title="查看详情">
                    <Eye size={18} />
                  </Link>
                  <button
                    onClick={() => copyMutation.mutate(char.id)}
                    className="p-2 text-slate-400 hover:text-indigo-600 hover:bg-indigo-50 rounded-lg transition-colors"
                    title="复制到我的角色"
                  >
                    <Copy size={18} />
                  </button>
                </div>
              </div>
              <h3 className="font-bold text-lg text-slate-900 mb-2">{char.name}</h3>
              <p className="text-slate-500 text-sm flex-1">{char.description || "暂无描述"}</p>
              <div className="mt-6 flex items-center justify-between pt-4 border-t border-slate-100 text-xs font-medium text-slate-500">
                <span>{char.tags?.slice(0, 3).join(", ") || "无标签"}</span>
                <span className="flex items-center gap-1"><Sparkles size={14} className="text-indigo-500" /> 就绪</span>
              </div>
            </motion.div>
          ))}
        </div>
      )}
    </div>
  );
}
