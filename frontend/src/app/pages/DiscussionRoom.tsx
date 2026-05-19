import { Fragment, useState, useEffect, useRef, useCallback } from "react";
import { Link, useParams } from "react-router";
import { ArrowLeft, Users, Send, User, Mic, Brain, Clock } from "lucide-react";
import { motion, AnimatePresence } from "motion/react";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { getDiscussion, getMessages, buildStreamUrl, intervene } from "../api/discussions";
import { toast } from "sonner";

function displayName(name: string): string {
  return name.replace(/-perspective$/, "");
}

function renderMarkdown(text: string): string {
  // Blockquote: lines starting with >  become styled blockquote
  let html = text.replace(/^&gt; (.+)$/gm, '<blockquote class="border-l-4 border-slate-300 pl-4 my-2 italic text-slate-600">$1</blockquote>');
  // Bold
  html = html.replace(/\*\*(.+?)\*\*/g, "<strong>$1</strong>");
  return html;
}

function escapeHtml(text: string): string {
  return text
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;");
}

interface Message {
  id: string | number;
  type: "host" | "agent" | "user";
  mode?: "thought" | "spoken";
  text: string;
  agent: string;
  confidence?: number;
}

function formatMessages(raw: any[]): Message[] {
  return raw.map((m: any) => ({
    id: m.id || Math.random(),
    type: m.message_type === "host_intro" || m.message_type === "host_summary" ? "host" : m.message_type === "user_intervene" ? "user" : "agent",
    mode: m.message_type === "agent_think" ? "thought" : "spoken",
    text: m.content,
    agent: displayName(m.agent_name || "系统"),
    confidence: m.confidence,
  }));
}

