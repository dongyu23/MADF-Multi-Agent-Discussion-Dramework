import { Link } from "react-router";
import { useQuery } from "@tanstack/react-query";
import { motion } from "motion/react";
import {
  Activity,
  ArrowRight,
  BookOpen,
  Bot,
  CirclePlus,
  Clock3,
  Library,
  MessageSquare,
  PenLine,
  Play,
  Radio,
  Sparkles,
  Users,
} from "lucide-react";
import { getGallery, getMyCharacters, type CharacterItem } from "../api/characters";
import { getDiscussions } from "../api/discussions";

type DiscussionItem = {
  id: string;
  topic: string;
  status: string;
  duration?: number;
  created_at?: string;
  agents?: unknown[];
};

function statusMeta(status: string) {
  const map: Record<string, { label: string; tone: string; dot: string }> = {
    running: { label: "进行中", tone: "border-[#207362]/25 bg-[#207362]/10 text-[#185f51]", dot: "bg-[#207362] animate-pulse" },
    completed: { label: "已完成", tone: "border-[#d8cbb7] bg-[#f9f4e9] text-[#6d6254]", dot: "bg-[#9a8b76]" },
    error: { label: "异常", tone: "border-rose-300 bg-rose-50 text-rose-700", dot: "bg-rose-500" },
    pending: { label: "等待中", tone: "border-[#db9a34]/35 bg-[#db9a34]/12 text-[#8a5c16]", dot: "bg-[#db9a34]" },
    starting: { label: "启动中", tone: "border-[#db9a34]/35 bg-[#db9a34]/12 text-[#8a5c16]", dot: "bg-[#db9a34] animate-pulse" },
  };
  return map[status] || { label: status || "未知", tone: "border-[#d8cbb7] bg-[#f9f4e9] text-[#6d6254]", dot: "bg-[#9a8b76]" };
}

function formatDate(value?: string) {
  if (!value) return "刚刚";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return "刚刚";
  return new Intl.DateTimeFormat("zh-CN", {
    month: "2-digit",
    day: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
  }).format(date);
}

function formatDuration(seconds?: number) {
  if (!seconds) return "自由时长";
  const minutes = Math.max(1, Math.round(seconds / 60));
  return `${minutes} 分钟`;
}

