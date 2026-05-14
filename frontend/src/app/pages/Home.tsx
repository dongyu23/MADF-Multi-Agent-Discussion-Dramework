import { Link } from "react-router";
import { Users, MessageSquare, Play, Sparkles, Activity } from "lucide-react";
import { motion } from "motion/react";
import { useQuery } from "@tanstack/react-query";
import { getMyCharacters, getGallery } from "../api/characters";
import { getDiscussions } from "../api/discussions";

export function Home() {
  const { data: charsData } = useQuery({
    queryKey: ["characters", { page: 1, pageSize: 1 }],
    queryFn: () => getMyCharacters(1, 1),
    staleTime: 30_000,
  });
  const { data: discsData } = useQuery({
    queryKey: ["discussions", { page: 1, pageSize: 5 }],
    queryFn: () => getDiscussions(1, 5),
    staleTime: 10_000,
  });
  const { data: galleryItems = [] } = useQuery({
    queryKey: ["gallery", "count"],
    queryFn: () => getGallery(undefined, undefined, 50).then(d => d.items || []),
    staleTime: 60_000,
  });

  const charsTotal = charsData?.total || 0;
  const discsItems = discsData?.items || [];
  const runningCount = discsItems.filter((d: any) => d.status === "running").length;

  const statCards = [
    { label: "我的角色", value: charsTotal, icon: <Users size={20} className="text-indigo-500" /> },
    { label: "讨论总数", value: discsData?.total || 0, icon: <MessageSquare size={20} className="text-blue-500" /> },
    { label: "运行中", value: runningCount, icon: <Activity size={20} className="text-emerald-500" /> },
    { label: "画廊技能", value: galleryItems.length, icon: <Sparkles size={20} className="text-purple-500" /> },
  ];

  const statusLabel = (s: string) => {
    const map: Record<string, string> = { running: "进行中", completed: "已完成", error: "错误" };
    return map[s] || s;
  };

  return (
    <div className="p-8 max-w-6xl mx-auto space-y-8">
      <div>
        <h1 className="text-3xl font-bold tracking-tight text-slate-900">欢迎来到 MADF</h1>
        <p className="text-slate-500 mt-2 text-lg">多智能体圆桌讨论平台</p>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
        {statCards.map((stat, i) => (
          <motion.div
            key={i}
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: i * 0.1 }}
            className="bg-white p-6 rounded-2xl border border-slate-200 shadow-sm"
          >
            <div className="flex items-center gap-4">
              <div className="p-3 bg-slate-50 rounded-xl">{stat.icon}</div>
              <div>
                <div className="text-2xl font-semibold text-slate-900">{stat.value}</div>
                <div className="text-sm font-medium text-slate-500">{stat.label}</div>
              </div>
            </div>
          </motion.div>
        ))}
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
        <div className="lg:col-span-2 space-y-6">
          <div className="flex items-center justify-between">
            <h2 className="text-xl font-bold text-slate-900">最近讨论</h2>
            <Link to="/discussions" className="text-sm font-medium text-indigo-600 hover:text-indigo-700">
              查看全部
            </Link>
          </div>
          <div className="bg-white border border-slate-200 rounded-2xl overflow-hidden shadow-sm">
            {discsItems.length === 0 ? (
              <div className="p-8 text-center text-slate-400">暂无讨论，快去创建一个吧</div>
            ) : (
              <ul className="divide-y divide-slate-100">
                {discsItems.map((disc: any) => (
                  <li key={disc.id} className="p-5 hover:bg-slate-50 transition-colors">
                    <div className="flex items-center justify-between">
                      <div>
                        <h3 className="font-semibold text-slate-900">{disc.topic}</h3>
                        <div className="flex items-center gap-3 mt-1 text-sm text-slate-500">
                          <span className="flex items-center gap-1">
                            <Users size={14} /> {disc.agents?.length || 0} 个智能体
                          </span>
                        </div>
                      </div>
                      <div className="flex items-center gap-4">
                        <span
                          className={`px-2.5 py-1 rounded-full text-xs font-medium ${
                            disc.status === "running" ? "bg-green-100 text-green-700" : "bg-slate-100 text-slate-700"
                          }`}
                        >
                          {statusLabel(disc.status)}
                        </span>
                        <Link
                          to={`/discussions/${disc.id}`}
                          className="p-2 text-slate-400 hover:text-indigo-600 hover:bg-indigo-50 rounded-full transition-colors"
                        >
                          <Play size={18} />
                        </Link>
                      </div>
                    </div>
                  </li>
                ))}
              </ul>
            )}
          </div>
        </div>

        <div className="space-y-6">
          <h2 className="text-xl font-bold text-slate-900">快捷操作</h2>
          <div className="space-y-4">
            <Link
              to="/discussions/new"
              className="block p-5 bg-indigo-600 hover:bg-indigo-700 text-white rounded-2xl shadow-sm transition-colors group"
            >
              <div className="flex items-center justify-between">
                <div>
                  <h3 className="font-semibold text-lg">新建讨论</h3>
                  <p className="text-indigo-100 text-sm mt-1">开启一场新的智能体圆桌会议</p>
                </div>
                <div className="w-10 h-10 bg-indigo-500 rounded-full flex items-center justify-center group-hover:scale-110 transition-transform">
                  <Play size={20} />
                </div>
              </div>
            </Link>
            <Link
              to="/characters/generate"
              className="block p-5 bg-white border border-slate-200 hover:border-indigo-300 hover:shadow-md rounded-2xl shadow-sm transition-all group"
            >
              <div className="flex items-center justify-between">
                <div>
                  <h3 className="font-semibold text-slate-900 text-lg">生成技能</h3>
                  <p className="text-slate-500 text-sm mt-1">创建新的智能体角色</p>
                </div>
                <div className="w-10 h-10 bg-slate-50 text-slate-600 rounded-full flex items-center justify-center group-hover:bg-indigo-50 group-hover:text-indigo-600 transition-colors">
                  <Sparkles size={20} />
                </div>
              </div>
            </Link>
          </div>
        </div>
      </div>
    </div>
  );
}
