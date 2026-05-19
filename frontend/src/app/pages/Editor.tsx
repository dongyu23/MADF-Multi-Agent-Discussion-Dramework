import { useState, useEffect, useRef, lazy, Suspense } from "react";
import { Link, useParams } from "react-router";
const MonacoEditor = lazy(() => import("@monaco-editor/react"));
import { ArrowLeft, Save, FileText, Folder, Terminal, Loader2, CheckCircle2, Zap, Search, Box, Copy, Cpu, PanelRightClose, PanelRightOpen } from "lucide-react";
import { motion, AnimatePresence } from "motion/react";
import { toast } from "sonner";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { getCharacter, getCharacterFiles, copyCharacter } from "../api/characters";

interface LogEvent {
  level: "idle" | "main" | "sub" | "tool" | "done" | "error" | "file";
  message: string;
  extra?: any;
  count?: number;
}

interface FileNode {
  name: string;
  type: "file" | "folder";
  path: string;
  children?: FileNode[];
}

function buildFileTree(rawFiles: string[]): FileNode[] {
  const root: FileNode[] = [];
  rawFiles.forEach((fpath) => {
    const parts = fpath.split("/");
    let current = root;
    parts.forEach((part, idx) => {
      const isLast = idx === parts.length - 1;
      let existing = current.find((n) => n.name === part);
      if (!existing) {
        existing = { name: part, type: isLast ? "file" : "folder", path: fpath };
        if (!isLast) existing.children = [];
        current.push(existing);
      }
      if (!isLast) current = existing.children!;
    });
  });
  return root;
}

const LOGS_PREFIX = "editor_logs_";
const COLLAPSED_PREFIX = "editor_collapsed_";

function loadLogs(charId: string): LogEvent[] {
  try {
    const raw = sessionStorage.getItem(LOGS_PREFIX + charId);
    return raw ? JSON.parse(raw) : [];
  } catch {
    return [];
  }
}

function saveLogs(charId: string, logs: LogEvent[]) {
  try {
    sessionStorage.setItem(LOGS_PREFIX + charId, JSON.stringify(logs));
  } catch { /* ignore */ }
}

function loadCollapsed(charId: string): boolean {
  try {
    const raw = sessionStorage.getItem(COLLAPSED_PREFIX + charId);
    return raw === "true";
  } catch {
    return false;
  }
}

function saveCollapsed(charId: string, v: boolean) {
  try {
    sessionStorage.setItem(COLLAPSED_PREFIX + charId, String(v));
  } catch { /* ignore */ }
}

