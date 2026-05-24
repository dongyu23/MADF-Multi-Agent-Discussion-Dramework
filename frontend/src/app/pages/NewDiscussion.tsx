import { useState, useEffect, useRef } from "react";
import { Link, useNavigate } from "react-router";
import { ArrowLeft, ChevronDown, Clock, Hash, Play, Shuffle, Sparkles, Users } from "lucide-react";
import { motion } from "motion/react";
import { toast } from "sonner";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { getMyCharacters } from "../api/characters";
import { createDiscussion, generateTopic } from "../api/discussions";

const TOPIC_KEY = "madf_topic_cache";
const FALLBACK_TOPICS = [
  "AI 与人类是否应共享同一套社会伦理与法律体系",
  "大学生如何在 AI 时代建立不可替代的学习能力",
  "多智能体讨论能否提升课堂辩论和论文选题质量",
  "自动化工具普及后，个人创造力会被削弱还是放大",
];

function pickFallbackTopic() {
  return FALLBACK_TOPICS[Math.floor(Math.random() * FALLBACK_TOPICS.length)];
}

function normalizeTopic(value: unknown) {
  if (typeof value === "string") return value.trim();
  if (value && typeof value === "object") {
    const record = value as Record<string, unknown>;
    const topic = record.topic || record.title || record.content;
    if (typeof topic === "string") return topic.trim();
  }
  return "";
}

function loadCachedTopic() {
  try {
    const raw = sessionStorage.getItem(TOPIC_KEY);
    if (raw) return raw;
  } catch { /* ignore */ }
  return "";
}

