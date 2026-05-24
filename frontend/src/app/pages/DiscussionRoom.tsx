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
  let html = text.replace(/^&gt; (.+)$/gm, '<blockquote class="border-l-4 border-[#d8cbb7] pl-4 my-2 italic text-[#6d6254]">$1</blockquote>');
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
  status?: "streaming" | "timeout";
}

const EMPTY_SPEECH_TEXT = "本轮发言生成超时，已跳过空白内容。";
const STREAMING_TEXT = "正在生成发言...";

function normalizeMessageText(messageType: string, content: string | null | undefined): string {
  if (messageType === "agent_speak" && !String(content || "").trim()) return EMPTY_SPEECH_TEXT;
  return String(content || "");
}

function formatMessages(raw: any[]): Message[] {
  return raw.map((m: any) => ({
    id: m.id || Math.random(),
    type: m.message_type === "host_intro" || m.message_type === "host_summary" ? "host" : m.message_type === "user_intervene" ? "user" : "agent",
    mode: m.message_type === "agent_think" ? "thought" : "spoken",
    text: normalizeMessageText(m.message_type, m.content),
    agent: displayName(m.agent_name || "系统"),
    confidence: m.confidence,
    status: m.message_type === "agent_speak" && !String(m.content || "").trim() ? "timeout" : undefined,
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
  const currentSpeakRef = useRef<{ agent: string; text: string; id: string | number | null }>({ agent: "", text: "", id: null });
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
        text: normalizeMessageText(d.message_type, d.content),
        agent: displayName(d.agent_name || "系统"),
        confidence: d.confidence,
        status: d.message_type === "agent_speak" && !String(d.content || "").trim() ? "timeout" : undefined,
      }]);
    });

    es.addEventListener("host_intro_start", () => {
      setMessages((prev) => {
        if (prev.some(m => m.type === "host" && m.agent === "主持人")) return prev;
        const newId = Date.now();
        hostStreamRef.current = { text: "", id: newId };
        return [...prev, { id: newId, type: "host", text: "主持人正在准备开场...", agent: "主持人", status: "streaming" }];
      });
    });

    es.addEventListener("host_intro_chunk", (e) => {
      const d = JSON.parse(e.data);
      hostStreamRef.current.text += d.content || "";
      const hid = hostStreamRef.current.id;
      setMessages((prev) => {
        const last = prev[prev.length - 1];
        if (last && last.type === "host" && last.id === hid) {
          return [...prev.slice(0, -1), { ...last, text: hostStreamRef.current.text, status: "streaming" }];
        }
        return [...prev, { id: hid, type: "host", text: hostStreamRef.current.text, agent: "主持人", status: "streaming" }];
      });
    });

    es.addEventListener("host_intro", (e) => {
      const d = JSON.parse(e.data);
      const hid = hostStreamRef.current.id;
      setMessages((prev) => {
        const last = prev[prev.length - 1];
        if (last && last.type === "host" && last.id === hid) {
          return [...prev.slice(0, -1), { ...last, text: d.content, status: undefined }];
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
      const agent = displayName(d.agent_name);
      const messageId = `speak-${d.round}-${agent}-${Date.now()}`;
      setSpeaking(agent);
      currentSpeakRef.current = { agent, text: "", id: messageId };
      setMessages((prev) => [...prev, {
        id: messageId,
        type: "agent",
        mode: "spoken",
        text: STREAMING_TEXT,
        agent,
        status: "streaming",
      }]);
    });

    es.addEventListener("agent_speak_chunk", (e) => {
      const d = JSON.parse(e.data);
      currentSpeakRef.current.text += d.content || "";
      const currentId = currentSpeakRef.current.id;
      setMessages((prev) => prev.map((msg) => (
        msg.id === currentId
          ? { ...msg, text: currentSpeakRef.current.text || STREAMING_TEXT, status: "streaming" }
          : msg
      )));
    });

    es.addEventListener("agent_speak_timeout", (e) => {
      const d = JSON.parse(e.data);
      const text = d.content || EMPTY_SPEECH_TEXT;
      const currentId = currentSpeakRef.current.id;
      setSpeaking(null);
      setMessages((prev) => prev.map((msg) => (
        msg.id === currentId
          ? { ...msg, text, status: "timeout" }
          : msg
      )));
    });

    es.addEventListener("agent_speak_end", (e) => {
      const d = JSON.parse(e.data);
      setSpeaking(null);
      const finalText = d.content || currentSpeakRef.current.text || EMPTY_SPEECH_TEXT;
      const currentId = currentSpeakRef.current.id;
      setMessages((prev) => {
        if (currentId && prev.some((msg) => msg.id === currentId)) {
          return prev.map((msg) => (
            msg.id === currentId
              ? {
                  ...msg,
                  text: finalText,
                  agent: displayName(d.agent_name || currentSpeakRef.current.agent),
                  status: d.empty_speech ? "timeout" : undefined,
                }
              : msg
          ));
        }
        return [...prev, {
          id: Date.now(), type: "agent", mode: "spoken",
          text: finalText,
          agent: displayName(d.agent_name || currentSpeakRef.current.agent),
          status: d.empty_speech ? "timeout" : undefined,
        }];
      });
      currentSpeakRef.current = { agent: "", text: "", id: null };
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
    <div className="h-full flex flex-col bg-[#f6f3ec] text-[#1d1a16]">
      {/* Header */}
      <div className="border-b border-[#d8cbb7] bg-[#fffdf7] flex-shrink-0 shadow-[0_10px_30px_rgba(53,45,32,0.08)] z-10 px-6 py-3">
        <div className="flex items-center gap-4">
          <Link to="/discussions" className="text-[#8a6b37] hover:text-[#1d1a16] transition-colors shrink-0"><ArrowLeft size={20} /></Link>
          <div className="flex-1 min-w-0">
            <h1 className="font-bold text-[#1d1a16] text-lg truncate">{discussion?.topic || "加载中..."}</h1>
            <div className="flex items-center gap-3 text-xs font-medium text-[#6d6254] mt-0.5 flex-wrap">
              <span className="flex items-center gap-1">
                <span className={`w-2 h-2 rounded-full ${discussion?.status === "running" ? "bg-[#207362] animate-pulse" : "bg-[#9a8b76]"}`} />
                {discussion?.status === "running" ? "进行中" : discussion?.status === "completed" ? "已结束" : discussion?.status || "-"}
              </span>
              <span>•</span>
              <span className="flex items-center gap-1"><Users size={12} /> {discussion?.agents?.length || 0} 个智能体</span>
              <span>•</span>
              <span className="flex items-center gap-1"><Clock size={12} /> {formatTime(discussion?.started_at)} — {discussion?.ended_at ? formatTime(discussion?.ended_at) : "至今"}</span>
              {discussion?.status === "running" && countdown && (
                <><span>•</span><span className="text-[#8a5c16] font-mono font-medium">⏳ {countdown}</span></>
              )}
              {connected && (<><span>•</span><span className="text-[#207362]">实时连接中</span></>)}
            </div>
            {discussion?.agents && discussion.agents.length > 0 && (
              <div className="flex items-center gap-1.5 mt-1.5 flex-wrap">
                {discussion.agents.map((a: any) => (
                  <span key={a.skill_id} className="inline-flex items-center gap-1 px-2 py-0.5 rounded-lg border border-[#207362]/25 bg-[#207362]/10 text-[#185f51] text-[11px] font-medium">
                    <span className="w-3.5 h-3.5 rounded-full bg-[#207362] text-white flex items-center justify-center text-[8px] font-bold">{displayName(a.name).charAt(0)}</span>
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
            <div className="text-center py-16 text-[#9a8b76]"><p className="text-lg mb-2">等待讨论开始...</p>{discussion?.status === "completed" && <p>讨论已结束</p>}</div>
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
              const displayText = msg.text.trim() || (msg.status === "streaming" ? STREAMING_TEXT : EMPTY_SPEECH_TEXT);
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
                      <span className="text-xs font-medium text-[#6d6254] bg-[#fffdf7] px-4 py-1.5 rounded-lg flex items-center gap-2 shadow-sm border border-[#d8cbb7]">
                        <span className="w-1.5 h-1.5 rounded-full bg-[#db9a34] animate-pulse" />
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
                    <div className={`w-10 h-10 rounded-lg flex items-center justify-center flex-shrink-0 font-bold text-sm shadow-sm ${msg.type === "host" ? "bg-[#f0d9ad] text-[#1d1a16]" : msg.type === "user" ? "bg-[#207362] text-white" : "bg-[#1d1a16] text-[#f0d9ad]"}`}>
                      {msg.type === "host" ? <Mic size={18} /> : msg.type === "user" ? <User size={18} /> : msg.agent.charAt(0)}
                    </div>
                    <div className={`max-w-[80%] ${msg.type === "user" ? "items-end flex flex-col" : "items-start flex flex-col"}`}>
                      <div className={`flex items-center gap-2 mb-1 px-1 ${msg.type === "user" ? "flex-row-reverse" : ""}`}>
	                        <span className="font-semibold text-sm text-[#1d1a16]">{msg.agent}</span>
	                        {msg.type === "agent" && msg.mode === "thought" && (<span className="text-[10px] font-medium text-[#6d6254] bg-[#f9f4e9] px-1.5 py-0.5 rounded flex items-center gap-1"><Brain size={10} /> 内部思考</span>)}
	                        {msg.type === "agent" && msg.mode === "spoken" && msg.status === "streaming" && (<span className="text-[10px] font-medium text-[#185f51] bg-[#207362]/10 px-1.5 py-0.5 rounded border border-[#207362]/20 flex items-center gap-1"><span className="w-1.5 h-1.5 rounded-full bg-[#207362] animate-pulse" />发言中</span>)}
	                        {msg.type === "agent" && msg.mode === "spoken" && msg.status === "timeout" && (<span className="text-[10px] font-medium text-[#8a5c16] bg-[#f9f4e9] px-1.5 py-0.5 rounded border border-[#d8cbb7]">生成超时</span>)}
	                        {msg.type === "agent" && msg.mode === "thought" && msg.confidence != null && (<span className="text-[10px] font-mono text-[#9a8b76] bg-[#e9dfcc]/60 px-1.5 py-0.5 rounded">置信度: {msg.confidence}</span>)}
	                      </div>
	                      <div className={`p-4 shadow-sm text-[15px] leading-relaxed ${msg.type === "user" ? "bg-[#207362] text-white rounded-lg rounded-tr-none" : msg.type === "host" ? "bg-[#f0d9ad]/55 text-[#1d1a16] border border-[#d8cbb7] rounded-lg rounded-tl-none" : msg.mode === "thought" ? "bg-[#f9f4e9] text-[#6d6254] border-2 border-dashed border-[#d8cbb7] rounded-lg italic" : "bg-[#fffdf7] text-[#1d1a16] border border-[#d8cbb7] rounded-lg rounded-tl-none"}`} dangerouslySetInnerHTML={{ __html: renderMarkdown(escapeHtml(displayText)) }} />
                    </div>
                  </motion.div>
                </Fragment>
              );
            })}
          </AnimatePresence>
          <div ref={endRef} />
        </div>
      </div>
      {discussion?.status === "running" && (
        <div className="bg-[#fffdf7] border-t border-[#d8cbb7] p-4 flex-shrink-0">
          <form onSubmit={handleSend} className="max-w-4xl mx-auto flex gap-4">
            <input type="text" value={input} onChange={(e) => setInput(e.target.value)} placeholder="介入讨论... (按回车键发送)" className="flex-1 px-5 py-3.5 bg-[#f9f4e9] border border-[#d8cbb7] rounded-lg focus:ring-2 focus:ring-[#207362]/20 focus:border-[#207362] focus:bg-[#fffdf7] outline-none transition-all shadow-sm" />
            <button type="submit" disabled={!input.trim()} className="bg-[#207362] hover:bg-[#185f51] disabled:opacity-50 disabled:cursor-not-allowed text-white px-6 py-3.5 rounded-lg font-bold flex items-center justify-center transition-colors shadow-sm"><Send size={20} /></button>
          </form>
        </div>
      )}
    </div>
  );
}
