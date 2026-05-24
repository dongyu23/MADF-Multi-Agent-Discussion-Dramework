import { useState, useEffect, useMemo } from "react";
import { Link, useNavigate } from "react-router";
import { ArrowLeft, Loader2, Shuffle, Sparkles } from "lucide-react";
import { motion, AnimatePresence } from "motion/react";
import { generateCharacter } from "../api/characters";
import {
  clearCachedRecommendations,
  fetchMoreRecommendations,
  loadCachedRecommendations,
  prefetchInitialRecommendations,
  saveCachedRecommendations,
  type RecItem,
} from "../lib/recommendation-cache";
import { toast } from "sonner";

const PAGE_SIZE = 6;

export function GenerateSkill() {
  const navigate = useNavigate();
  const [submitting, setSubmitting] = useState(false);
  const [query, setQuery] = useState("");
  const [showRecommendations, setShowRecommendations] = useState(true);

  const cached = loadCachedRecommendations();
  const [allRecs, setAllRecs] = useState<RecItem[]>(cached || []);
  const [page, setPage] = useState(0);
  const [loadingRecs, setLoadingRecs] = useState(!cached);

  const totalPages = Math.max(1, Math.ceil(allRecs.length / PAGE_SIZE));
  const visibleRecs = useMemo(() => allRecs.slice(page * PAGE_SIZE, (page + 1) * PAGE_SIZE), [allRecs, page]);

  const fetchAllRecommendations = async (append: boolean = false) => {
    setLoadingRecs(true);
    try {
      const items = append
        ? await fetchMoreRecommendations(allRecs)
        : await prefetchInitialRecommendations();
      if (items.length > 0) {
        const merged = append ? [...allRecs, ...items] : items;
        saveCachedRecommendations(merged);
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
    if (page + 1 < totalPages) setPage((p) => p + 1);
    else fetchAllRecommendations(true);
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!query.trim()) return;
    setSubmitting(true);
    try {
      const data = await generateCharacter(query.trim());
      clearCachedRecommendations();
      navigate(`/characters/${data.id}`, { replace: true });
    } catch (err: any) {
      toast.error(err.response?.data?.message || "启动生成失败");
      setSubmitting(false);
    }
  };

  return (
    <div className="relative min-h-full overflow-hidden bg-[#f6f3ec] text-[#1d1a16]">
      <div className="pointer-events-none absolute inset-0 bg-[linear-gradient(90deg,rgba(29,26,22,0.045)_1px,transparent_1px),linear-gradient(rgba(29,26,22,0.045)_1px,transparent_1px)] bg-[size:48px_48px]" />
      <div className="relative mx-auto flex w-full max-w-5xl flex-col gap-6 px-4 py-6 sm:px-6 lg:px-8">
        <header className="flex items-center gap-4 border-b border-[#d8cbb7] pb-6">
          <Link to="/characters" className="flex h-10 w-10 shrink-0 items-center justify-center rounded-lg border border-[#d8cbb7] bg-[#fffdf7] text-[#6d6254] transition hover:bg-[#e9dfcc] hover:text-[#1d1a16]">
            <ArrowLeft size={20} />
          </Link>
          <div>
            <p className="text-xs font-semibold uppercase tracking-[0.24em] text-[#8a6b37]">Skill Pipeline</p>
            <h1 className="mt-2 font-['Noto_Serif_SC'] text-3xl font-semibold leading-tight md:text-4xl">生成技能</h1>
            <p className="mt-2 text-sm leading-6 text-[#6d6254]">从互联网调研到 SKILL.md，生成一个可参与讨论的角色。</p>
          </div>
        </header>

        <section className="rounded-lg border border-[#d8cbb7] bg-[#fffdf7] p-5 shadow-[0_16px_44px_rgba(53,45,32,0.09)] sm:p-6">
          <div className="mb-4 flex flex-wrap items-center justify-between gap-3">
            <h2 className="flex items-center gap-2 text-sm font-semibold">
              <Sparkles size={16} className="text-[#db9a34]" />
              推荐人物
              {allRecs.length > PAGE_SIZE && <span className="text-xs font-normal text-[#9a8b76]">{page + 1}/{totalPages}</span>}
            </h2>
            <div className="flex items-center gap-3">
              <button onClick={handleShuffle} disabled={loadingRecs} className="inline-flex items-center gap-1.5 text-xs font-semibold text-[#207362] transition hover:text-[#185f51] disabled:opacity-50">
                <Shuffle size={14} />
                换一个
              </button>
              <label className="relative inline-flex cursor-pointer items-center">
                <input type="checkbox" checked={showRecommendations} onChange={(e) => setShowRecommendations(e.target.checked)} className="peer sr-only" />
                <div className="h-5 w-9 rounded-full bg-[#d8cbb7] after:absolute after:start-[2px] after:top-[2px] after:h-4 after:w-4 after:rounded-full after:bg-white after:transition-all after:content-[''] peer-checked:bg-[#207362] peer-checked:after:translate-x-full" />
              </label>
            </div>
          </div>

          <AnimatePresence mode="wait">
            {showRecommendations && (
              <motion.div key={`recs-${page}`} initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0, height: 0 }} transition={{ duration: 0.15 }} className="overflow-hidden">
                {loadingRecs ? (
                  <div className="flex items-center justify-center rounded-lg border border-dashed border-[#cdbfa9] bg-[#f9f4e9] py-12">
                    <Loader2 className="mr-3 animate-spin text-[#207362]" size={20} />
                    <span className="text-sm text-[#6d6254]">加载中（需要 30s 左右）</span>
                  </div>
                ) : (
                  <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
                    {visibleRecs.map((item, index) => (
                      <motion.button
                        key={item.name}
                        type="button"
                        initial={{ opacity: 0, y: 8 }}
                        animate={{ opacity: 1, y: 0 }}
                        transition={{ delay: index * 0.04 }}
                        onClick={() => setQuery(item.name)}
                        className="group rounded-lg border border-[#e4dccd] bg-[#f9f4e9] p-4 text-left transition hover:-translate-y-0.5 hover:border-[#207362] hover:bg-[#fdfaf3]"
                      >
                        <div className="text-sm font-semibold group-hover:text-[#185f51]">{item.name}</div>
                        <div className="mt-1 line-clamp-2 text-xs leading-5 text-[#6d6254]">{item.description}</div>
                      </motion.button>
                    ))}
                  </div>
                )}
              </motion.div>
            )}
          </AnimatePresence>
        </section>

        <section className="rounded-lg border border-[#252018] bg-[#1d1a16] p-6 text-white shadow-[0_18px_56px_rgba(29,26,22,0.22)] sm:p-8">
          <form onSubmit={handleSubmit} className="space-y-5">
            <div>
              <label className="mb-2 block text-sm font-semibold text-[#f0d9ad]">目标人格 / 主题</label>
              <input
                type="text"
                required
                value={query}
                onChange={(e) => setQuery(e.target.value)}
                className="h-12 w-full rounded-lg border border-white/12 bg-white/[0.08] px-4 text-lg text-white outline-none transition placeholder:text-[#8f7d62] focus:border-[#f0d9ad] focus:ring-2 focus:ring-[#f0d9ad]/15"
                placeholder="例如：史蒂夫·乔布斯，产品管理专家..."
              />
            </div>
            <button type="submit" disabled={submitting} className="inline-flex h-12 w-full items-center justify-center gap-3 rounded-lg bg-[#f0d9ad] text-base font-semibold text-[#1d1a16] transition hover:bg-[#f5e4bd] disabled:opacity-50">
              {submitting ? <Loader2 className="animate-spin" size={22} /> : <Sparkles size={22} />}
              {submitting ? "正在启动..." : "启动生成流水线"}
            </button>
          </form>
        </section>
      </div>
    </div>
  );
}
