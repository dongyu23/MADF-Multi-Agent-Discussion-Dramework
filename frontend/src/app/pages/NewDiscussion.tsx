import { useState } from "react";
import { Link, useNavigate } from "react-router";
import { ArrowLeft, Play, Users, Clock, Hash } from "lucide-react";
import { motion } from "motion/react";
import { toast } from "sonner";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { getMyCharacters } from "../api/characters";
import { createDiscussion } from "../api/discussions";

export function NewDiscussion() {
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const [topic, setTopic] = useState("");
  const [duration, setDuration] = useState(120);
  const [selectedIds, setSelectedIds] = useState<string[]>([]);

  const { data: agents = [] } = useQuery({
    queryKey: ["characters"],
    queryFn: () => getMyCharacters().then(d => (d.items || []).filter((c: any) => c.status === "ready")),
    staleTime: 30_000,
  });

  const createMutation = useMutation({
    mutationFn: () => createDiscussion(topic.trim(), selectedIds, duration),
    onSuccess: (data) => {
      queryClient.invalidateQueries({ queryKey: ["discussions"] });
      toast.success("讨论已创建");
      navigate(`/discussions/${data.id}`);
    },
    onError: (err: any) => toast.error(err.response?.data?.message || "创建失败"),
  });

  const toggleAgent = (id: string) => {
    setSelectedIds((prev) => (prev.includes(id) ? prev.filter((a) => a !== id) : [...prev, id]));
  };

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!topic.trim() || selectedIds.length < 2) {
      toast.error("请填写主题并至少选择 2 位参与者");
      return;
    }
    createMutation.mutate();
  };

  return (
    <div className="p-8 max-w-3xl mx-auto space-y-6">
      <div className="flex items-center gap-4">
        <Link to="/discussions" className="w-10 h-10 bg-white border border-slate-200 rounded-full flex items-center justify-center text-slate-500 hover:text-slate-900 transition-colors shadow-sm">
          <ArrowLeft size={20} />
        </Link>
        <div>
          <h1 className="text-2xl font-bold text-slate-900">创建圆桌讨论</h1>
          <p className="text-slate-500 mt-1">设置讨论主题、时长和参与者</p>
        </div>
      </div>

      <motion.form initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} onSubmit={handleSubmit} className="bg-white border border-slate-200 rounded-3xl p-8 shadow-sm space-y-8">
        <div className="space-y-6">
          <div>
            <label className="flex items-center gap-2 text-sm font-bold text-slate-900 mb-2">
              <Hash size={16} className="text-indigo-500" /> 讨论主题
            </label>
            <input type="text" required value={topic} onChange={(e) => setTopic(e.target.value)}
              className="w-full px-4 py-3 border border-slate-200 rounded-xl focus:ring-2 focus:ring-indigo-600 outline-none text-lg placeholder-slate-300"
              placeholder="你想讨论什么主题？" />
          </div>
          <div>
            <label className="flex items-center gap-2 text-sm font-bold text-slate-900 mb-2">
              <Clock size={16} className="text-indigo-500" /> 讨论时长
            </label>
            <select value={duration} onChange={(e) => setDuration(Number(e.target.value))}
              className="w-full px-4 py-3 border border-slate-200 rounded-xl focus:ring-2 focus:ring-indigo-600 outline-none text-slate-700 bg-white">
              <option value={60}>1 分钟</option>
              <option value={120}>2 分钟</option>
              <option value={300}>5 分钟</option>
              <option value={600}>10 分钟</option>
              <option value={1800}>30 分钟</option>
            </select>
          </div>
          <div>
            <label className="flex items-center gap-2 text-sm font-bold text-slate-900 mb-3">
              <Users size={16} className="text-indigo-500" /> 选择参与者（已选 {selectedIds.length} 位）
            </label>
            {agents.length === 0 ? (
              <p className="text-slate-400 text-sm">暂无可用的就绪角色，请先生成角色</p>
            ) : (
              <div className="border border-slate-200 rounded-xl max-h-60 overflow-y-auto">
                <div className="p-2 space-y-1">
                  {agents.map((agent: any) => {
                    const isSelected = selectedIds.includes(agent.id);
                    return (
                      <div key={agent.id} onClick={() => toggleAgent(agent.id)}
                        className={`cursor-pointer flex items-center p-3 rounded-lg transition-all ${isSelected ? "bg-indigo-50/50" : "hover:bg-slate-50"}`}>
                        <div className="flex-1 flex items-center gap-3">
                          <div className={`w-8 h-8 rounded-full flex items-center justify-center font-bold text-sm ${isSelected ? "bg-indigo-600 text-white" : "bg-slate-100 text-slate-600"}`}>
                            {agent.name.charAt(0)}
                          </div>
                          <div>
                            <div className={`font-semibold text-sm ${isSelected ? "text-indigo-900" : "text-slate-900"}`}>{agent.name}</div>
                            <div className={`text-xs ${isSelected ? "text-indigo-600/80" : "text-slate-500"}`}>{agent.description?.slice(0, 40) || "暂无描述"}</div>
                          </div>
                        </div>
                        <div className={`w-5 h-5 rounded border flex items-center justify-center ${isSelected ? "border-indigo-600 bg-indigo-600" : "border-slate-300"}`}>
                          {isSelected && (
                            <svg className="w-3.5 h-3.5 text-white" viewBox="0 0 20 20" fill="currentColor">
                              <path fillRule="evenodd" d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z" clipRule="evenodd" />
                            </svg>
                          )}
                        </div>
                      </div>
                    );
                  })}
                </div>
              </div>
            )}
          </div>
        </div>
        <div className="pt-6 border-t border-slate-100 flex justify-end">
          <button type="submit" disabled={selectedIds.length < 2 || createMutation.isPending}
            className="bg-indigo-600 hover:bg-indigo-700 disabled:opacity-50 disabled:cursor-not-allowed text-white px-8 py-3.5 rounded-xl font-bold text-lg flex items-center gap-3 transition-colors shadow-md">
            <Play size={20} />
            {createMutation.isPending ? "创建中..." : "开始讨论"}
          </button>
        </div>
      </motion.form>
    </div>
  );
}
