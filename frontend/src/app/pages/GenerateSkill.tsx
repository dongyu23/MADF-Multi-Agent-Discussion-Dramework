import { useState, useEffect, useMemo } from "react";
import { Link, useNavigate } from "react-router";
import { Sparkles, ArrowLeft, Loader2, Shuffle } from "lucide-react";
import { motion, AnimatePresence } from "motion/react";
import { generateCharacter, getRecommendations } from "../api/characters";
import { toast } from "sonner";

const RECS_KEY = "madf_recs";
const PAGE_SIZE = 6;

type RecItem = { name: string; description: string; query: string };

function loadCachedRecs(): RecItem[] | null {
  try {
    const raw = sessionStorage.getItem(RECS_KEY);
    if (raw) return JSON.parse(raw) as RecItem[];
  } catch { /* ignore */ }
  return null;
}

function saveCachedRecs(items: RecItem[]) {
  try {
    sessionStorage.setItem(RECS_KEY, JSON.stringify(items));
  } catch { /* ignore */ }
}

export function GenerateSkill() {
  const navigate = useNavigate();
  const [submitting, setSubmitting] = useState(false);
  const [query, setQuery] = useState("");
  const [showRecommendations, setShowRecommendations] = useState(true);

  const cached = loadCachedRecs();
  const [allRecs, setAllRecs] = useState<RecItem[]>(cached || []);
  const [page, setPage] = useState(0);
  const [loadingRecs, setLoadingRecs] = useState(!cached);

  const totalPages = Math.max(1, Math.ceil(allRecs.length / PAGE_SIZE));
  const visibleRecs = useMemo(
    () => allRecs.slice(page * PAGE_SIZE, (page + 1) * PAGE_SIZE),
    [allRecs, page]
  );

  const fetchAllRecommendations = async (append: boolean = false) => {
    setLoadingRecs(true);
    try {
      const excludeNames = append ? allRecs.map((r) => r.name) : undefined;
      const data = await getRecommendations(excludeNames);
      const items: RecItem[] = data.items || [];
      if (items.length > 0) {
        const merged = append ? [...allRecs, ...items] : items;
        saveCachedRecs(merged);
        setAllRecs(merged);
        setPage(append ? page + 1 : 0);
      }
    } catch {
      toast.error("推荐加载失败");
    } finally {
      setLoadingRecs(false);
    }
  };

  useEffect(() => {
    if (!cached) fetchAllRecommendations();
  }, []);

  const handleShuffle = () => {
    if (page + 1 < totalPages) {
      setPage((p) => p + 1);
    } else {
      fetchAllRecommendations(true);
    }
  };

  const selectRecommendation = (item: RecItem) => {
    setQuery(item.name);
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!query.trim()) return;
    setSubmitting(true);
    try {
      const data = await generateCharacter(query.trim());
      sessionStorage.removeItem(RECS_KEY);
      navigate(`/characters/${data.id}`, { replace: true });
    } catch (err: any) {
      toast.error(err.response?.data?.message || "启动生成失败");
      setSubmitting(false);
    }
  };

  return (
    <div className="p-8 max-w-4xl mx-auto space-y-6">
      <div className="flex items-center gap-4">
        <Link to="/characters" className="w-10 h-10 bg-white border border-slate-200 rounded-full flex items-center justify-center text-slate-500 hover:text-slate-900 transition-colors shadow-sm">
          <ArrowLeft size={20} />
        </Link>
        <div>
          <h1 className="text-2xl font-bold text-slate-900">生成技能</h1>
          <p className="text-slate-500 mt-1">从互联网信息中提取新的智能体人格</p>
        </div>
      </div>

      {/* ── Recommendation Section ── */}
      <div className="bg-white border border-slate-200 rounded-3xl p-6 shadow-sm">
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-sm font-semibold text-slate-900 flex items-center gap-2">
            <Sparkles size={16} className="text-indigo-500" />
            推荐人物
            {allRecs.length > PAGE_SIZE && (
              <span className="text-slate-400 font-normal text-xs">
                {page + 1}/{totalPages}
              </span>
            )}
          </h2>
          <div className="flex items-center gap-3">
            <button
              onClick={handleShuffle}
              disabled={loadingRecs}
              className="flex items-center gap-1.5 text-xs font-medium text-slate-500 hover:text-indigo-600 transition-colors disabled:opacity-50"
            >
              <Shuffle size={14} />
              换一个
            </button>
            <label className="relative inline-flex items-center cursor-pointer">
              <input
                type="checkbox"
                checked={showRecommendations}
                onChange={(e) => setShowRecommendations(e.target.checked)}
                className="sr-only peer"
              />
              <div className="w-9 h-5 bg-slate-200 peer-focus:outline-none rounded-full peer peer-checked:after:translate-x-full rtl:peer-checked:after:-translate-x-full peer-checked:bg-indigo-600 after:content-[''] after:absolute after:top-[2px] after:start-[2px] after:bg-white after:rounded-full after:h-4 after:w-4 after:transition-all" />
            </label>
          </div>
        </div>

        <AnimatePresence mode="wait">
          {showRecommendations && (
            <motion.div
              key={`recs-${page}`}
              initial={{ opacity: 0, y: 8 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, height: 0 }}
              transition={{ duration: 0.15 }}
              className="overflow-hidden"
            >
              {loadingRecs ? (
                <div className="flex items-center justify-center py-12">
                  <Loader2 className="animate-spin text-indigo-500 mr-3" size={20} />
                  <span className="text-slate-500 text-sm">加载中（需要 30s 左右）</span>
                </div>
              ) : (
                <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3">
                  {visibleRecs.map((item, i) => (
                    <motion.button
                      key={item.name}
                      type="button"
                      initial={{ opacity: 0, y: 8 }}
                      animate={{ opacity: 1, y: 0 }}
                      transition={{ delay: i * 0.04 }}
                      onClick={() => selectRecommendation(item)}
                      className="text-left p-4 bg-slate-50 border border-slate-200 rounded-xl hover:border-indigo-300 hover:bg-indigo-50/50 transition-all group"
                    >
                      <div className="font-semibold text-slate-900 text-sm group-hover:text-indigo-700 transition-colors">
                        {item.name}
                      </div>
                      <div className="text-xs text-slate-500 mt-1 line-clamp-2">
                        {item.description}
                      </div>
                    </motion.button>
                  ))}
                </div>
              )}
            </motion.div>
          )}
        </AnimatePresence>
      </div>

      <div className="bg-white border border-slate-200 rounded-3xl p-8 shadow-sm">
        <form onSubmit={handleSubmit} className="space-y-6">
          <div>
            <label className="block text-sm font-medium text-slate-900 mb-2">目标人格 / 主题</label>
            <input type="text" required value={query} onChange={(e) => setQuery(e.target.value)}
              className="w-full px-4 py-3 border border-slate-200 rounded-xl focus:ring-2 focus:ring-indigo-600 outline-none text-lg"
              placeholder="例如：史蒂夫·乔布斯，产品管理专家..." />
          </div>
          <button type="submit" disabled={submitting}
            className="w-full bg-indigo-600 hover:bg-indigo-700 disabled:opacity-50 text-white py-4 rounded-xl font-bold text-lg flex items-center justify-center gap-3 transition-colors shadow-md">
            {submitting ? <Loader2 className="animate-spin" size={24} /> : <Sparkles size={24} />}
            {submitting ? "正在启动..." : "启动生成流水线"}
          </button>
        </form>
      </div>
    </div>
  );
}
