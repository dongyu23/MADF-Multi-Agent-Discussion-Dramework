import { useState, useEffect, useRef } from "react";
import { Link, useParams } from "react-router";
import { ArrowLeft, Users, Send, User, Mic, Brain } from "lucide-react";
import { motion, AnimatePresence } from "motion/react";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { getDiscussion, getMessages, buildStreamUrl, intervene } from "../api/discussions";
import { toast } from "sonner";

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
    agent: m.agent_name || "系统",
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
  const endRef = useRef<HTMLDivElement>(null);
  const esRef = useRef<EventSource | null>(null);
  const currentSpeakRef = useRef<{ agent: string; text: string }>({ agent: "", text: "" });

  const { data: discussion } = useQuery({
    queryKey: ["discussion", id],
    queryFn: () => getDiscussion(id!),
    enabled: !!id,
    staleTime: 5_000,
  });

  // Load historical messages (only for completed discussions)
  useEffect(() => {
    if (!id || discussion?.status !== "completed") return;
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

    es.addEventListener("host_intro", (e) => {
      const d = JSON.parse(e.data);
      setMessages((prev) => [...prev, { id: Date.now(), type: "host", text: d.content, agent: "主持人" }]);
    });

    es.addEventListener("agent_think", (e) => {
      const d = JSON.parse(e.data);
      setMessages((prev) => [...prev, { id: Date.now(), type: "agent", mode: "thought", text: d.reasoning || d.content || "", agent: d.agent_name, confidence: d.confidence }]);
    });

    es.addEventListener("agent_speak_start", (e) => {
      const d = JSON.parse(e.data);
      setSpeaking(d.agent_name);
      currentSpeakRef.current = { agent: d.agent_name, text: "" };
    });

    es.addEventListener("agent_speak_chunk", (e) => {
      const d = JSON.parse(e.data);
      currentSpeakRef.current.text += d.content || "";
      setMessages((prev) => {
        const last = prev[prev.length - 1];
        if (last && last.type === "agent" && last.mode === "spoken" && last.agent === currentSpeakRef.current.agent) {
          return [...prev.slice(0, -1), { ...last, text: currentSpeakRef.current.text }];
        }
        return [...prev, { id: Date.now(), type: "agent", mode: "spoken", text: currentSpeakRef.current.text, agent: currentSpeakRef.current.agent }];
      });
    });

    es.addEventListener("agent_speak_end", () => { setSpeaking(null); currentSpeakRef.current = { agent: "", text: "" }; });
    es.addEventListener("host_summary", (e) => {
      const d = JSON.parse(e.data);
      setMessages((prev) => [...prev, { id: Date.now(), type: "host", text: d.content, agent: "主持人总结" }]);
    });
    es.addEventListener("discussion_end", () => {
      setConnected(false);
      queryClient.invalidateQueries({ queryKey: ["discussion", id] });
      queryClient.invalidateQueries({ queryKey: ["discussions"] });
    });
    es.addEventListener("user_intervened", (e) => {
      const d = JSON.parse(e.data);
      setMessages((prev) => [...prev, { id: Date.now(), type: "user", text: d.content, agent: d.username || "用户" }]);
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
      <div className="h-16 border-b border-slate-200 bg-white flex items-center justify-between px-6 flex-shrink-0 shadow-sm z-10">
        <div className="flex items-center gap-4">
          <Link to="/discussions" className="text-slate-400 hover:text-slate-900 transition-colors"><ArrowLeft size={20} /></Link>
          <div>
            <h1 className="font-bold text-slate-900 text-lg">{discussion?.topic || "加载中..."}</h1>
            <div className="flex items-center gap-3 text-xs font-medium text-slate-500">
              <span className="flex items-center gap-1">
                <span className={`w-2 h-2 rounded-full ${discussion?.status === "running" ? "bg-emerald-500 animate-pulse" : "bg-slate-400"}`} />
                {discussion?.status === "running" ? "进行中" : discussion?.status === "completed" ? "已结束" : discussion?.status || "-"}
              </span>
              <span>•</span>
              <span className="flex items-center gap-1"><Users size={12} /> {discussion?.agents?.length || 0} 个智能体</span>
              {connected && (<><span>•</span><span className="text-emerald-600">实时连接中</span></>)}
            </div>
          </div>
        </div>
      </div>

      <div className="flex-1 overflow-y-auto p-6 scroll-smooth">
        <div className="max-w-4xl mx-auto space-y-6">
          {messages.length === 0 && (
            <div className="text-center py-16 text-slate-400"><p className="text-lg mb-2">等待讨论开始...</p>{discussion?.status === "completed" && <p>讨论已结束</p>}</div>
          )}
          <AnimatePresence>
            {messages.map((msg, index) => {
              const prevMsg = index > 0 ? messages[index - 1] : null;
              const isTransition = prevMsg && prevMsg.agent === msg.agent && prevMsg.mode === "thought" && msg.mode === "spoken";
              return (
                <React.Fragment key={msg.id}>
                  {isTransition && (
                    <motion.div initial={{ opacity: 0, y: 5 }} animate={{ opacity: 1, y: 0 }} className="flex justify-center my-4">
                      <span className="text-xs font-medium text-slate-400 bg-slate-100 px-4 py-1.5 rounded-full flex items-center gap-2"><span className="w-1.5 h-1.5 rounded-full bg-slate-300 animate-pulse" />{msg.agent} 即将进行发言</span>
                    </motion.div>
                  )}
                  <motion.div initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} className={`flex gap-4 ${msg.type === "user" ? "flex-row-reverse" : ""}`}>
                    <div className={`w-10 h-10 rounded-full flex items-center justify-center flex-shrink-0 font-bold text-sm shadow-sm ${msg.type === "host" ? "bg-amber-100 text-amber-700" : msg.type === "user" ? "bg-indigo-600 text-white" : "bg-slate-800 text-white"}`}>
                      {msg.type === "host" ? <Mic size={18} /> : msg.type === "user" ? <User size={18} /> : msg.agent.charAt(0)}
                    </div>
                    <div className={`max-w-[80%] ${msg.type === "user" ? "items-end flex flex-col" : "items-start flex flex-col"}`}>
                      <div className={`flex items-center gap-2 mb-1 px-1 ${msg.type === "user" ? "flex-row-reverse" : ""}`}>
                        <span className="font-semibold text-sm text-slate-700">{msg.agent}</span>
                        {msg.type === "agent" && msg.mode === "thought" && (<span className="text-[10px] font-medium text-slate-500 bg-slate-100 px-1.5 py-0.5 rounded flex items-center gap-1"><Brain size={10} /> 内部思考</span>)}
                        {msg.type === "agent" && msg.mode === "thought" && msg.confidence != null && (<span className="text-[10px] font-mono text-slate-400 bg-slate-200/50 px-1.5 py-0.5 rounded">置信度: {msg.confidence}</span>)}
                      </div>
                      <div className={`p-4 shadow-sm text-[15px] leading-relaxed ${msg.type === "user" ? "bg-indigo-600 text-white rounded-2xl rounded-tr-none" : msg.type === "host" ? "bg-amber-50 text-amber-900 border border-amber-200/50 rounded-2xl rounded-tl-none" : msg.mode === "thought" ? "bg-slate-50 text-slate-500 border-2 border-dashed border-slate-200 rounded-3xl italic" : "bg-white text-slate-800 border border-slate-200 rounded-2xl rounded-tl-none"}`}>{msg.text}</div>
                    </div>
                  </motion.div>
                </React.Fragment>
              );
            })}
          </AnimatePresence>
          {speaking && (
            <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} className="flex gap-4">
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
        <div className="bg-white border-t border-slate-200 p-4">
          <form onSubmit={handleSend} className="max-w-4xl mx-auto flex gap-4">
            <input type="text" value={input} onChange={(e) => setInput(e.target.value)} placeholder="介入讨论... (按回车键发送)" className="flex-1 px-5 py-3.5 bg-slate-50 border border-slate-200 rounded-xl focus:ring-2 focus:ring-indigo-600 focus:bg-white outline-none transition-all shadow-sm" />
            <button type="submit" disabled={!input.trim()} className="bg-indigo-600 hover:bg-indigo-700 disabled:opacity-50 disabled:cursor-not-allowed text-white px-6 py-3.5 rounded-xl font-bold flex items-center justify-center transition-colors shadow-sm"><Send size={20} /></button>
          </form>
        </div>
      )}
    </div>
  );
}