function saveCachedTopic(topic: string) {
  try {
    sessionStorage.setItem(TOPIC_KEY, topic);
  } catch { /* ignore */ }
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
  const [genTopicSource, setGenTopicSource] = useState<"ai" | "fallback">(genTopic ? "ai" : "fallback");
  const [genLoading, setGenLoading] = useState(!genTopic);
  const dropdownRef = useRef<HTMLDivElement>(null);

  const { data: allChars = [] } = useQuery({
    queryKey: ["characters"],
    queryFn: () => getMyCharacters().then((d) => d.items || []),
    staleTime: 30_000,
  });
  const agents = allChars.filter((item: any) => item.status === "ready");
  const selectedAgents = agents.filter((item: any) => selectedIds.includes(item.id));

  const getDurationSeconds = () => {
    const minutes = customDuration ? parseInt(customDuration) : parseInt(duration);
    return (isNaN(minutes) || minutes < 1 ? 10 : minutes) * 60;
  };

  const createMutation = useMutation({
    mutationFn: () => createDiscussion(topic.trim(), selectedIds, getDurationSeconds()),
    onSuccess: (data) => {
      queryClient.invalidateQueries({ queryKey: ["discussions"] });
      toast.success("讨论已创建");
      navigate(`/discussions/${data.id}`);
    },
    onError: (err: any) => toast.error(err.response?.data?.message || "创建失败"),
  });

  const toggleAgent = (id: string) => {
    setSelectedIds((prev) => (prev.includes(id) ? prev.filter((item) => item !== id) : [...prev, id]));
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
      const nextTopic = normalizeTopic(await generateTopic()) || pickFallbackTopic();
      setGenTopic(nextTopic);
      saveCachedTopic(nextTopic);
      setGenTopicSource("ai");
    } catch {
      const fallbackTopic = pickFallbackTopic();
      setGenTopic(fallbackTopic);
      setGenTopicSource("fallback");
    } finally {
      setGenLoading(false);
    }
  };

  useEffect(() => {
    if (!genTopic) fetchGenTopic();
    const handler = (event: MouseEvent) => {
      if (dropdownRef.current && !dropdownRef.current.contains(event.target as Node)) {
        setDropdownOpen(false);
      }
    };
    document.addEventListener("mousedown", handler);
    return () => document.removeEventListener("mousedown", handler);
  }, []);

  return (
    <div className="relative min-h-full overflow-hidden bg-[#f6f3ec] text-[#1d1a16]">
      <div className="pointer-events-none absolute inset-0 bg-[linear-gradient(90deg,rgba(29,26,22,0.045)_1px,transparent_1px),linear-gradient(rgba(29,26,22,0.045)_1px,transparent_1px)] bg-[size:48px_48px]" />
      <div className="relative mx-auto flex w-full max-w-5xl flex-col gap-6 px-4 py-6 sm:px-6 lg:px-8">
        <header className="flex items-center gap-4 border-b border-[#d8cbb7] pb-6">
          <Link to="/discussions" className="flex h-10 w-10 shrink-0 items-center justify-center rounded-lg border border-[#d8cbb7] bg-[#fffdf7] text-[#6d6254] transition hover:bg-[#e9dfcc] hover:text-[#1d1a16]">
            <ArrowLeft size={20} />
          </Link>
          <div>
            <p className="text-xs font-semibold uppercase tracking-[0.24em] text-[#8a6b37]">Roundtable Setup</p>
            <h1 className="mt-2 font-['Noto_Serif_SC'] text-3xl font-semibold leading-tight md:text-4xl">创建圆桌讨论</h1>
            <p className="mt-2 text-sm leading-6 text-[#6d6254]">设置主题、时长和参与者，启动一场可回放的多智能体讨论。</p>
          </div>
        </header>

        <motion.form
          initial={{ opacity: 0, y: 10 }}
          animate={{ opacity: 1, y: 0 }}
          onSubmit={handleSubmit}
          className="rounded-lg border border-[#d8cbb7] bg-[#fffdf7] p-5 shadow-[0_18px_56px_rgba(53,45,32,0.1)] sm:p-8"
        >
          <div className="rounded-lg border border-[#d8cbb7] bg-[#f9f4e9] p-4 sm:p-5">
            <div className="mb-3 flex flex-wrap items-center justify-between gap-3">
              <span className="flex items-center gap-2 text-sm font-semibold text-[#1d1a16]">
                <Sparkles size={16} />
                AI 推荐主题
              </span>
              <button type="button" onClick={fetchGenTopic} disabled={genLoading} className="inline-flex items-center gap-1.5 rounded-lg border border-[#d8cbb7] bg-[#fffdf7] px-3 py-1.5 text-xs font-semibold text-[#6d6254] transition hover:border-[#207362] hover:text-[#185f51] disabled:opacity-50">
                <Shuffle size={14} />
                换一个
              </button>
            </div>
            {genLoading ? (
              <div className="flex min-h-14 items-center rounded-lg border border-dashed border-[#cdbfa9] bg-[#fffdf7] px-4 text-sm text-[#9a8b76]">
                正在生成推荐主题...
              </div>
            ) : (
              <button
                type="button"
                onClick={() => setTopic(genTopic)}
                className="group grid w-full grid-cols-[minmax(0,1fr)_auto] items-center gap-3 rounded-lg border border-[#d8cbb7] bg-[#fffdf7] p-4 text-left transition hover:border-[#207362] hover:shadow-[0_10px_28px_rgba(53,45,32,0.08)]"
              >
                <span className="min-w-0 text-sm font-semibold leading-6 text-[#1d1a16]">
                  {genTopic || pickFallbackTopic()}
                </span>
                <span className="rounded-lg border border-[#207362]/25 bg-[#207362]/10 px-2 py-1 text-[11px] font-semibold text-[#185f51]">
                  {genTopicSource === "ai" ? "AI" : "备选"}
                </span>
              </button>
            )}
          </div>

          <div className="mt-7 grid gap-6 md:grid-cols-5">
            <div className="md:col-span-3">
              <label className="mb-2 flex items-center gap-2 text-sm font-semibold">
                <Hash size={16} className="text-[#207362]" />
                讨论主题
              </label>
              <input
                type="text"
                required
                value={topic}
                onChange={(event) => setTopic(event.target.value)}
                className="h-12 w-full rounded-lg border border-[#d8cbb7] bg-[#fdfaf3] px-4 text-lg outline-none transition placeholder:text-[#9a8b76] focus:border-[#207362] focus:ring-2 focus:ring-[#207362]/15"
                placeholder="你想讨论什么主题？"
              />
            </div>
            <div className="md:col-span-2">
              <label className="mb-2 flex items-center gap-2 text-sm font-semibold">
                <Clock size={16} className="text-[#207362]" />
                讨论时长
              </label>
              <div className="flex gap-2">
                <select
                  value={customDuration ? "__custom" : duration}
                  onChange={(event) => {
                    const value = event.target.value;
                    if (value === "__custom") {
                      setCustomDuration("15");
                      setDuration("__custom");
                    } else {
                      setCustomDuration("");
                      setDuration(value);
                    }
                  }}
                  className="h-12 min-w-0 flex-1 rounded-lg border border-[#d8cbb7] bg-[#fdfaf3] px-3 outline-none transition focus:border-[#207362] focus:ring-2 focus:ring-[#207362]/15"
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
                      onChange={(event) => setCustomDuration(event.target.value)}
                      className="h-12 w-full rounded-lg border border-[#d8cbb7] bg-[#fdfaf3] px-3 pr-8 outline-none transition focus:border-[#207362] focus:ring-2 focus:ring-[#207362]/15"
                    />
                    <span className="pointer-events-none absolute right-3 top-1/2 -translate-y-1/2 text-xs text-[#9a8b76]">分</span>
                  </div>
                )}
              </div>
            </div>
          </div>

          <div ref={dropdownRef} className="mt-7">
            <label className="mb-2 flex items-center gap-2 text-sm font-semibold">
              <Users size={16} className="text-[#207362]" />
              选择参与者（已选 {selectedIds.length} 位）
            </label>

            {agents.length === 0 ? (
              <div className="rounded-lg border border-dashed border-[#cdbfa9] bg-[#f9f4e9] p-4 text-sm text-[#6d6254]">暂无可用的就绪角色，请先生成角色。</div>
            ) : (
              <div className="relative">
                <button
                  type="button"
                  onClick={() => setDropdownOpen(!dropdownOpen)}
                  className="flex min-h-12 w-full items-center justify-between gap-3 rounded-lg border border-[#d8cbb7] bg-[#fdfaf3] px-4 py-3 text-left transition hover:border-[#207362]"
                >
                  <div className="flex min-w-0 flex-wrap items-center gap-2">
                    {selectedAgents.length === 0 ? (
                      <span className="text-sm text-[#9a8b76]">点击选择参与讨论的角色...</span>
                    ) : (
                      selectedAgents.map((agent: any) => (
                        <span key={agent.id} className="inline-flex items-center gap-1 rounded-lg border border-[#207362]/25 bg-[#207362]/10 px-2.5 py-1 text-xs font-semibold text-[#185f51]">
                          {agent.name.replace(/-perspective$/, "")}
                          <span
                            role="button"
                            tabIndex={0}
                            onClick={(event) => {
                              event.stopPropagation();
                              toggleAgent(agent.id);
                            }}
                            onKeyDown={(event) => {
                              if (event.key === "Enter" || event.key === " ") {
                                event.stopPropagation();
                                toggleAgent(agent.id);
                              }
                            }}
                            className="ml-0.5 cursor-pointer hover:text-[#1d1a16]"
                          >
                            x
                          </span>
                        </span>
                      ))
                    )}
                  </div>
                  <ChevronDown size={18} className={`shrink-0 text-[#8a6b37] transition-transform ${dropdownOpen ? "rotate-180" : ""}`} />
                </button>

                {dropdownOpen && (
                  <div className="absolute z-20 mt-2 max-h-64 w-full overflow-y-auto rounded-lg border border-[#d8cbb7] bg-[#fffdf7] p-2 shadow-[0_20px_50px_rgba(53,45,32,0.18)]">
                    {agents.map((agent: any) => {
                      const isSelected = selectedIds.includes(agent.id);
                      return (
                        <div
                          key={agent.id}
                          onClick={() => toggleAgent(agent.id)}
                          className={`flex cursor-pointer items-center gap-3 rounded-lg p-2.5 transition ${isSelected ? "bg-[#207362]/10" : "hover:bg-[#f9f4e9]"}`}
                        >
                          <div className={`flex h-9 w-9 shrink-0 items-center justify-center rounded-lg text-sm font-semibold ${isSelected ? "bg-[#207362] text-white" : "bg-[#1d1a16] text-[#f0d9ad]"}`}>
                            {agent.name.charAt(0)}
                          </div>
                          <div className="min-w-0 flex-1">
                            <div className={`truncate text-sm font-semibold ${isSelected ? "text-[#185f51]" : "text-[#1d1a16]"}`}>{agent.name.replace(/-perspective$/, "")}</div>
                            <div className="truncate text-xs text-[#6d6254]">{agent.description?.slice(0, 44) || "暂无描述"}</div>
                          </div>
                          <div className={`flex h-5 w-5 shrink-0 items-center justify-center rounded border ${isSelected ? "border-[#207362] bg-[#207362]" : "border-[#cdbfa9]"}`}>
                            {isSelected && <span className="h-2 w-2 rounded-full bg-white" />}
                          </div>
                        </div>
                      );
                    })}
                  </div>
                )}
              </div>
            )}
          </div>

          <div className="mt-8 flex justify-end border-t border-[#e4dccd] pt-6">
            <button type="submit" disabled={selectedIds.length < 2 || createMutation.isPending} className="inline-flex h-12 items-center gap-3 rounded-lg bg-[#207362] px-8 text-base font-semibold text-white shadow-[0_10px_24px_rgba(32,115,98,0.24)] transition hover:bg-[#185f51] disabled:cursor-not-allowed disabled:opacity-50">
              <Play size={20} />
              {createMutation.isPending ? "创建中..." : "开始讨论"}
            </button>
          </div>
        </motion.form>
      </div>
    </div>
  );
}
