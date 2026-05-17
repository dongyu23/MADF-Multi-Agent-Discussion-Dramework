import { useState, useEffect, useRef } from "react";
import { Link, useNavigate } from "react-router";
import { ArrowLeft, Play, Users, Clock, Hash, ChevronDown, Shuffle, Sparkles } from "lucide-react";
import { motion } from "motion/react";
import { toast } from "sonner";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { getMyCharacters } from "../api/characters";
import { createDiscussion, generateTopic } from "../api/discussions";

const TOPIC_KEY = "madf_topic_cache";

function loadCachedTopic() {
  try {
    const raw = sessionStorage.getItem(TOPIC_KEY);
    if (raw) return raw;
  } catch { /* ignore */ }
  return "";
}

function saveCachedTopic(t: string) {
  try { sessionStorage.setItem(TOPIC_KEY, t); } catch { /* ignore */ }
}

export function NewDiscussion() {
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const [topic, setTopic] = useState("");
  const [duration, setDuration] = useState("10");
  const [customDuration, setCustomDuration] = useState("");
  const [selectedIds, setSelectedIds] = useState<string[]>([]);
  const [dropdownOpen, setDropdownOpen] = useState(false);
  const [genTopic, setGenTopic] = useState(loadCachedTopic);
  const [genLoading, setGenLoading] = useState(!genTopic);
  const dropdownRef = useRef<HTMLDivElement>(null);

  const { data: allChars = [] } = useQuery({
    queryKey: ["characters"],
    queryFn: () => getMyCharacters().then(d => d.items || []),
    staleTime: 30_000,
  });
  const agents = allChars.filter((c: any) => c.status === "ready");

  const createMutation = useMutation({
    mutationFn: () => createDiscussion(topic.trim(), selectedIds, getDurationSeconds()),
    onSuccess: (data) => {
      queryClient.invalidateQueries({ queryKey: ["discussions"] });
      toast.success("讨论已创建");
      navigate(`/discussions/${data.id}`);
    },
    onError: (err: any) => toast.error(err.response?.data?.message || "创建失败"),
  });

  const getDurationSeconds = () => {
    const mins = customDuration ? parseInt(customDuration) : parseInt(duration);
    return (isNaN(mins) || mins < 1 ? 10 : mins) * 60;
  };

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

  const fetchGenTopic = async () => {
    setGenLoading(true);
    try {
      const t = await generateTopic();
      setGenTopic(t);
      saveCachedTopic(t);
    } catch {
      // silent fallback
    } finally {
      setGenLoading(false);
    }
  };

  useEffect(() => {
    if (!genTopic) fetchGenTopic();
    const handler = (e: MouseEvent) => {
      if (dropdownRef.current && !dropdownRef.current.contains(e.target as Node)) {
        setDropdownOpen(false);
      }
    };
    document.addEventListener("mousedown", handler);
    return () => document.removeEventListener("mousedown", handler);
  }, []);

  const selectedAgents = agents.filter((a: any) => selectedIds.includes(a.id));

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
        {/* ── AI Topic Generation ── */}
        <div className="bg-indigo-50/50 border border-indigo-100 rounded-2xl p-5">
          <div className="flex items-center justify-between mb-3">
            <span className="text-sm font-semibold text-indigo-800 flex items-center gap-2">
              <Sparkles size={16} className="text-indigo-500" />
              AI 推荐主题
            </span>
            <button
              type="button"
              onClick={fetchGenTopic}
              disabled={genLoading}
              className="flex items-center gap-1.5 text-xs font-medium text-indigo-600 hover:text-indigo-800 transition-colors disabled:opacity-50"
            >
              <Shuffle size={14} />
              换一个
            </button>
          </div>
          {genLoading ? (
            <div className="h-12 bg-indigo-100/50 rounded-xl animate-pulse" />
          ) : (
            <button
              type="button"
              onClick={() => setTopic(genTopic)}
              className="w-full text-left p-3 bg-white border border-indigo-200 rounded-xl text-slate-800 text-sm hover:border-indigo-400 hover:bg-indigo-50/30 transition-all cursor-pointer"
            >
              {genTopic}
            </button>
          )}
        </div>

        {/* ── Row 1: Topic + Duration ── */}
        <div className="grid grid-cols-1 md:grid-cols-5 gap-6">
          <div className="md:col-span-3">
            <label className="flex items-center gap-2 text-sm font-bold text-slate-900 mb-2">
              <Hash size={16} className="text-indigo-500" /> 讨论主题
            </label>
            <input
              type="text"
              required
              value={topic}
              onChange={(e) => setTopic(e.target.value)}
              className="w-full px-4 py-3 border border-slate-200 rounded-xl focus:ring-2 focus:ring-indigo-600 outline-none text-lg placeholder-slate-300"
              placeholder="你想讨论什么主题？"
            />
          </div>
          <div className="md:col-span-2">
            <label className="flex items-center gap-2 text-sm font-bold text-slate-900 mb-2">
              <Clock size={16} className="text-indigo-500" /> 讨论时长
            </label>
            <div className="flex gap-2">
              <select
                value={customDuration ? "__custom" : duration}
                onChange={(e) => {
                  const v = e.target.value;
                  if (v === "__custom") { setCustomDuration("15"); setDuration("__custom"); }
                  else { setCustomDuration(""); setDuration(v); }
                }}
                className="flex-1 px-3 py-3 border border-slate-200 rounded-xl focus:ring-2 focus:ring-indigo-600 outline-none text-slate-700 bg-white"
              >
                <option value="1">1 分钟</option>
                <option value="2">2 分钟</option>
                <option value="5">5 分钟</option>
                <option value="10">10 分钟</option>
                <option value="30">30 分钟</option>
                <option value="__custom">自定义...</option>
              </select>
              {customDuration && (
                <div className="relative w-24">
                  <input
                    type="number"
                    min={1}
                    max={60}
                    value={customDuration}
                    onChange={(e) => setCustomDuration(e.target.value)}
                    className="w-full px-3 py-3 border border-slate-200 rounded-xl focus:ring-2 focus:ring-indigo-600 outline-none text-slate-700"
                    placeholder="分钟"
                  />
                  <span className="absolute right-3 top-1/2 -translate-y-1/2 text-xs text-slate-400 pointer-events-none">分</span>
                </div>
              )}
            </div>
          </div>
        </div>

        {/* ── Row 2: Participant Dropdown ── */}
        <div ref={dropdownRef}>
          <label className="flex items-center gap-2 text-sm font-bold text-slate-900 mb-2">
            <Users size={16} className="text-indigo-500" /> 选择参与者（已选 {selectedIds.length} 位）
          </label>

          {agents.length === 0 ? (
            <p className="text-slate-400 text-sm">暂无可用的就绪角色，请先生成角色</p>
          ) : (
            <div className="relative">
              {/* Selected chips + toggle */}
              <button
                type="button"
                onClick={() => setDropdownOpen(!dropdownOpen)}
                className="w-full flex items-center justify-between px-4 py-3 border border-slate-200 rounded-xl bg-white hover:border-slate-300 transition-colors text-left"
              >
                <div className="flex items-center gap-2 flex-wrap">
                  {selectedAgents.length === 0 ? (
                    <span className="text-slate-400 text-sm">点击选择参与讨论的角色...</span>
                  ) : (
                    selectedAgents.map((a: any) => (
                      <span key={a.id} className="inline-flex items-center gap-1 px-2.5 py-1 bg-indigo-50 text-indigo-700 text-xs font-medium rounded-lg">
                        {a.name}
                        <button
                          type="button"
                          onClick={(e) => { e.stopPropagation(); toggleAgent(a.id); }}
                          className="ml-0.5 hover:text-indigo-900"
                        >
                          ×
                        </button>
                      </span>
                    ))
                  )}
                </div>
                <ChevronDown size={18} className={`text-slate-400 transition-transform shrink-0 ${dropdownOpen ? "rotate-180" : ""}`} />
              </button>

              {/* Dropdown list */}
              {dropdownOpen && (
                <div className="absolute z-20 mt-1 w-full border border-slate-200 rounded-xl bg-white shadow-lg max-h-56 overflow-y-auto">
                  <div className="p-2 space-y-1">
                    {agents.map((agent: any) => {
                      const isSelected = selectedIds.includes(agent.id);
                      return (
                        <div
                          key={agent.id}
                          onClick={() => toggleAgent(agent.id)}
                          className={`cursor-pointer flex items-center p-2.5 rounded-lg transition-all ${isSelected ? "bg-indigo-50/50" : "hover:bg-slate-50"}`}
                        >
                          <div className="flex-1 flex items-center gap-3 min-w-0">
                            <div className={`w-8 h-8 rounded-full flex items-center justify-center font-bold text-sm shrink-0 ${isSelected ? "bg-indigo-600 text-white" : "bg-slate-100 text-slate-600"}`}>
                              {agent.name.charAt(0)}
                            </div>
                            <div className="min-w-0">
                              <div className={`font-semibold text-sm truncate ${isSelected ? "text-indigo-900" : "text-slate-900"}`}>{agent.name}</div>
                              <div className="text-xs text-slate-500 truncate">{agent.description?.slice(0, 30) || "暂无描述"}</div>
                            </div>
                          </div>
                          <div className={`w-5 h-5 rounded border flex items-center justify-center shrink-0 ml-2 ${isSelected ? "border-indigo-600 bg-indigo-600" : "border-slate-300"}`}>
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
          )}
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
