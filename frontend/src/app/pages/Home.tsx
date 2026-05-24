import { Link } from "react-router";
import { motion } from "motion/react";
import {
  ArrowRight,
  Bot,
  BrainCircuit,
  CheckCircle2,
  Clock3,
  FileCode2,
  Library,
  MessageSquare,
  Network,
  Play,
  Radio,
  ShieldCheck,
  Sparkles,
  Users,
  Zap,
} from "lucide-react";

const roles = ["战略家", "工程师", "研究者", "批判者", "主持人"];
const eventTypes = ["host_intro", "agent_think", "agent_speak_chunk", "user_intervened", "discussion_end"];

const featureBands = [
  {
    icon: BrainCircuit,
    title: "Skill 驱动角色",
    text: "角色不是简单 prompt，而是完整 SKILL.md 与 references 目录，讨论时从经历、信念和表达方式出发。",
  },
  {
    icon: Radio,
    title: "真实流式圆桌",
    text: "SSE 按事件类型推送，发言、思考、主持人摘要和用户介入都能在前端独立呈现。",
  },
  {
    icon: Network,
    title: "去中心化发言权",
    text: "每轮由 Agent 先给出发言决策，再按 confidence 仲裁发言者，全员沉默时强制推进。",
  },
  {
    icon: ShieldCheck,
    title: "业务审计可追溯",
    text: "讨论生命周期、管理操作和错误事件落入 audit_events，便于复盘、追责和教学评估。",
  },
];

const workflow = [
  "输入主题",
  "选择角色",
  "设定时长",
  "圆桌讨论",
  "回放审计",
];

