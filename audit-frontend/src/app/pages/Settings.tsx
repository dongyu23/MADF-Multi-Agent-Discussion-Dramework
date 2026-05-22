import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { motion } from "motion/react";
import { Loader2, Save, RotateCw, AlertTriangle, Server, Database } from "lucide-react";
import { toast } from "sonner";
import { getSettings, updateSettings, restartService, updateRetention } from "../api/admin";

export function Settings() {
  const qc = useQueryClient();
  const [showRestartConfirm, setShowRestartConfirm] = useState(false);

  const { data: settings, isLoading } = useQuery({
    queryKey: ["admin-settings"],
    queryFn: getSettings,
  });

  const saveMutation = useMutation({
    mutationFn: (data: Record<string, any>) => updateSettings(data),
    onSuccess: () => { qc.invalidateQueries({ queryKey: ["admin-settings"] }); toast.success("设置已保存"); },
    onError: (err: any) => toast.error(err?.response?.data?.message || "保存失败"),
  });

  const retentionMutation = useMutation({
    mutationFn: (data: Record<string, any>) => updateRetention(data),
    onSuccess: () => { qc.invalidateQueries({ queryKey: ["admin-settings"] }); toast.success("保留策略已更新"); },
    onError: (err: any) => toast.error(err?.response?.data?.message || "保存失败"),
  });

  const restartMutation = useMutation({
    mutationFn: restartService,
    onSuccess: () => { setShowRestartConfirm(false); toast.success("重启指令已发送"); },
    onError: (err: any) => toast.error(err?.response?.data?.message || "重启失败"),
  });

  return (
    <motion.div initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }} className="p-8 max-w-3xl mx-auto space-y-6">
      <h1 className="text-2xl font-bold text-slate-900">系统设置</h1>

      {isLoading ? (
        <div className="flex items-center justify-center py-20"><Loader2 className="animate-spin text-indigo-400" size={28} /></div>
      ) : (
        <>
          <SystemInfoSection settings={settings} />
          <GeneralSettingsSection
            settings={settings}
            onSave={(data) => saveMutation.mutate(data)}
            saving={saveMutation.isPending}
          />
          <RetentionSection
            settings={settings}
            onSave={(data) => retentionMutation.mutate(data)}
            saving={retentionMutation.isPending}
          />
          <RestartSection
            onRestart={() => setShowRestartConfirm(true)}
            dockerAvailable={settings?.docker_available ?? true}
          />
        </>
      )}

      {showRestartConfirm && (
        <div className="fixed inset-0 bg-black/20 flex items-center justify-center z-50">
          <motion.div
            initial={{ opacity: 0, scale: 0.95 }}
            animate={{ opacity: 1, scale: 1 }}
            className="bg-white border border-slate-200 rounded-2xl shadow-xl p-6 w-full max-w-sm space-y-4"
          >
            <div className="flex items-center gap-3">
              <AlertTriangle size={20} className="text-amber-500" />
              <h2 className="text-lg font-semibold text-slate-900">确认重启服务</h2>
            </div>
            <p className="text-sm text-slate-500">重启服务将短暂中断服务，确定要继续吗？</p>
            <div className="flex justify-end gap-3">
              <button onClick={() => setShowRestartConfirm(false)} className="px-4 py-2 text-sm font-medium text-slate-600 hover:bg-slate-50 rounded-xl transition-colors">取消</button>
              <button
                onClick={() => restartMutation.mutate()}
                disabled={restartMutation.isPending}
                className="px-4 py-2 bg-red-600 hover:bg-red-700 text-white rounded-xl text-sm font-semibold transition-colors disabled:opacity-50"
              >
                {restartMutation.isPending ? "重启中..." : "确认重启"}
              </button>
            </div>
          </motion.div>
        </div>
      )}
    </motion.div>
  );
}