export function DiscussionRoom() {
  const { id } = useParams();
  const queryClient = useQueryClient();
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState("");
  const [connected, setConnected] = useState(false);
  const [speaking, setSpeaking] = useState<string | null>(null);
  const [countdown, setCountdown] = useState("");
  const endRef = useRef<HTMLDivElement>(null);
  const esRef = useRef<EventSource | null>(null);
  const currentSpeakRef = useRef<{ agent: string; text: string }>({ agent: "", text: "" });
  const hostStreamRef = useRef<{ text: string; id: number }>({ text: "", id: 0 });

  const { data: discussion } = useQuery({
    queryKey: ["discussion", id],
    queryFn: () => getDiscussion(id!),
    enabled: !!id,
    staleTime: 5_000,
    refetchInterval: 3000,
  });

  // Countdown timer for running discussions
  useEffect(() => {
    if (!discussion || discussion.status !== "running" || !discussion.started_at) {
      setCountdown("");
      return;
    }
    const start = new Date(discussion.started_at).getTime();
    const duration = (discussion.duration || 0) * 1000;
    const end = start + duration;

    const tick = () => {
      const now = Date.now();
      const remaining = Math.max(0, end - now);
      const s = Math.ceil(remaining / 1000);
      const m = Math.floor(s / 60);
      const sec = s % 60;
      setCountdown(`${m}:${String(sec).padStart(2, "0")}`);
    };
    tick();
    const timer = setInterval(tick, 1000);
    return () => clearInterval(timer);
  }, [discussion?.status, discussion?.started_at, discussion?.duration]);

  const formatTime = (iso: string | null | undefined) => {
    if (!iso) return "";
    return new Date(iso).toLocaleTimeString("zh-CN", { hour: "2-digit", minute: "2-digit" });
  };

  // Load historical messages for running AND completed discussions.
  // Running discussions need this because SSE (Redis Pub/Sub) does not replay
  // events emitted before the client subscribed — host_intro is typically missed.
  useEffect(() => {
    if (!id || discussion?.status === "pending") return;
    getMessages(id).then((msgs) => {
      const items = Array.isArray(msgs) ? msgs : msgs?.items || [];
      setMessages(formatMessages(items));
    }).catch(() => {});
  }, [id, discussion?.status]);

  // SSE live stream
  useEffect(() => {
    if (!id) return;
    const es = new EventSource(buildStreamUrl(id));
    esRef.current = es;

    es.addEventListener("heartbeat", () => setConnected(true));

    es.addEventListener("catchup_msg", (e) => {
      const d = JSON.parse(e.data);
      const isHost = d.message_type === "host_intro" || d.message_type === "host_summary";
      const isUser = d.message_type === "user_intervene";
      const msgType = isUser ? "user" : isHost ? "host" : "agent";
      const mode = d.message_type === "agent_think" ? "thought" : "spoken";
      setMessages((prev) => [...prev, {
        id: Date.now() + Math.random(),
        type: msgType as "agent" | "host" | "user",
        mode: mode as "thought" | "spoken",
        text: d.content,
        agent: displayName(d.agent_name || "系统"),
        confidence: d.confidence,
      }]);
    });

    es.addEventListener("host_intro_start", () => {
      setMessages((prev) => {
        if (prev.some(m => m.type === "host" && m.agent === "主持人")) return prev;
        const newId = Date.now();
        hostStreamRef.current = { text: "", id: newId };
        return [...prev, { id: newId, type: "host", text: "", agent: "主持人" }];
      });
    });

    es.addEventListener("host_intro_chunk", (e) => {
      const d = JSON.parse(e.data);
      hostStreamRef.current.text += d.content || "";
      const hid = hostStreamRef.current.id;
      setMessages((prev) => {
        const last = prev[prev.length - 1];
        if (last && last.type === "host" && last.id === hid) {
          return [...prev.slice(0, -1), { ...last, text: hostStreamRef.current.text }];
        }
        return [...prev, { id: hid, type: "host", text: hostStreamRef.current.text, agent: "主持人" }];
      });
    });

    es.addEventListener("host_intro", (e) => {
      const d = JSON.parse(e.data);
      const hid = hostStreamRef.current.id;
      setMessages((prev) => {
        const last = prev[prev.length - 1];
        if (last && last.type === "host" && last.id === hid) {
          return [...prev.slice(0, -1), { ...last, text: d.content }];
        }
        return [...prev, { id: Date.now(), type: "host", text: d.content, agent: "主持人" }];
      });
    });

    es.addEventListener("agent_think", (e) => {
      const d = JSON.parse(e.data);
      setMessages((prev) => [...prev, { id: Date.now(), type: "agent", mode: "thought", text: d.reasoning || d.content || "", agent: displayName(d.agent_name), confidence: d.confidence }]);
    });

    es.addEventListener("agent_speak_start", (e) => {
      const d = JSON.parse(e.data);
      setSpeaking(displayName(d.agent_name));
      currentSpeakRef.current = { agent: displayName(d.agent_name), text: "" };
    });

    es.addEventListener("agent_speak_chunk", (e) => {
      const d = JSON.parse(e.data);
      currentSpeakRef.current.text += d.content || "";
      // Do NOT add to messages during streaming — the `speaking` indicator
      // renders the live typewriter bubble.  Only persist on `agent_speak_end`.
    });

    es.addEventListener("agent_speak_end", (e) => {
      const d = JSON.parse(e.data);
      setSpeaking(null);
      setMessages((prev) => [...prev, {
        id: Date.now(), type: "agent", mode: "spoken",
        text: d.content || currentSpeakRef.current.text,
        agent: displayName(d.agent_name || currentSpeakRef.current.agent),
      }]);
      currentSpeakRef.current = { agent: "", text: "" };
    });
    es.addEventListener("host_summary_start", () => {
      setMessages((prev) => {
        if (prev.some(m => m.type === "host" && m.agent === "主持人总结")) return prev;
        const newId = Date.now();
        hostStreamRef.current = { text: "", id: newId };
        return [...prev, { id: newId, type: "host", text: "", agent: "主持人总结" }];
      });
    });

    es.addEventListener("host_summary_chunk", (e) => {
      const d = JSON.parse(e.data);
      hostStreamRef.current.text += d.content || "";
      const hid = hostStreamRef.current.id;
      setMessages((prev) => {
        const last = prev[prev.length - 1];
        if (last && last.type === "host" && last.id === hid) {
          return [...prev.slice(0, -1), { ...last, text: hostStreamRef.current.text }];
        }
        return [...prev, { id: hid, type: "host", text: hostStreamRef.current.text, agent: "主持人总结" }];
      });
    });

    es.addEventListener("host_summary", (e) => {
      const d = JSON.parse(e.data);
      const hid = hostStreamRef.current.id;
      setMessages((prev) => {
        const last = prev[prev.length - 1];
        if (last && last.type === "host" && last.id === hid) {
          return [...prev.slice(0, -1), { ...last, text: d.content }];
        }
        return [...prev, { id: Date.now(), type: "host", text: d.content, agent: "主持人总结" }];
      });
    });
    es.addEventListener("discussion_end", () => {
      setConnected(false);
      queryClient.invalidateQueries({ queryKey: ["discussion", id] });
      queryClient.invalidateQueries({ queryKey: ["discussions"] });
    });
    es.addEventListener("user_intervened", (e) => {
      const d = JSON.parse(e.data);
      const agentName = d.username || d.user_id?.slice(0, 8) || "用户";
      setMessages((prev) => [...prev, { id: Date.now(), type: "user", text: d.content, agent: agentName }]);
    });
    es.onerror = () => setConnected(false);

    return () => { es.close(); esRef.current = null; };
  }, [id]);

  useEffect(() => {
    endRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  const handleSend = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!input.trim() || !id) return;
    try {
      await intervene(id, input.trim());
      setInput("");
    } catch (err: any) {
      toast.error(err.response?.data?.message || "发送失败");
    }
  };

  return (
    <div className="h-full flex flex-col bg-slate-50">
      {/* Header */}
      <div className="border-b border-slate-200 bg-white flex-shrink-0 shadow-sm z-10 px-6 py-3">
        <div className="flex items-center gap-4">
          <Link to="/discussions" className="text-slate-400 hover:text-slate-900 transition-colors shrink-0"><ArrowLeft size={20} /></Link>
          <div className="flex-1 min-w-0">
            <h1 className="font-bold text-slate-900 text-lg truncate">{discussion?.topic || "加载中..."}</h1>
            <div className="flex items-center gap-3 text-xs font-medium text-slate-500 mt-0.5 flex-wrap">
              <span className="flex items-center gap-1">
                <span className={`w-2 h-2 rounded-full ${discussion?.status === "running" ? "bg-emerald-500 animate-pulse" : "bg-slate-400"}`} />
                {discussion?.status === "running" ? "进行中" : discussion?.status === "completed" ? "已结束" : discussion?.status || "-"}
              </span>
              <span>•</span>
              <span className="flex items-center gap-1"><Users size={12} /> {discussion?.agents?.length || 0} 个智能体</span>
              <span>•</span>
              <span className="flex items-center gap-1"><Clock size={12} /> {formatTime(discussion?.started_at)} — {discussion?.ended_at ? formatTime(discussion?.ended_at) : "至今"}</span>
              {discussion?.status === "running" && countdown && (
                <><span>•</span><span className="text-amber-600 font-mono font-medium">⏳ {countdown}</span></>
              )}
              {connected && (<><span>•</span><span className="text-emerald-600">实时连接中</span></>)}
            </div>
            {discussion?.agents && discussion.agents.length > 0 && (
              <div className="flex items-center gap-1.5 mt-1.5 flex-wrap">
                {discussion.agents.map((a: any) => (
                  <span key={a.skill_id} className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full bg-indigo-50 text-indigo-700 text-[11px] font-medium">
                    <span className="w-3.5 h-3.5 rounded-full bg-indigo-200 text-indigo-600 flex items-center justify-center text-[8px] font-bold">{displayName(a.name).charAt(0)}</span>
                    {displayName(a.name).length > 18 ? displayName(a.name).slice(0, 16) + "…" : displayName(a.name)}
                  </span>
                ))}
              </div>
            )}
          </div>
        </div>
      </div>

      <div className="flex-1 overflow-y-auto p-6 scroll-smooth">
        <div className="max-w-4xl mx-auto space-y-6">
          {messages.length === 0 && (
            <div className="text-center py-16 text-slate-400"><p className="text-lg mb-2">等待讨论开始...</p>{discussion?.status === "completed" && <p>讨论已结束</p>}</div>
          )}
          <AnimatePresence mode="popLayout">
            {messages.map((msg, index) => {
              // Look back up to 5 messages to find a thought from the same agent.
              // Needed because multiple agents' think messages are interleaved.
              const prevThought = (() => {
                for (let i = index - 1; i >= Math.max(0, index - 5); i--) {
                  if (messages[i].agent === msg.agent && messages[i].mode === "thought") return messages[i];
                }
                return null;
              })();
              const isTransition = prevThought && msg.mode === "spoken";
              const delay = Math.min(index * 0.03, 0.3); // stagger up to 300ms
              return (
                <Fragment key={msg.id}>
                  {isTransition && (
                    <motion.div
                      initial={{ opacity: 0, scale: 0.8, y: -8 }}
                      animate={{ opacity: 1, scale: 1, y: 0 }}
                      exit={{ opacity: 0, scale: 0.9, y: -4 }}
                      transition={{ type: "spring", stiffness: 300, damping: 24, delay: delay + 0.3 }}
                      className="flex justify-center my-3"
                    >
                      <span className="text-xs font-medium text-slate-400 bg-slate-100 px-4 py-1.5 rounded-full flex items-center gap-2 shadow-sm border border-slate-200/50">
                        <span className="w-1.5 h-1.5 rounded-full bg-amber-400 animate-pulse" />
                        {msg.agent} 即将发言
                      </span>
                    </motion.div>
                  )}
                  <motion.div
                    initial={msg.type === "agent" && msg.mode === "spoken" ? false : { opacity: 0, y: 16, scale: 0.97 }}
                    animate={msg.type === "agent" && msg.mode === "spoken" ? {} : { opacity: 1, y: 0, scale: 1 }}
                    exit={{ opacity: 0, scale: 0.95, transition: { duration: 0.15 } }}
                    transition={msg.type === "agent" && msg.mode === "spoken"
                      ? { duration: 0 }
                      : { type: "spring", stiffness: 260, damping: 26, delay }}
                    className={`flex gap-4 ${msg.type === "user" ? "flex-row-reverse" : ""}`}
                  >
                    <div className={`w-10 h-10 rounded-full flex items-center justify-center flex-shrink-0 font-bold text-sm shadow-sm ${msg.type === "host" ? "bg-amber-100 text-amber-700" : msg.type === "user" ? "bg-indigo-600 text-white" : "bg-slate-800 text-white"}`}>
                      {msg.type === "host" ? <Mic size={18} /> : msg.type === "user" ? <User size={18} /> : msg.agent.charAt(0)}
                    </div>
                    <div className={`max-w-[80%] ${msg.type === "user" ? "items-end flex flex-col" : "items-start flex flex-col"}`}>
                      <div className={`flex items-center gap-2 mb-1 px-1 ${msg.type === "user" ? "flex-row-reverse" : ""}`}>
                        <span className="font-semibold text-sm text-slate-700">{msg.agent}</span>
                        {msg.type === "agent" && msg.mode === "thought" && (<span className="text-[10px] font-medium text-slate-500 bg-slate-100 px-1.5 py-0.5 rounded flex items-center gap-1"><Brain size={10} /> 内部思考</span>)}
                        {msg.type === "agent" && msg.mode === "thought" && msg.confidence != null && (<span className="text-[10px] font-mono text-slate-400 bg-slate-200/50 px-1.5 py-0.5 rounded">置信度: {msg.confidence}</span>)}
                      </div>
                      <div className={`p-4 shadow-sm text-[15px] leading-relaxed ${msg.type === "user" ? "bg-indigo-600 text-white rounded-2xl rounded-tr-none" : msg.type === "host" ? "bg-amber-50 text-amber-900 border border-amber-200/50 rounded-2xl rounded-tl-none" : msg.mode === "thought" ? "bg-slate-50 text-slate-500 border-2 border-dashed border-slate-200 rounded-3xl italic" : "bg-white text-slate-800 border border-slate-200 rounded-2xl rounded-tl-none"}`} dangerouslySetInnerHTML={{ __html: renderMarkdown(escapeHtml(msg.text)) }} />
                    </div>
                  </motion.div>
                </Fragment>
              );
            })}
          </AnimatePresence>
          {speaking && (
            <motion.div
              initial={{ opacity: 0, y: 12, scale: 0.96 }}
              animate={{ opacity: 1, y: 0, scale: 1 }}
              exit={{ opacity: 0, scale: 0.95, transition: { duration: 0.12 } }}
              transition={{ type: "spring", stiffness: 280, damping: 24 }}
              className="flex gap-4"
            >
              <div className="w-10 h-10 rounded-full bg-slate-800 text-white flex items-center justify-center flex-shrink-0 font-bold text-sm shadow-sm">{speaking.charAt(0)}</div>
              <div className="max-w-[80%] items-start flex flex-col">
                <div className="flex items-center gap-2 mb-1 px-1">
                  <span className="font-semibold text-sm text-slate-700">{speaking}</span>
                  <span className="text-[10px] font-medium text-emerald-600 bg-emerald-50 px-1.5 py-0.5 rounded border border-emerald-100 flex items-center gap-1"><span className="w-1.5 h-1.5 rounded-full bg-emerald-500 animate-pulse" />发言中</span>
                </div>
                <div className="p-4 rounded-2xl shadow-sm text-[15px] leading-relaxed bg-white text-slate-800 border border-slate-200 rounded-tl-none min-w-[60px]">
                  {currentSpeakRef.current.text || (<span className="flex gap-1"><span className="w-2 h-2 bg-slate-400 rounded-full animate-bounce" style={{ animationDelay: "0ms" }} /><span className="w-2 h-2 bg-slate-400 rounded-full animate-bounce" style={{ animationDelay: "150ms" }} /><span className="w-2 h-2 bg-slate-400 rounded-full animate-bounce" style={{ animationDelay: "300ms" }} /></span>)}
                </div>
              </div>
            </motion.div>
          )}
          <div ref={endRef} />
        </div>
      </div>
      {discussion?.status === "running" && (
        <div className="bg-white border-t border-slate-200 p-4 flex-shrink-0">
          <form onSubmit={handleSend} className="max-w-4xl mx-auto flex gap-4">
            <input type="text" value={input} onChange={(e) => setInput(e.target.value)} placeholder="介入讨论... (按回车键发送)" className="flex-1 px-5 py-3.5 bg-slate-50 border border-slate-200 rounded-xl focus:ring-2 focus:ring-indigo-600 focus:bg-white outline-none transition-all shadow-sm" />
            <button type="submit" disabled={!input.trim()} className="bg-indigo-600 hover:bg-indigo-700 disabled:opacity-50 disabled:cursor-not-allowed text-white px-6 py-3.5 rounded-xl font-bold flex items-center justify-center transition-colors shadow-sm"><Send size={20} /></button>
          </form>
        </div>
      )}
    </div>
  );
}
