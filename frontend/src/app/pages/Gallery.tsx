import { useState } from "react";
import { Link } from "react-router";
import { Copy, Eye, Filter, Library, Search, Sparkles } from "lucide-react";
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
    queryFn: () => getGallery(searchTerm || undefined).then((d) => d.items || []),
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

  return (
    <div className="relative min-h-full overflow-hidden bg-[#f6f3ec] text-[#1d1a16]">
      <div className="pointer-events-none absolute inset-0 bg-[linear-gradient(90deg,rgba(29,26,22,0.045)_1px,transparent_1px),linear-gradient(rgba(29,26,22,0.045)_1px,transparent_1px)] bg-[size:48px_48px]" />
      <div className="relative mx-auto flex w-full max-w-7xl flex-col gap-6 px-4 py-6 sm:px-6 lg:px-8">
        <header className="grid gap-5 border-b border-[#d8cbb7] pb-6 lg:grid-cols-[minmax(0,1fr)_auto] lg:items-end">
          <div>
            <p className="text-xs font-semibold uppercase tracking-[0.24em] text-[#8a6b37]">Skill Gallery</p>
            <h1 className="mt-2 font-['Noto_Serif_SC'] text-3xl font-semibold leading-tight md:text-4xl">技能画廊</h1>
            <p className="mt-2 max-w-2xl text-sm leading-6 text-[#6d6254]">发现公开角色，复制到自己的角色资产库，再放入圆桌。</p>
          </div>
          <form onSubmit={handleSearch} className="flex w-full max-w-xl gap-2">
            <div className="relative min-w-0 flex-1">
              <Search className="absolute left-3 top-1/2 h-5 w-5 -translate-y-1/2 text-[#9a8b76]" />
              <input
                type="text"
                value={search}
                onChange={(e) => setSearch(e.target.value)}
                placeholder="按名称或标签搜索角色..."
                className="h-11 w-full rounded-lg border border-[#d8cbb7] bg-[#fffdf7] pl-10 pr-4 text-sm outline-none transition focus:border-[#207362] focus:ring-2 focus:ring-[#207362]/15"
              />
            </div>
            <button type="submit" className="inline-flex h-11 items-center gap-2 rounded-lg border border-[#1d1a16] bg-[#fdfaf3] px-4 text-sm font-semibold transition hover:bg-[#e9dfcc]">
              <Filter size={17} />
              搜索
            </button>
          </form>
        </header>

        {isLoading ? (
          <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
            {[1, 2, 3].map((item) => (
              <div key={item} className="h-56 animate-pulse rounded-lg border border-[#d8cbb7] bg-[#fffdf7]" />
            ))}
          </div>
        ) : characters.length === 0 ? (
          <section className="rounded-lg border border-dashed border-[#cdbfa9] bg-[#fffdf7] p-10 text-center shadow-[0_16px_44px_rgba(53,45,32,0.07)]">
            <Library className="mx-auto text-[#db9a34]" size={34} />
            <h2 className="mt-4 text-xl font-semibold">画廊暂无角色</h2>
            <p className="mt-2 text-sm text-[#6d6254]">去“我的角色”页面生成并公开角色。</p>
          </section>
        ) : (
          <section className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
            {characters.map((char: any, index: number) => (
              <motion.article
                key={char.id}
                initial={{ opacity: 0, y: 12 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: index * 0.035 }}
                className="group flex min-h-[250px] flex-col rounded-lg border border-[#d8cbb7] bg-[#fffdf7] p-5 shadow-[0_14px_38px_rgba(53,45,32,0.08)] transition hover:-translate-y-0.5 hover:border-[#252018]"
              >
                <div className="flex items-start justify-between gap-4">
                  <div className="flex h-12 w-12 items-center justify-center rounded-lg bg-[#1d1a16] text-lg font-semibold text-[#f0d9ad]">
                    {char.name.charAt(0)}
                  </div>
                  <div className="flex gap-1">
                    <Link to={`/gallery/${char.id}/view`} className="rounded-lg p-2 text-[#8a6b37] transition hover:bg-[#f0d9ad]/45 hover:text-[#1d1a16]" title="查看详情">
                      <Eye size={18} />
                    </Link>
                    <button
                      onClick={() => copyMutation.mutate(char.id)}
                      className="rounded-lg p-2 text-[#8a6b37] transition hover:bg-[#207362]/10 hover:text-[#185f51]"
                      title="复制到我的角色"
                    >
                      <Copy size={18} />
                    </button>
                  </div>
                </div>
                <h2 className="mt-5 text-lg font-semibold">{char.name.replace(/-perspective$/, "")}</h2>
                <p className="mt-2 line-clamp-4 flex-1 text-sm leading-6 text-[#6d6254]">{char.description || "暂无描述"}</p>
                <div className="mt-5 flex items-center justify-between border-t border-[#e4dccd] pt-4 text-xs font-semibold">
                  <span className="truncate text-[#7a6a56]">{char.tags?.slice(0, 3).join(", ") || "无标签"}</span>
                  <span className="inline-flex items-center gap-1 rounded-lg border border-[#207362]/25 bg-[#207362]/10 px-2 py-1 text-[#185f51]">
                    <Sparkles size={13} />
                    就绪
                  </span>
                </div>
              </motion.article>
            ))}
          </section>
        )}
      </div>
    </div>
  );
}
