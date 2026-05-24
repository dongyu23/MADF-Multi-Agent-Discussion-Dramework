import { Link, useNavigate } from "react-router";
import { ArrowRight, BookOpen, Globe, Plus, Sparkles, Trash2 } from "lucide-react";
import { motion } from "motion/react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { getMyCharacters, deleteCharacter, updateCharacter, type CharacterItem } from "../api/characters";
import { toast } from "sonner";

function statusMeta(status: string) {
  const map: Record<string, { label: string; tone: string; dot: string }> = {
    ready: { label: "就绪", tone: "border-[#207362]/25 bg-[#207362]/10 text-[#185f51]", dot: "bg-[#207362]" },
    generating: { label: "生成中", tone: "border-[#db9a34]/35 bg-[#db9a34]/12 text-[#8a5c16]", dot: "bg-[#db9a34] animate-pulse" },
    error: { label: "错误", tone: "border-rose-300 bg-rose-50 text-rose-700", dot: "bg-rose-500" },
  };
  return map[status] || { label: status || "未知", tone: "border-[#d8cbb7] bg-[#f9f4e9] text-[#6d6254]", dot: "bg-[#9a8b76]" };
}

export function Characters() {
  const navigate = useNavigate();
  const queryClient = useQueryClient();

  const { data: characters = [], isLoading } = useQuery({
    queryKey: ["characters"],
    queryFn: () => getMyCharacters().then((d) => d.items || []),
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

  return (
    <div className="relative min-h-full overflow-hidden bg-[#f6f3ec] text-[#1d1a16]">
      <div className="pointer-events-none absolute inset-0 bg-[linear-gradient(90deg,rgba(29,26,22,0.045)_1px,transparent_1px),linear-gradient(rgba(29,26,22,0.045)_1px,transparent_1px)] bg-[size:48px_48px]" />
      <div className="relative mx-auto flex w-full max-w-7xl flex-col gap-6 px-4 py-6 sm:px-6 lg:px-8">
        <header className="flex flex-col justify-between gap-4 border-b border-[#d8cbb7] pb-6 md:flex-row md:items-end">
          <div>
            <p className="text-xs font-semibold uppercase tracking-[0.24em] text-[#8a6b37]">Character Assets</p>
            <h1 className="mt-2 font-['Noto_Serif_SC'] text-3xl font-semibold leading-tight md:text-4xl">我的角色</h1>
            <p className="mt-2 max-w-2xl text-sm leading-6 text-[#6d6254]">管理由 Skill 驱动的角色文件、公开状态和讨论可用性。</p>
          </div>
          <Link
            to="/characters/generate"
            className="inline-flex h-11 w-fit items-center gap-2 rounded-lg bg-[#207362] px-4 text-sm font-semibold text-white shadow-[0_10px_24px_rgba(32,115,98,0.24)] transition hover:-translate-y-0.5 hover:bg-[#185f51]"
          >
            <Plus size={18} />
            生成新角色
          </Link>
        </header>

        {isLoading ? (
          <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
            {[1, 2, 3].map((item) => (
              <div key={item} className="h-52 animate-pulse rounded-lg border border-[#d8cbb7] bg-[#fffdf7]" />
            ))}
          </div>
        ) : characters.length === 0 ? (
          <section className="rounded-lg border border-dashed border-[#cdbfa9] bg-[#fffdf7] p-10 text-center shadow-[0_16px_44px_rgba(53,45,32,0.07)]">
            <Sparkles className="mx-auto text-[#db9a34]" size={34} />
            <h2 className="mt-4 text-xl font-semibold">还没有角色</h2>
            <p className="mt-2 text-sm text-[#6d6254]">生成第一个角色后，就可以把它放入圆桌讨论。</p>
          </section>
        ) : (
          <section className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
            {characters.map((char: CharacterItem, index: number) => {
              const meta = statusMeta(char.status);
              return (
                <motion.article
                  key={char.id}
                  initial={{ opacity: 0, y: 12 }}
                  animate={{ opacity: 1, y: 0 }}
                  transition={{ delay: index * 0.035 }}
                  onClick={() => navigate(`/characters/${char.id}`)}
                  className="group cursor-pointer rounded-lg border border-[#d8cbb7] bg-[#fffdf7] p-5 shadow-[0_14px_38px_rgba(53,45,32,0.08)] transition hover:-translate-y-0.5 hover:border-[#252018] hover:shadow-[0_18px_50px_rgba(53,45,32,0.12)]"
                >
                  <div className="flex items-start justify-between gap-4">
                    <div className="flex min-w-0 items-center gap-3">
                      <div className="flex h-11 w-11 shrink-0 items-center justify-center rounded-lg bg-[#1d1a16] text-[#f0d9ad]">
                        <BookOpen size={20} />
                      </div>
                      <div className="min-w-0">
                        <h2 className="truncate text-lg font-semibold">{char.name.replace(/-perspective$/, "")}</h2>
                        <div className="mt-1 flex items-center gap-2">
                          <span className={`h-2 w-2 rounded-full ${meta.dot}`} />
                          <span className={`rounded-lg border px-2 py-0.5 text-[11px] font-semibold ${meta.tone}`}>{meta.label}</span>
                        </div>
                      </div>
                    </div>
                    <div className="flex items-center gap-1 opacity-100 transition md:opacity-0 md:group-hover:opacity-100" onClick={(e) => e.stopPropagation()}>
                      <button
                        className="rounded-lg p-2 text-[#8a6b37] transition hover:bg-[#f0d9ad]/45 hover:text-[#1d1a16]"
                        title={char.is_public ? "取消公开" : "公开到画廊"}
                        onClick={() => togglePublicMutation.mutate({ id: char.id, isPublic: !char.is_public })}
                      >
                        <Globe size={18} />
                      </button>
                      <button
                        className="rounded-lg p-2 text-[#9a8b76] transition hover:bg-rose-50 hover:text-rose-600"
                        title="删除"
                        onClick={() => {
                          if (confirm("确定要删除？")) deleteMutation.mutate(char.id);
                        }}
                      >
                        <Trash2 size={18} />
                      </button>
                    </div>
                  </div>

                  <p className="mt-5 line-clamp-3 min-h-[4.5rem] text-sm leading-6 text-[#6d6254]">{char.description || "暂无角色描述"}</p>
                  <div className="mt-5 flex items-center justify-between border-t border-[#e4dccd] pt-4">
                    <span className="rounded-lg border border-[#d8cbb7] bg-[#f9f4e9] px-2.5 py-1 text-xs font-semibold text-[#6d6254]">
                      {char.is_public ? "公开画廊" : "私有角色"}
                    </span>
                    <span className="inline-flex items-center gap-1.5 text-sm font-semibold text-[#207362]">
                      查看文件
                      <ArrowRight size={15} className="transition group-hover:translate-x-1" />
                    </span>
                  </div>
                </motion.article>
              );
            })}
          </section>
        )}
      </div>
    </div>
  );
}