export function Editor() {
  const { id } = useParams();
  const queryClient = useQueryClient();
  const isViewMode = window.location.pathname.includes("/view");

  const [activeFile, setActiveFile] = useState<string>("SKILL.md");
  const [logs, setLogs] = useState<LogEvent[]>(() => (id ? loadLogs(id) : []));
  const [panelCollapsed, setPanelCollapsed] = useState<boolean>(() => id ? loadCollapsed(id) : false);
  const scrollRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    setActiveFile("SKILL.md");
    setLogs(id ? loadLogs(id) : []);
    setPanelCollapsed(id ? loadCollapsed(id) : false);
  }, [id]);

  useEffect(() => {
    if (id) saveCollapsed(id, panelCollapsed);
  }, [panelCollapsed, id]);

  const { data: character, isLoading } = useQuery({
    queryKey: ["character", id],
    queryFn: () => getCharacter(id!),
    enabled: !!id,
    staleTime: 5_000,
    refetchInterval: 5000,
  });

  const isGenerating = character?.status === "generating";

  const { data: fileList = [] } = useQuery({
    queryKey: ["characterFiles", id],
    queryFn: () => getCharacterFiles(id!).then(d => (Array.isArray(d) ? d : d?.files || [])),
    enabled: !!id,
    staleTime: 3_000,
    refetchInterval: isGenerating ? 3000 : false,
  });

  const { data: code = "" } = useQuery({
    queryKey: ["characterFile", id, activeFile],
    queryFn: () => getCharacterFiles(id!, activeFile).then(d => (typeof d === "string" ? d : d.content || "")),
    enabled: !!id && !!activeFile,
    staleTime: 30_000,
  });

  const files = buildFileTree(fileList);

  // Persist logs to sessionStorage on change
  useEffect(() => {
    if (id) saveLogs(id, logs);
  }, [logs, id]);

  useEffect(() => {
    if (!id || isViewMode || !isGenerating) return;
    const es = new EventSource(`/api/v1/characters/${id}/generation-progress`);
    es.onmessage = (event) => {
      try {
        const payload = JSON.parse(event.data);
        setLogs((prev) => {
          const last = prev[prev.length - 1];
          if (last && last.level === payload.level && last.message === payload.message) {
            const merged = { ...last, count: (last.count || 1) + 1 };
            return [...prev.slice(0, -1), merged];
          }
          return [...prev, payload];
        });
        if (payload.level === "file") {
          queryClient.invalidateQueries({ queryKey: ["characterFiles", id] });
        }
        if (payload.level === "done" || payload.level === "error") {
          es.close();
          queryClient.invalidateQueries({ queryKey: ["character", id] });
          queryClient.invalidateQueries({ queryKey: ["characterFiles", id] });
          queryClient.invalidateQueries({ queryKey: ["characters"] });
          if (payload.level === "done") toast.success("生成完成！");
          else toast.error(payload.message || "生成失败");
        }
      } catch {}
    };
    es.onerror = () => {
      es.close();
      queryClient.invalidateQueries({ queryKey: ["character", id] });
      queryClient.invalidateQueries({ queryKey: ["characterFiles", id] });
    };
    return () => es.close();
  }, [id, isViewMode, isGenerating]);

  useEffect(() => {
    if (scrollRef.current) scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
  }, [logs, panelCollapsed]);

  const copyMutation = useMutation({
    mutationFn: () => copyCharacter(id!),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["characters"] });
      toast.success("复制成功！", { description: `角色已保存到"我的角色"列表中` });
    },
    onError: (err: any) => toast.error(err.response?.data?.message || "复制失败"),
  });

  const renderLogIcon = (level?: string) => {
    switch (level) {
      case "main": return <Zap size={14} className="text-amber-500 mt-0.5 flex-shrink-0" />;
      case "sub": return <Box size={14} className="text-indigo-400 mt-0.5 flex-shrink-0" />;
      case "tool": return <Search size={12} className="text-slate-500 mt-0.5 flex-shrink-0" />;
      case "done": return <CheckCircle2 size={16} className="text-emerald-500 mt-0.5 flex-shrink-0" />;
      case "file": return <FileText size={14} className="text-cyan-400 mt-0.5 flex-shrink-0" />;
      default: return <Terminal size={14} className="text-slate-500 mt-0.5 flex-shrink-0" />;
    }
  };

  const renderFileTree = (nodes: FileNode[], depth = 0) =>
    nodes.map((node) => (
      <div key={node.path}>
        <div className={`flex items-center gap-2 px-2 py-1.5 rounded-md cursor-pointer ${activeFile === node.path ? "bg-indigo-100 text-indigo-700 font-medium" : "text-slate-600 hover:bg-slate-200"}`}
          style={{ paddingLeft: 8 + depth * 16 }}
          onClick={() => node.type === "file" && setActiveFile(node.path)}>
          {node.type === "folder" ? <Folder size={16} className="text-slate-400" /> : <FileText size={16} className={activeFile === node.path ? "text-indigo-500" : "text-slate-400"} />}
          <span className="text-sm truncate">{node.name}</span>
        </div>
        {node.children && renderFileTree(node.children, depth + 1)}
      </div>
    ));

  if (isLoading) {
    return (
      <div className="h-screen w-screen flex items-center justify-center bg-slate-50">
        <Loader2 className="animate-spin text-indigo-600" size={32} />
      </div>
    );
  }

  // Status derived from character state (not stale logs from another character)
  const generationDone = character?.status === "ready";
  const generationFailed = character?.status === "error";
  const hasLogs = logs.length > 0;
  const showPanelToggle = !isViewMode && (hasLogs || isGenerating);

  return (
    <div className="h-full w-full flex flex-col bg-slate-50">
      {/* Top Bar */}
      <div className="h-14 border-b border-slate-200 bg-white flex items-center justify-between px-4 flex-shrink-0">
        <div className="flex items-center gap-4">
          <Link to={isViewMode ? "/gallery" : "/characters"} className="text-slate-400 hover:text-slate-900 transition-colors">
            <ArrowLeft size={20} />
          </Link>
          <div className="flex items-center gap-2">
            <span className="font-semibold text-slate-900">{character?.name || "..."}</span>
            {isGenerating && (
              <span className="text-xs font-medium text-amber-600 bg-amber-50 px-2 py-0.5 rounded-full flex items-center gap-1">
                <span className="w-1.5 h-1.5 rounded-full bg-amber-500 animate-pulse" /> 生成中
              </span>
            )}
            <span className="text-slate-400">/</span>
            <span className="text-sm text-slate-500 font-mono">{activeFile}</span>
          </div>
        </div>
        <div className="flex items-center gap-3">
          {showPanelToggle && (
            <button
              onClick={() => setPanelCollapsed(prev => !prev)}
              className="flex items-center gap-1.5 text-xs font-medium text-slate-500 hover:text-indigo-600 bg-slate-50 hover:bg-indigo-50 px-3 py-1.5 rounded-lg transition-colors"
              title={panelCollapsed ? "展开生成日志" : "折叠生成日志"}
            >
              {panelCollapsed ? <PanelRightOpen size={14} /> : <PanelRightClose size={14} />}
              {panelCollapsed ? "展开日志" : "折叠日志"}
              {hasLogs && <span className="text-slate-400">({logs.length})</span>}
            </button>
          )}
          {isViewMode ? (
            <button onClick={() => copyMutation.mutate()} disabled={copyMutation.isPending}
              className="flex items-center gap-2 bg-indigo-600 hover:bg-indigo-700 text-white px-4 py-2 rounded-lg text-sm font-medium transition-colors shadow-sm">
              <Copy size={16} /> 复制到我的角色
            </button>
          ) : (
            <button className="flex items-center gap-2 bg-indigo-600 hover:bg-indigo-700 text-white px-4 py-2 rounded-lg text-sm font-medium transition-colors shadow-sm">
              <Save size={16} /> 保存更改
            </button>
          )}
        </div>
      </div>

      {/* Three-Panel Layout */}
      <div className="flex-1 flex overflow-hidden">
        {/* Left: File Tree */}
        <div className="w-56 bg-slate-50 border-r border-slate-200 overflow-y-auto flex-shrink-0">
          <div className="p-4 text-xs font-semibold text-slate-500 uppercase tracking-wider">资源管理器</div>
          <div className="px-2 space-y-1">
            {files.length === 0 && isGenerating ? (
              <div className="p-4 text-center text-slate-400 text-sm">
                <Loader2 className="animate-spin mx-auto mb-2" size={18} />
                等待文件生成…
              </div>
            ) : (
              renderFileTree(files)
            )}
          </div>
        </div>

        {/* Center: Editor + Right: Progress Panel */}
        <div className="flex-1 flex bg-white relative min-w-0">
          <div className="flex-1 relative min-w-0">
            {files.length === 0 && isGenerating ? (
              <div className="flex items-center justify-center h-full text-slate-400">
                <div className="text-center">
                  <Cpu className="mx-auto mb-3 text-indigo-400 animate-pulse" size={32} />
                  <p className="text-sm">AI 智能体正在生成角色技能…</p>
                  <p className="text-xs mt-1 text-slate-400">右侧面板查看实时进度</p>
                </div>
              </div>
            ) : (
              <Suspense fallback={<div className="flex items-center justify-center h-full"><Loader2 className="animate-spin" size={24} /></div>}>
                <MonacoEditor height="100%" defaultLanguage="markdown" value={code}
                  onChange={() => {}} options={{ readOnly: true, folding: true, minimap: { enabled: false }, fontSize: 14, fontFamily: "'JetBrains Mono', 'Fira Code', monospace", wordWrap: "on", padding: { top: 24, bottom: 24 }, lineHeight: 1.6 }} />
              </Suspense>
            )}
          </div>

          {/* Right: Progress Panel */}
          {showPanelToggle && (
            <div className="bg-slate-950 border-l border-slate-800 flex flex-col flex-shrink-0 z-10 text-slate-300" style={{ width: panelCollapsed ? 44 : 360 }}>
              {/* Collapsed strip */}

              {/* Expanded content */}
              {!panelCollapsed && (
                <>
                  <div className="absolute top-0 right-0 w-64 h-64 bg-amber-500/5 rounded-full blur-3xl pointer-events-none" />
                  <div className="absolute bottom-0 left-0 w-64 h-64 bg-rose-500/5 rounded-full blur-3xl pointer-events-none" />
                  <div className="h-14 border-b border-slate-800/60 flex items-center justify-between px-4 bg-slate-950/80 backdrop-blur-sm z-10 relative flex-shrink-0">
                    <div className="flex items-center gap-2.5 font-medium tracking-wide">
                      <Terminal size={16} className="text-amber-500/90" />
                      <span className="bg-gradient-to-r from-slate-200 to-slate-400 bg-clip-text text-transparent">生成进度日志</span>
                    </div>
                    <div className="flex items-center gap-2">
                      <span className={`text-xs font-mono px-2.5 py-1 rounded-full border flex items-center gap-1 ${
                        isGenerating ? "text-amber-500/80 bg-amber-500/10 border-amber-500/20" :
                        generationDone ? "text-emerald-400 bg-emerald-400/10 border-emerald-400/20" :
                        generationFailed ? "text-red-400 bg-red-400/10 border-red-400/20" :
                        "text-slate-400 bg-slate-400/10 border-slate-400/20"
                      }`}>
                        {isGenerating && <Loader2 size={12} className="animate-spin" />}
                        {isGenerating ? "运行中" : generationDone ? "已完成" : generationFailed ? "失败" : "就绪"}
                      </span>
                    </div>
                  </div>
                  <div className="flex-1 overflow-y-auto p-5 space-y-4 font-mono text-xs z-10 relative" ref={scrollRef}>
                    <AnimatePresence>
                      {logs.map((log, idx) => (
                        <motion.div key={`${idx}-${log.level}-${log.message.slice(0, 20)}`} initial={{ opacity: 0, y: 10, filter: "blur(4px)" }} animate={{ opacity: 1, y: 0, filter: "blur(0px)" }} transition={{ duration: 0.3 }}
                          className={`flex items-start gap-2.5 ${
                            log.level === "main" ? "text-amber-200/90 font-semibold text-[13px] mt-6 first:mt-0"
                            : log.level === "sub" ? "text-indigo-200/80 ml-2 border-l border-indigo-500/20 pl-3 py-0.5"
                            : log.level === "tool" ? "text-slate-500 ml-6"
                            : log.level === "file" ? "text-cyan-400/80 ml-2 border-l border-cyan-500/30 pl-3 py-0.5"
                            : log.level === "done" ? "text-emerald-400 font-semibold mt-6 bg-emerald-950/30 p-3 rounded-lg border border-emerald-900/50"
                            : log.level === "error" ? "text-red-400 font-semibold mt-4 bg-red-950/20 p-3 rounded-lg border border-red-900/30" : ""
                          }`}>
                          {renderLogIcon(log.level)}
                          <div className="flex-1 flex flex-col gap-1.5 leading-relaxed">
                            <span>
                              {log.message}
                              {log.count && log.count > 1 && (
                                <span className="ml-1.5 text-[10px] text-slate-500 bg-slate-800 px-1.5 py-0.5 rounded-full">×{log.count}</span>
                              )}
                            </span>
                            {log.extra && log.level === "sub" && (
                              <span className="text-[10px] text-slate-500/70">{log.extra.description?.slice(0, 60)}</span>
                            )}
                            {log.extra && log.level === "done" && (
                              <div className="mt-2 text-emerald-500/70 text-xs">
                                └─ 派发了 {log.extra.subagents_spawned} 个子智能体，生成了 {log.extra.file_count} 个文件。
                              </div>
                            )}
                          </div>
                        </motion.div>
                      ))}
                    </AnimatePresence>
                    {generationDone && (
                      <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} transition={{ delay: 0.3 }}
                        className="pt-4 border-t border-slate-800/50 flex justify-center">
                        <span className="text-slate-500 text-xs">文件树和编辑器已就绪</span>
                      </motion.div>
                    )}
                  </div>
                </>
              )}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