function SystemInfoSection({ settings }: { settings: any }) {
  return (
    <div className="bg-white border border-slate-200 rounded-2xl shadow-sm p-6 space-y-4">
      <div className="flex items-center gap-2">
        <Server size={18} className="text-slate-400" />
        <h2 className="text-lg font-semibold text-slate-900">系统信息</h2>
      </div>
      <div className="grid grid-cols-2 gap-3 text-sm">
        <InfoRow label="应用名称" value={settings?.app_name} />
        <InfoRow label="LLM 模型" value={settings?.llm_model} />
        <InfoRow label="LLM API" value={settings?.llm_api_base} />
        <InfoRow label="数据库" value={settings?.db_host ? `${settings.db_host}:${settings.db_port}/${settings.db_name}` : "-"} />
        <InfoRow label="Redis" value={settings?.redis_host ? `${settings.redis_host}:${settings.redis_port}` : "-"} />
        <InfoRow label="调试模式" value={settings?.debug ? "开启" : "关闭"} />
      </div>
    </div>
  );
}

function GeneralSettingsSection({
  settings,
  onSave,
  saving,
}: {
  settings: any;
  onSave: (data: Record<string, any>) => void;
  saving: boolean;
}) {
  const [jwtExpire, setJwtExpire] = useState(String(settings?.jwt_expire_minutes ?? 240));
  const [maxDuration, setMaxDuration] = useState(String(settings?.max_discussion_duration ?? 3600));
  const [maxAgents, setMaxAgents] = useState(String(settings?.max_agents_per_discussion ?? 8));
  const [regOpen, setRegOpen] = useState(settings?.registration_open ?? true);

  return (
    <div className="bg-white border border-slate-200 rounded-2xl shadow-sm p-6 space-y-4">
      <h2 className="text-lg font-semibold text-slate-900">通用设置</h2>
      <div className="grid grid-cols-2 gap-4">
        <div>
          <label className="block text-sm font-medium text-slate-700 mb-1.5">JWT 过期时间 (分钟)</label>
          <input
            type="number" value={jwtExpire} onChange={(e) => setJwtExpire(e.target.value)}
            className="w-full border border-slate-200 rounded-xl px-4 py-3 focus:ring-2 focus:ring-indigo-500 outline-none text-sm"
          />
        </div>
        <div>
          <label className="block text-sm font-medium text-slate-700 mb-1.5">最大讨论时长 (秒)</label>
          <input
            type="number" value={maxDuration} onChange={(e) => setMaxDuration(e.target.value)}
            className="w-full border border-slate-200 rounded-xl px-4 py-3 focus:ring-2 focus:ring-indigo-500 outline-none text-sm"
          />
        </div>
        <div>
          <label className="block text-sm font-medium text-slate-700 mb-1.5">最大参与 Agent 数</label>
          <input
            type="number" value={maxAgents} onChange={(e) => setMaxAgents(e.target.value)}
            className="w-full border border-slate-200 rounded-xl px-4 py-3 focus:ring-2 focus:ring-indigo-500 outline-none text-sm"
          />
        </div>
        <div>
          <label className="block text-sm font-medium text-slate-700 mb-1.5">开放注册</label>
          <div className="mt-3">
            <label className="inline-flex items-center gap-2 cursor-pointer">
              <input
                type="checkbox" checked={regOpen} onChange={(e) => setRegOpen(e.target.checked)}
                className="w-4 h-4 rounded border-slate-300 text-indigo-600 focus:ring-indigo-500"
              />
              <span className="text-sm text-slate-600">{regOpen ? "允许新用户注册" : "禁止新用户注册"}</span>
            </label>
          </div>
        </div>
      </div>
      <div className="flex justify-end pt-2">
        <button
          onClick={() => onSave({
            jwt_expire_minutes: parseInt(jwtExpire),
            max_discussion_duration: parseInt(maxDuration),
            max_agents_per_discussion: parseInt(maxAgents),
            registration_open: regOpen,
          })}
          disabled={saving}
          className="flex items-center gap-2 bg-indigo-600 hover:bg-indigo-700 text-white rounded-xl px-4 py-2 text-sm font-semibold transition-colors disabled:opacity-50"
        >
          <Save size={16} /> {saving ? "保存中..." : "保存设置"}
        </button>
      </div>
    </div>
  );
}