export function Home() {
  return (
    <main className="min-h-screen overflow-x-hidden bg-[#f6f3ec] text-[#1d1a16]">
      <nav className="sticky top-0 z-30 border-b border-[#d8cbb7] bg-[#f6f3ec]/88 backdrop-blur-xl">
        <div className="mx-auto flex h-16 max-w-7xl items-center justify-between px-5 lg:px-8">
          <Link to="/" className="flex items-center gap-3">
            <span className="flex h-9 w-9 items-center justify-center rounded-lg bg-[#1d1a16] text-[#f0d9ad]">
              <Sparkles size={19} />
            </span>
            <span className="text-lg font-semibold tracking-tight">MADF</span>
          </Link>
          <div className="hidden items-center gap-7 text-sm font-semibold text-[#6d6254] md:flex">
            <a href="#framework" className="hover:text-[#1d1a16]">框架</a>
            <a href="#workflow" className="hover:text-[#1d1a16]">流程</a>
            <a href="#audit" className="hover:text-[#1d1a16]">审计</a>
          </div>
          <div className="flex items-center gap-2">
            <Link to="/login" className="hidden h-10 items-center rounded-lg px-3 text-sm font-semibold text-[#1d1a16] hover:bg-[#e9dfcc] sm:inline-flex">
              登录
            </Link>
            <Link to="/login?redirect=%2Fdashboard" className="inline-flex h-10 items-center gap-2 rounded-lg bg-[#1d1a16] px-4 text-sm font-semibold text-white transition hover:-translate-y-0.5 hover:bg-[#2f281f]">
              进入系统
              <ArrowRight size={16} />
            </Link>
          </div>
        </div>
      </nav>

      <section className="relative min-h-[calc(100vh-4rem)] border-b border-[#d8cbb7]">
        <div className="absolute inset-0 bg-[linear-gradient(90deg,rgba(29,26,22,0.06)_1px,transparent_1px),linear-gradient(rgba(29,26,22,0.06)_1px,transparent_1px)] bg-[size:56px_56px]" />
        <div className="absolute right-0 top-0 hidden h-full w-[44%] bg-[#1d1a16] lg:block" />
        <div className="relative mx-auto grid min-h-[calc(100vh-4rem)] max-w-7xl items-center gap-12 px-5 py-12 sm:py-16 lg:grid-cols-[minmax(0,1.02fr)_minmax(0,0.98fr)] lg:px-8">
          <motion.div initial={{ opacity: 0, y: 18 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.55 }}>
            <div className="mb-6 inline-flex items-center gap-2 rounded-lg border border-[#d8cbb7] bg-[#fffdf7] px-3 py-1.5 text-xs font-semibold text-[#8a6b37]">
              <Zap size={14} />
              Multi-Agent Discussion Framework
            </div>
            <h1 className="font-['Noto_Serif_SC'] text-4xl font-semibold leading-[1.08] tracking-tight text-[#1d1a16] sm:text-5xl md:text-7xl">
              让多个 AI 角色围坐下来，把一个问题讨论透。
            </h1>
            <p className="mt-6 max-w-2xl text-lg leading-8 text-[#6d6254]">
              面向学生和研究场景的企业级多智能体圆桌讨论平台。创建主题、选择角色、限制时间，系统自动组织发言、流式呈现并保留完整回放。
            </p>
            <div className="mt-9 flex flex-wrap gap-3">
              <Link to="/login?redirect=%2Fdashboard" className="inline-flex h-12 items-center gap-2 rounded-lg bg-[#207362] px-5 text-sm font-semibold text-white shadow-[0_14px_30px_rgba(32,115,98,0.28)] transition hover:-translate-y-0.5 hover:bg-[#185f51]">
                开始圆桌
                <Play size={17} />
              </Link>
              <a href="#framework" className="inline-flex h-12 items-center gap-2 rounded-lg border border-[#1d1a16] bg-[#f6f3ec] px-5 text-sm font-semibold text-[#1d1a16] transition hover:-translate-y-0.5 hover:bg-[#e9dfcc]">
                查看架构
                <ArrowRight size={17} />
              </a>
            </div>
          </motion.div>

          <motion.div initial={{ opacity: 0, scale: 0.96 }} animate={{ opacity: 1, scale: 1 }} transition={{ duration: 0.6, delay: 0.1 }} className="relative">
            <div className="relative mx-auto h-[520px] w-full max-w-[560px] overflow-hidden rounded-lg border border-white/15 bg-[#242019] p-4 text-white shadow-[0_30px_90px_rgba(29,26,22,0.45)] sm:h-[560px] sm:p-5">
              <div className="flex items-center justify-between border-b border-white/10 pb-4">
                <div>
                  <div className="text-xs font-semibold text-[#f0d9ad]">Live Roundtable</div>
                  <div className="mt-1 text-lg font-semibold">未来教育如何重构？</div>
                </div>
                <div className="rounded-lg border border-emerald-300/30 bg-emerald-300/10 px-3 py-1 text-xs font-semibold text-emerald-200">RUNNING</div>
              </div>

              <div className="relative mt-6 h-[280px] rounded-lg border border-white/10 bg-black/14 sm:mt-8 sm:h-[320px]">
                <div className="absolute left-1/2 top-1/2 h-44 w-44 -translate-x-1/2 -translate-y-1/2 rounded-full border border-[#f0d9ad]/30 sm:h-52 sm:w-52" />
                <div className="absolute left-1/2 top-1/2 h-24 w-24 -translate-x-1/2 -translate-y-1/2 rounded-full bg-[#f0d9ad] shadow-[0_0_80px_rgba(240,217,173,0.34)] sm:h-28 sm:w-28" />
                <div className="absolute left-1/2 top-1/2 flex h-16 w-16 -translate-x-1/2 -translate-y-1/2 items-center justify-center rounded-full bg-[#207362] sm:h-20 sm:w-20">
                  <MessageSquare size={28} />
                </div>
                {roles.map((role, index) => {
                  const pos = [
                    "left-7 top-8",
                    "right-7 top-8",
                    "left-8 bottom-9",
                    "right-8 bottom-9",
                    "left-1/2 top-3 -translate-x-1/2",
                  ][index];
                  return (
                    <div key={role} className={`absolute ${pos} flex max-w-[128px] items-center gap-2 rounded-lg border border-white/12 bg-white/10 px-2.5 py-2 backdrop-blur sm:max-w-none sm:px-3`}>
                      <span className="flex h-8 w-8 items-center justify-center rounded-lg bg-[#f0d9ad] text-[#1d1a16]">
                        <Bot size={16} />
                      </span>
                      <span className="truncate text-xs font-semibold">{role}</span>
                    </div>
                  );
                })}
              </div>

              <div className="mt-5 space-y-3">
                {eventTypes.map((event, index) => (
                  <div key={event} className="flex items-center justify-between rounded-lg border border-white/10 bg-white/[0.06] px-3 py-2">
                    <span className="font-mono text-xs text-[#d8cbb7]">{event}</span>
                    <span className="h-1.5 w-20 overflow-hidden rounded-full bg-white/10">
                      <span className="block h-full rounded-full bg-[#db9a34]" style={{ width: `${42 + index * 11}%` }} />
                    </span>
                  </div>
                ))}
              </div>
            </div>
          </motion.div>
        </div>
      </section>

      <section id="framework" className="border-b border-[#d8cbb7] bg-[#fffdf7] py-24">
        <div className="mx-auto max-w-7xl px-5 lg:px-8">
          <div className="max-w-3xl">
            <p className="text-xs font-semibold uppercase tracking-[0.24em] text-[#8a6b37]">Framework</p>
            <h2 className="mt-4 font-['Noto_Serif_SC'] text-4xl font-semibold leading-tight md:text-5xl">
              不是聊天窗口，是一套讨论编排系统。
            </h2>
          </div>
          <div className="mt-12 grid gap-4 md:grid-cols-2 xl:grid-cols-4">
            {featureBands.map((item) => {
              const Icon = item.icon;
              return (
                <div key={item.title} className="rounded-lg border border-[#d8cbb7] bg-[#f9f4e9] p-5">
                  <div className="mb-6 flex h-11 w-11 items-center justify-center rounded-lg bg-[#1d1a16] text-[#f0d9ad]">
                    <Icon size={21} />
                  </div>
                  <h3 className="text-lg font-semibold">{item.title}</h3>
                  <p className="mt-3 text-sm leading-6 text-[#6d6254]">{item.text}</p>
                </div>
              );
            })}
          </div>
        </div>
      </section>

      <section id="workflow" className="bg-[#f6f3ec] py-24">
        <div className="mx-auto grid max-w-7xl gap-10 px-5 lg:grid-cols-[minmax(0,0.85fr)_minmax(0,1.15fr)] lg:px-8">
          <div>
            <p className="text-xs font-semibold uppercase tracking-[0.24em] text-[#8a6b37]">Workflow</p>
            <h2 className="mt-4 font-['Noto_Serif_SC'] text-4xl font-semibold leading-tight md:text-5xl">
              从一个问题，到一份可回放的讨论记录。
            </h2>
            <p className="mt-5 text-base leading-7 text-[#6d6254]">
              一期能力覆盖创建、发言仲裁、SSE 流、用户介入、主持人总结和历史回放。
            </p>
          </div>

          <div className="rounded-lg border border-[#252018] bg-[#1d1a16] p-5 text-white">
            <div className="grid gap-3">
              {workflow.map((step, index) => (
                <div key={step} className="grid grid-cols-[44px_minmax(0,1fr)_auto] items-center gap-3 rounded-lg border border-white/10 bg-white/[0.06] p-4 sm:grid-cols-[52px_minmax(0,1fr)_auto] sm:gap-4">
                  <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-[#f0d9ad] font-semibold text-[#1d1a16]">
                    {String(index + 1).padStart(2, "0")}
                  </div>
                  <div>
                    <div className="font-semibold">{step}</div>
                    <div className="mt-1 text-xs text-[#d8cbb7]">
                      {index === 0 && "把开放问题转成讨论主题"}
                      {index === 1 && "从我的角色和画廊中多选参与者"}
                      {index === 2 && "系统按时自动总结并结束"}
                      {index === 3 && "Agent 决策后竞争发言权"}
                      {index === 4 && "消息、审计、摘要全部保留"}
                    </div>
                  </div>
                  <CheckCircle2 className="text-[#db9a34]" size={20} />
                </div>
              ))}
            </div>
          </div>
        </div>
      </section>

      <section id="audit" className="border-y border-[#d8cbb7] bg-[#fffdf7] py-24">
        <div className="mx-auto grid max-w-7xl gap-10 px-5 lg:grid-cols-[1.1fr_0.9fr] lg:px-8">
          <div className="rounded-lg border border-[#d8cbb7] bg-[#f9f4e9] p-6">
            <div className="mb-6 flex items-center gap-3">
              <ShieldCheck className="text-[#207362]" size={25} />
              <h2 className="text-2xl font-semibold">审计后台不是附属品</h2>
            </div>
            <div className="grid gap-3">
              {[
                ["audit_events", "记录讨论、管理、错误事件"],
                ["Redis Pub/Sub", "旁路推送审计实时流"],
                ["service JWT", "审计后端代理主系统管理接口"],
                ["read-only mirror", "审计后端只读查询主事件表"],
              ].map(([name, text]) => (
                <div key={name} className="flex flex-col gap-1 rounded-lg border border-[#e4dccd] bg-[#fffdf7] px-4 py-3 sm:flex-row sm:items-center sm:justify-between sm:gap-4">
                  <span className="break-all font-mono text-sm font-semibold text-[#1d1a16]">{name}</span>
                  <span className="text-sm leading-6 text-[#6d6254] sm:text-right">{text}</span>
                </div>
              ))}
            </div>
          </div>

          <div className="flex flex-col justify-center">
            <p className="text-xs font-semibold uppercase tracking-[0.24em] text-[#8a6b37]">For Students</p>
            <h2 className="mt-4 font-['Noto_Serif_SC'] text-4xl font-semibold leading-tight">
              适合课堂讨论、论文选题、观点拆解和方案评审。
            </h2>
            <p className="mt-5 text-base leading-7 text-[#6d6254]">
              让不同立场的角色先思考，再按确信度发言。用户可以随时介入，讨论结束后再回放整场过程。
            </p>
            <div className="mt-7 grid gap-3 sm:grid-cols-3">
              {[
                [Users, "50+ 并发"],
                [Clock3, "限时讨论"],
                [FileCode2, "Skill 管理"],
              ].map(([Icon, label]) => {
                const LucideIcon = Icon as typeof Users;
                return (
                  <div key={label as string} className="rounded-lg border border-[#d8cbb7] bg-[#f6f3ec] p-4">
                    <LucideIcon className="mb-3 text-[#207362]" size={21} />
                    <div className="text-sm font-semibold">{label as string}</div>
                  </div>
                );
              })}
            </div>
          </div>
        </div>
      </section>

      <section className="bg-[#1d1a16] py-20 text-white">
        <div className="mx-auto flex max-w-7xl flex-col items-start justify-between gap-8 px-5 lg:flex-row lg:items-center lg:px-8">
          <div>
            <p className="text-xs font-semibold uppercase tracking-[0.24em] text-[#f0d9ad]">Ready</p>
            <h2 className="mt-4 font-['Noto_Serif_SC'] text-4xl font-semibold">进入主系统，创建第一场圆桌。</h2>
          </div>
          <Link to="/login?redirect=%2Fdashboard" className="inline-flex h-12 items-center gap-2 rounded-lg bg-[#f0d9ad] px-5 text-sm font-semibold text-[#1d1a16] transition hover:-translate-y-0.5 hover:bg-[#ffe3aa]">
            登录并开始
            <ArrowRight size={17} />
          </Link>
        </div>
      </section>
    </main>
  );
}