export function Dashboard() {
  const { data: charsData, isLoading: charsLoading } = useQuery({
    queryKey: ["characters", { page: 1, pageSize: 6 }],
    queryFn: () => getMyCharacters(1, 6),
    staleTime: 30_000,
  });

  const { data: discsData, isLoading: discsLoading } = useQuery({
    queryKey: ["discussions", { page: 1, pageSize: 6 }],
    queryFn: () => getDiscussions(1, 6),
    staleTime: 10_000,
  });

  const { data: galleryData, isLoading: galleryLoading } = useQuery({
    queryKey: ["gallery", { pageSize: 24 }],
    queryFn: () => getGallery(undefined, undefined, 24),
    staleTime: 60_000,
  });

  const characters: CharacterItem[] = charsData?.items || [];
  const discussions: DiscussionItem[] = discsData?.items || [];
  const galleryItems: CharacterItem[] = galleryData?.items || [];
  const running = discussions.filter((item) => item.status === "running").length;
  const readyCharacters = characters.filter((item) => item.status === "ready").length;
  const latestDiscussion = discussions[0];
  const tableAgents = characters.slice(0, 5);
  const isLoading = charsLoading || discsLoading || galleryLoading;

  const metrics = [
    { label: "角色资产", value: charsData?.total ?? characters.length, icon: Users, tone: "border-[#207362]/25 bg-[#207362]/10 text-[#185f51]" },
    { label: "讨论档案", value: discsData?.total ?? discussions.length, icon: MessageSquare, tone: "border-[#3c6f9d]/25 bg-[#3c6f9d]/10 text-[#28577e]" },
    { label: "实时席位", value: running, icon: Radio, tone: "border-rose-300 bg-rose-50 text-rose-700" },
    { label: "公开技能", value: galleryItems.length, icon: Library, tone: "border-[#db9a34]/35 bg-[#db9a34]/12 text-[#8a5c16]" },
  ];

  return (
    <div className="relative min-h-full overflow-hidden bg-[#f6f3ec] text-[#1d1a16]">
      <div className="pointer-events-none absolute inset-0 bg-[linear-gradient(90deg,rgba(29,26,22,0.045)_1px,transparent_1px),linear-gradient(rgba(29,26,22,0.045)_1px,transparent_1px)] bg-[size:48px_48px]" />
      <div className="relative mx-auto flex w-full max-w-[1440px] flex-col gap-5 px-4 py-5 sm:px-6 lg:px-8">
        <header className="flex flex-col justify-between gap-4 border-b border-[#d8cbb7] pb-5 xl:flex-row xl:items-end">
          <div className="min-w-0">
            <p className="text-xs font-semibold uppercase tracking-[0.24em] text-[#8a6b37]">MADF Console</p>
            <h1 className="mt-2 font-['Noto_Serif_SC'] text-3xl font-semibold leading-tight md:text-4xl">主系统仪表盘</h1>
            <p className="mt-2 max-w-3xl text-sm leading-6 text-[#6d6254]">从这里创建讨论、检查角色资产，并进入最近的圆桌记录。</p>
          </div>
          <div className="flex flex-wrap gap-2 text-xs font-semibold">
            <span className="rounded-lg border border-[#d8cbb7] bg-[#fffdf7] px-3 py-1.5 text-[#6d6254]">Docker 环境</span>
            <span className="rounded-lg border border-[#207362]/25 bg-[#207362]/10 px-3 py-1.5 text-[#185f51]">后端已连接</span>
          </div>
        </header>

        <motion.section
          initial={{ opacity: 0, y: 14 }}
          animate={{ opacity: 1, y: 0 }}
          className="grid gap-5 xl:grid-cols-[minmax(0,1.55fr)_minmax(360px,0.75fr)]"
        >
          <div className="overflow-hidden rounded-lg border border-[#252018] bg-[#fffdf7] shadow-[0_18px_56px_rgba(53,45,32,0.12)]">
            <div className="grid min-h-[280px] lg:grid-cols-[minmax(0,1fr)_340px]">
              <div className="flex flex-col justify-between gap-8 p-5 sm:p-6 lg:p-7">
                <div>
                  <div className="mb-5 inline-flex items-center gap-2 rounded-lg border border-[#d8cbb7] bg-[#f9f4e9] px-3 py-1.5 text-xs font-semibold text-[#6f5d40]">
                    <Sparkles size={14} />
                    Roundtable Operations
                  </div>
                  <h2 className="max-w-3xl font-['Noto_Serif_SC'] text-3xl font-semibold leading-tight md:text-5xl">
                    创建一场可追踪、可回放的角色圆桌。
                  </h2>
                  <p className="mt-4 max-w-2xl text-base leading-7 text-[#6d6254]">
                    选择 Skill 驱动的角色，设置主题和时长，让系统完成发言仲裁、流式记录和主持人摘要。
                  </p>
                </div>
                <div className="flex flex-wrap gap-3">
                  <Link to="/discussions/new" className="inline-flex h-11 items-center gap-2 rounded-lg bg-[#207362] px-4 text-sm font-semibold text-white shadow-[0_10px_24px_rgba(32,115,98,0.24)] transition hover:-translate-y-0.5 hover:bg-[#185f51]">
                    <CirclePlus size={18} />
                    新建讨论
                  </Link>
                  <Link to="/characters/generate" className="inline-flex h-11 items-center gap-2 rounded-lg border border-[#1d1a16] bg-[#fdfaf3] px-4 text-sm font-semibold text-[#1d1a16] transition hover:-translate-y-0.5 hover:bg-[#efe7d8]">
                    <Sparkles size={18} />
                    生成角色
                  </Link>
                </div>
              </div>

              <div className="relative hidden overflow-hidden border-l border-[#252018] bg-[#1d1a16] p-5 text-white lg:block">
                <div className="absolute inset-0 bg-[linear-gradient(90deg,rgba(255,255,255,0.05)_1px,transparent_1px),linear-gradient(rgba(255,255,255,0.05)_1px,transparent_1px)] bg-[size:34px_34px]" />
                <div className="relative flex h-full min-h-[280px] flex-col justify-between">
                  <div className="rounded-lg border border-white/12 bg-white/[0.07] p-4">
                    <div className="text-xs font-semibold text-[#f0d9ad]">Live Protocol</div>
                    <div className="mt-4 space-y-3">
                      {["agent_think", "agent_speak", "host_summary"].map((event, index) => (
                        <div key={event} className="grid grid-cols-[minmax(0,1fr)_76px] items-center gap-3">
                          <span className="truncate font-mono text-[11px] text-[#d8cbb7]">{event}</span>
                          <span className="h-1.5 overflow-hidden rounded-full bg-white/12">
                            <span className="block h-full rounded-full bg-[#db9a34]" style={{ width: `${54 + index * 16}%` }} />
                          </span>
                        </div>
                      ))}
                    </div>
                  </div>
                  <div className="relative mx-auto h-36 w-36 rounded-full border border-[#f0d9ad]/35">
                    <div className="absolute left-1/2 top-1/2 h-24 w-24 -translate-x-1/2 -translate-y-1/2 rounded-full bg-[#f0d9ad] shadow-[0_0_80px_rgba(240,217,173,0.32)]" />
                    <div className="absolute left-1/2 top-1/2 flex h-14 w-14 -translate-x-1/2 -translate-y-1/2 items-center justify-center rounded-full bg-[#207362]">
                      <MessageSquare size={22} />
                    </div>
                  </div>
                </div>
              </div>
            </div>
          </div>

          <aside className="rounded-lg border border-[#252018] bg-[#fffdf7] p-5 shadow-[0_18px_56px_rgba(53,45,32,0.1)]">
            <div className="mb-4 flex items-center justify-between">
              <div>
                <p className="text-xs font-semibold text-[#8a6b37]">下一场讨论</p>
                <h2 className="mt-1 text-lg font-semibold">圆桌调度</h2>
              </div>
              <Activity className="text-[#207362]" size={22} />
            </div>
            {latestDiscussion ? (
              <Link to={`/discussions/${latestDiscussion.id}`} className="group block rounded-lg border border-[#e4dccd] bg-[#f9f4e9] p-4 transition hover:-translate-y-0.5 hover:border-[#207362] hover:shadow-[0_14px_34px_rgba(53,45,32,0.12)]">
                <div className="mb-4 flex items-center gap-2">
                  <span className={`h-2 w-2 rounded-full ${statusMeta(latestDiscussion.status).dot}`} />
                  <span className={`rounded-lg border px-2 py-0.5 text-xs font-semibold ${statusMeta(latestDiscussion.status).tone}`}>
                    {statusMeta(latestDiscussion.status).label}
                  </span>
                </div>
                <p className="line-clamp-3 text-lg font-semibold leading-7">{latestDiscussion.topic}</p>
                <div className="mt-5 flex items-center justify-between text-xs text-[#7a6a56]">
                  <span className="inline-flex items-center gap-1.5">
                    <Clock3 size={14} />
                    {formatDuration(latestDiscussion.duration)}
                  </span>
                  <span className="inline-flex items-center gap-1.5 font-semibold text-[#207362]">
                    进入
                    <ArrowRight className="transition group-hover:translate-x-1" size={14} />
                  </span>
                </div>
              </Link>
            ) : (
              <div className="rounded-lg border border-dashed border-[#cdbfa9] bg-[#f9f4e9] p-5 text-sm leading-6 text-[#6d6254]">
                当前没有讨论记录。先创建一场 3-5 个角色参与的短时讨论。
              </div>
            )}
          </aside>
        </motion.section>

        <section className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
          {metrics.map((metric, index) => {
            const Icon = metric.icon;
            return (
              <motion.div
                key={metric.label}
                initial={{ opacity: 0, y: 12 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: 0.04 * index }}
                className="rounded-lg border border-[#d8cbb7] bg-[#fffdf7] p-4 shadow-[0_12px_34px_rgba(53,45,32,0.08)]"
              >
                <div className="flex items-start justify-between gap-4">
                  <div>
                    <div className="font-['Noto_Serif_SC'] text-3xl font-semibold">{metric.value}</div>
                    <div className="mt-1 text-sm font-medium text-[#6d6254]">{metric.label}</div>
                  </div>
                  <div className={`rounded-lg border p-2.5 ${metric.tone}`}>
                    <Icon size={19} />
                  </div>
                </div>
                {isLoading && <div className="mt-4 h-1.5 overflow-hidden rounded-full bg-[#e4dccd]"><div className="h-full w-1/2 animate-pulse rounded-full bg-[#db9a34]" /></div>}
              </motion.div>
            );
          })}
        </section>

        <section className="grid gap-5 xl:grid-cols-[minmax(0,1.1fr)_minmax(360px,0.9fr)]">
          <div className="rounded-lg border border-[#d8cbb7] bg-[#fffdf7] p-5 shadow-[0_16px_44px_rgba(53,45,32,0.09)]">
            <div className="mb-5 flex items-center justify-between gap-4">
              <div>
                <p className="text-xs font-semibold text-[#8a6b37]">Agent Table</p>
                <h2 className="mt-1 text-xl font-semibold">角色圆桌</h2>
              </div>
              <Link to="/characters" className="inline-flex items-center gap-1.5 text-sm font-semibold text-[#207362] hover:text-[#185a4d]">
                管理角色
                <ArrowRight size={15} />
              </Link>
            </div>

            <div className="grid gap-5 lg:grid-cols-[minmax(280px,0.82fr)_minmax(0,1fr)]">
              <div className="relative min-h-[310px] overflow-hidden rounded-lg border border-[#252018] bg-[#1d1a16] p-5 text-white">
                <div className="absolute inset-0 bg-[linear-gradient(90deg,rgba(255,255,255,0.045)_1px,transparent_1px),linear-gradient(rgba(255,255,255,0.045)_1px,transparent_1px)] bg-[size:32px_32px]" />
                <div className="absolute left-1/2 top-1/2 h-48 w-48 -translate-x-1/2 -translate-y-1/2 rounded-full border border-[#e8dec9]/35" />
                <div className="absolute left-1/2 top-1/2 h-28 w-28 -translate-x-1/2 -translate-y-1/2 rounded-full bg-[#f0d9ad] shadow-[0_0_80px_rgba(240,217,173,0.42)]" />
                <div className="absolute left-1/2 top-1/2 flex h-16 w-16 -translate-x-1/2 -translate-y-1/2 items-center justify-center rounded-full bg-[#207362]">
                  <MessageSquare size={25} />
                </div>

                {tableAgents.length === 0 ? (
                  <div className="relative z-10 flex h-full min-h-[260px] items-end text-sm leading-6 text-[#d8cbb7]">
                    还没有可用角色。生成一个角色后，圆桌会自动形成席位。
                  </div>
                ) : (
                  tableAgents.map((agent, index) => {
                    const positions = [
                      "left-[10%] top-[18%]",
                      "right-[9%] top-[18%]",
                      "left-[8%] bottom-[17%]",
                      "right-[9%] bottom-[17%]",
                      "left-1/2 top-[6%] -translate-x-1/2",
                    ];
                    return (
                      <Link
                        key={agent.id}
                        to={`/characters/${agent.id}`}
                        className={`absolute ${positions[index]} group flex max-w-[140px] items-center gap-2 rounded-lg border border-white/15 bg-white/10 px-3 py-2 backdrop-blur transition hover:-translate-y-1 hover:bg-white/18`}
                      >
                        <span className="flex h-8 w-8 shrink-0 items-center justify-center rounded-lg bg-[#f0d9ad] text-[#1d1a16]">
                          <Bot size={17} />
                        </span>
                        <span className="min-w-0">
                          <span className="block truncate text-xs font-semibold">{agent.name.replace(/-perspective$/, "")}</span>
                          <span className="block text-[11px] text-[#d8cbb7]">{agent.status}</span>
                        </span>
                      </Link>
                    );
                  })
                )}
              </div>

              <div className="grid content-start gap-3">
                {characters.length === 0 ? (
                  <div className="rounded-lg border border-dashed border-[#cdbfa9] bg-[#f9f4e9] p-6">
                    <Sparkles className="mb-4 text-[#db9a34]" size={28} />
                    <h3 className="text-lg font-semibold">建立第一个角色</h3>
                    <p className="mt-2 text-sm leading-6 text-[#6d6254]">角色 Skill 准备好后，才能进入多智能体圆桌。</p>
                    <Link to="/characters/generate" className="mt-5 inline-flex h-10 w-fit items-center gap-2 rounded-lg bg-[#1d1a16] px-4 text-sm font-semibold text-white">
                      开始生成
                      <ArrowRight size={15} />
                    </Link>
                  </div>
                ) : (
                  characters.slice(0, 4).map((agent) => (
                    <Link key={agent.id} to={`/characters/${agent.id}`} className="group flex items-start gap-3 rounded-lg border border-[#e4dccd] bg-[#fdfaf3] p-4 transition hover:border-[#207362] hover:bg-[#f7efe0]">
                      <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-lg bg-[#1d1a16] text-[#f0d9ad]">
                        <BookOpen size={18} />
                      </div>
                      <div className="min-w-0 flex-1">
                        <div className="flex items-center justify-between gap-3">
                          <h3 className="truncate text-sm font-semibold">{agent.name.replace(/-perspective$/, "")}</h3>
                          <span className="shrink-0 rounded-lg border border-[#d8cbb7] px-2 py-0.5 text-[11px] font-semibold text-[#6d6254]">{agent.status}</span>
                        </div>
                        <p className="mt-1 line-clamp-2 text-xs leading-5 text-[#6d6254]">{agent.description || "暂无角色描述"}</p>
                      </div>
                    </Link>
                  ))
                )}
              </div>
            </div>
          </div>

          <div className="grid gap-5">
            <div className="rounded-lg border border-[#d8cbb7] bg-[#fffdf7] p-5 shadow-[0_16px_44px_rgba(53,45,32,0.09)]">
              <div className="mb-4 flex items-center justify-between">
                <div>
                  <p className="text-xs font-semibold text-[#8a6b37]">Recent Sessions</p>
                  <h2 className="mt-1 text-xl font-semibold">最近讨论</h2>
                </div>
                <Link to="/discussions" className="text-sm font-semibold text-[#207362] hover:text-[#185a4d]">全部</Link>
              </div>

              <div className="space-y-3">
                {discussions.length === 0 ? (
                  <div className="rounded-lg border border-dashed border-[#cdbfa9] bg-[#f9f4e9] p-5 text-sm text-[#6d6254]">暂无讨论记录</div>
                ) : (
                  discussions.slice(0, 4).map((item) => {
                    const meta = statusMeta(item.status);
                    return (
                      <Link key={item.id} to={`/discussions/${item.id}`} className="group grid grid-cols-[minmax(0,1fr)_auto] gap-3 rounded-lg border border-[#e4dccd] bg-[#fdfaf3] p-4 transition hover:border-[#207362]">
                        <div className="min-w-0">
                          <div className="mb-2 flex items-center gap-2">
                            <span className={`h-2 w-2 rounded-full ${meta.dot}`} />
                            <span className="text-xs font-medium text-[#7a6a56]">{formatDate(item.created_at)}</span>
                          </div>
                          <h3 className="line-clamp-2 text-sm font-semibold leading-5">{item.topic}</h3>
                        </div>
                        <div className="flex flex-col items-end justify-between">
                          <span className={`rounded-lg border px-2 py-0.5 text-[11px] font-semibold ${meta.tone}`}>{meta.label}</span>
                          <Play className="text-[#9a8b76] transition group-hover:text-[#207362]" size={16} />
                        </div>
                      </Link>
                    );
                  })
                )}
              </div>
            </div>

            <div className="rounded-lg border border-[#252018] bg-[#1d1a16] p-5 text-white">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-xs font-semibold text-[#f0d9ad]">Next Move</p>
                  <h2 className="mt-1 text-xl font-semibold">工作流入口</h2>
                </div>
                <PenLine className="text-[#f0d9ad]" size={22} />
              </div>
              <div className="mt-5 grid gap-3 sm:grid-cols-2">
                <Link to="/discussions/new" className="rounded-lg border border-white/12 bg-white/8 p-4 transition hover:-translate-y-0.5 hover:bg-white/14">
                  <MessageSquare className="mb-4 text-[#f0d9ad]" size={22} />
                  <div className="text-sm font-semibold">创建讨论</div>
                  <div className="mt-1 text-xs leading-5 text-[#d8cbb7]">选择主题、角色和时长</div>
                </Link>
                <Link to="/gallery" className="rounded-lg border border-white/12 bg-white/8 p-4 transition hover:-translate-y-0.5 hover:bg-white/14">
                  <Library className="mb-4 text-[#f0d9ad]" size={22} />
                  <div className="text-sm font-semibold">浏览画廊</div>
                  <div className="mt-1 text-xs leading-5 text-[#d8cbb7]">复制公开 Skill 到我的角色</div>
                </Link>
              </div>
              <div className="mt-5 rounded-lg border border-white/12 bg-[#f0d9ad] p-4 text-[#1d1a16]">
                <div className="flex items-center justify-between gap-3">
                  <div>
                    <div className="text-sm font-semibold">可用角色</div>
                    <div className="text-xs text-[#675332]">{readyCharacters} 个 ready，可直接进入讨论</div>
                  </div>
                  <Bot size={22} />
                </div>
              </div>
            </div>
          </div>
        </section>
      </div>
    </div>
  );
}