function RetentionSection({
  settings,
  onSave,
  saving,
}: {
  settings: any;
  onSave: (data: Record<string, any>) => void;
  saving: boolean;
}) {
  const [retentionDays, setRetentionDays] = useState(String(settings?.retention_days ?? 90));
  const [dryRun, setDryRun] = useState(false);
  const policies = settings?.retention_policies || [];

  return (
    <div className="bg-white border border-slate-200 rounded-2xl shadow-sm p-6 space-y-4">
      <div className="flex items-center gap-2">
        <Database size={18} className="text-slate-400" />
        <h2 className="text-lg font-semibold text-slate-900">数据保留策略</h2>
      </div>

      {policies.length > 0 && (
        <div className="space-y-2">
          <p className="text-xs text-slate-400 uppercase font-medium">当前策略</p>
          <div className="grid grid-cols-4 gap-3 text-xs font-medium text-slate-500 uppercase px-3">
            <span>级别</span>
            <span>热存储 (天)</span>
            <span>温存储 (天)</span>
            <span>状态</span>
          </div>
          {policies.map((p: any) => (
            <div key={p.id || p.level} className="grid grid-cols-4 gap-3 items-center py-2 px-3 bg-slate-50 rounded-xl text-sm">
              <span className={`font-medium ${p.level === "P0" ? "text-red-600" : p.level === "P1" ? "text-orange-600" : "text-slate-600"}`}>{p.level}</span>
              <span className="text-slate-700">{p.hot_days}</span>
              <span className="text-slate-700">{p.warm_days}</span>
              <span className={p.is_active ? "text-green-600" : "text-slate-400"}>{p.is_active ? "启用" : "停用"}</span>
            </div>
          ))}
        </div>
      )}

      <div className="border-t border-slate-100 pt-4 space-y-4">
        <p className="text-xs text-slate-400 uppercase font-medium">更新保留策略</p>
        <div className="flex items-end gap-4">
          <div className="flex-1">
            <label className="block text-sm font-medium text-slate-700 mb-1.5">保留天数</label>
            <p className="text-xs text-slate-400 mb-2">设置后将自动计算 P0/P1/P2 各级别的热/温存储天数</p>
            <input
              type="number" value={retentionDays} onChange={(e) => setRetentionDays(e.target.value)}
              className="w-full border border-slate-200 rounded-xl px-4 py-3 focus:ring-2 focus:ring-indigo-500 outline-none text-sm"
            />
          </div>
          <button
            onClick={() => onSave({ retention_days: parseInt(retentionDays), dry_run: dryRun })}
            disabled={saving}
            className="flex items-center gap-2 bg-indigo-600 hover:bg-indigo-700 text-white rounded-xl px-4 py-3 text-sm font-semibold transition-colors disabled:opacity-50 shrink-0"
          >
            <Save size={16} /> {saving ? "保存中..." : "应用"}
          </button>
        </div>
        <label className="inline-flex items-center gap-2 cursor-pointer">
          <input
            type="checkbox" checked={dryRun} onChange={(e) => setDryRun(e.target.checked)}
            className="w-4 h-4 rounded border-slate-300 text-indigo-600 focus:ring-indigo-500"
          />
          <span className="text-sm text-slate-500">仅模拟（dry run），不实际删除数据</span>
        </label>
      </div>
    </div>
  );
}

function RestartSection({ onRestart, dockerAvailable }: { onRestart: () => void; dockerAvailable: boolean }) {
  return (
    <div className="bg-white border border-slate-200 rounded-2xl shadow-sm p-6">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-lg font-semibold text-slate-900">重启服务</h2>
          <p className="text-sm text-slate-400 mt-1">
            {dockerAvailable ? "通过 Docker 策略重启所有服务" : "Docker socket 不可用，需手动重启"}
          </p>
        </div>
        <button
          onClick={onRestart}
          className="flex items-center gap-2 px-4 py-2.5 text-sm font-medium text-red-600 hover:bg-red-50 rounded-xl transition-colors border border-red-200"
        >
          <RotateCw size={16} /> 重启服务
        </button>
      </div>
    </div>
  );
}

function InfoRow({ label, value }: { label: string; value: any }) {
  return (
    <div className="flex justify-between items-center py-2 px-3 bg-slate-50 rounded-xl">
      <span className="text-slate-500">{label}</span>
      <span className="font-medium text-slate-800">{value ?? "-"}</span>
    </div>
  );
}
