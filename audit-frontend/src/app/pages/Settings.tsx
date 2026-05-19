import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { motion } from "motion/react";
import { Loader2, Save, RotateCw, AlertTriangle } from "lucide-react";
import { toast } from "sonner";
import { getSettings, updateSettings, restartService, updateRetention } from "../api/admin";

export function Settings() {
  const qc = useQueryClient();
  const [showRestartConfirm, setShowRestartConfirm] = useState(false);

  const { data: settings, isLoading } = useQuery({
    queryKey: ["admin-settings"],
    queryFn: getSettings,
  });

  const saveSettings = useMutation({
    mutationFn: (data: Record<string, any>) => updateSettings(data),
    onSuccess: () => { qc.invalidateQueries({ queryKey: ["admin-settings"] }); toast.success("设置已保存"); },
    onError: (err: any) => toast.error(err?.response?.data?.message || "保存失败"),
  });

  const saveRetention = useMutation({
    mutationFn: (data: Record<string, any>) => updateRetention(data),
    onSuccess: () => { qc.invalidateQueries({ queryKey: ["admin-settings"] }); toast.success("保留策略已保存"); },
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
          <PortConfigSection
            settings={settings}
            onSave={(data) => saveSettings.mutate(data)}
            saving={saveSettings.isPending}
            onRestart={() => setShowRestartConfirm(true)}
          />

          <AlertThresholdSection
            settings={settings}
            onSave={(data) => saveSettings.mutate(data)}
            saving={saveSettings.isPending}
          />

          <DataRetentionSection
            settings={settings}
            onSave={(data) => saveRetention.mutate(data)}
            saving={saveRetention.isPending}
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

function PortConfigSection({
  settings,
  onSave,
  saving,
  onRestart,
}: {
  settings: any;
  onSave: (data: Record<string, any>) => void;
  saving: boolean;
  onRestart: () => void;
}) {
  const [mainPort, setMainPort] = useState(String(settings?.main_port || "8000"));
  const [auditPort, setAuditPort] = useState(String(settings?.audit_port || "8001"));

  return (
    <div className="bg-white border border-slate-200 rounded-2xl shadow-sm p-6 space-y-4">
      <h2 className="text-lg font-semibold text-slate-900">端口配置</h2>
      <div className="grid grid-cols-2 gap-4">
        <div>
          <label className="block text-sm font-medium text-slate-700 mb-1.5">主服务端口</label>
          <input
            type="number" value={mainPort} onChange={(e) => setMainPort(e.target.value)}
            className="w-full border border-slate-200 rounded-xl px-4 py-3 focus:ring-2 focus:ring-indigo-500 outline-none text-sm"
          />
        </div>
        <div>
          <label className="block text-sm font-medium text-slate-700 mb-1.5">管理后台端口</label>
          <input
            type="number" value={auditPort} onChange={(e) => setAuditPort(e.target.value)}
            className="w-full border border-slate-200 rounded-xl px-4 py-3 focus:ring-2 focus:ring-indigo-500 outline-none text-sm"
          />
        </div>
      </div>
      <div className="flex justify-between items-center pt-2">
        <button
          onClick={onRestart}
          className="flex items-center gap-2 px-4 py-2 text-sm font-medium text-slate-600 hover:bg-slate-100 rounded-xl transition-colors"
        >
          <RotateCw size={16} /> 重启服务
        </button>
        <button
          onClick={() => onSave({ main_port: parseInt(mainPort), audit_port: parseInt(auditPort) })}
          disabled={saving}
          className="flex items-center gap-2 bg-indigo-600 hover:bg-indigo-700 text-white rounded-xl px-4 py-2 text-sm font-semibold transition-colors disabled:opacity-50"
        >
          <Save size={16} /> {saving ? "保存中..." : "保存端口配置"}
        </button>
      </div>
    </div>
  );
}

function AlertThresholdSection({
  settings,
  onSave,
  saving,
}: {
  settings: any;
  onSave: (data: Record<string, any>) => void;
  saving: boolean;
}) {
  const [p0Threshold, setP0Threshold] = useState(String(settings?.p0_error_threshold || "5"));
  const [p1Threshold, setP1Threshold] = useState(String(settings?.p1_error_threshold || "20"));
  const [tokenThreshold, setTokenThreshold] = useState(String(settings?.token_usage_alert_threshold || "1000000"));

  return (
    <div className="bg-white border border-slate-200 rounded-2xl shadow-sm p-6 space-y-4">
      <h2 className="text-lg font-semibold text-slate-900">告警阈值</h2>
      <div className="grid grid-cols-3 gap-4">
        <div>
          <label className="block text-sm font-medium text-slate-700 mb-1.5">P0 错误阈值</label>
          <input
            type="number" value={p0Threshold} onChange={(e) => setP0Threshold(e.target.value)}
            className="w-full border border-slate-200 rounded-xl px-4 py-3 focus:ring-2 focus:ring-indigo-500 outline-none text-sm"
          />
          <p className="text-xs text-slate-400 mt-1">每小时 P0 错误上限</p>
        </div>
        <div>
          <label className="block text-sm font-medium text-slate-700 mb-1.5">P1 告警阈值</label>
          <input
            type="number" value={p1Threshold} onChange={(e) => setP1Threshold(e.target.value)}
            className="w-full border border-slate-200 rounded-xl px-4 py-3 focus:ring-2 focus:ring-indigo-500 outline-none text-sm"
          />
          <p className="text-xs text-slate-400 mt-1">每小时 P1 事件上限</p>
        </div>
        <div>
          <label className="block text-sm font-medium text-slate-700 mb-1.5">Token 用量告警</label>
          <input
            type="number" value={tokenThreshold} onChange={(e) => setTokenThreshold(e.target.value)}
            className="w-full border border-slate-200 rounded-xl px-4 py-3 focus:ring-2 focus:ring-indigo-500 outline-none text-sm"
          />
          <p className="text-xs text-slate-400 mt-1">每日 Token 用量上限</p>
        </div>
      </div>
      <div className="flex justify-end pt-2">
        <button
          onClick={() => onSave({ p0_error_threshold: parseInt(p0Threshold), p1_error_threshold: parseInt(p1Threshold), token_usage_alert_threshold: parseInt(tokenThreshold) })}
          disabled={saving}
          className="flex items-center gap-2 bg-indigo-600 hover:bg-indigo-700 text-white rounded-xl px-4 py-2 text-sm font-semibold transition-colors disabled:opacity-50"
        >
          <Save size={16} /> {saving ? "保存中..." : "保存告警设置"}
        </button>
      </div>
    </div>
  );
}

function DataRetentionSection({
  settings,
  onSave,
  saving,
}: {
  settings: any;
  onSave: (data: Record<string, any>) => void;
  saving: boolean;
}) {
  const [p0Hot, setP0Hot] = useState(String(settings?.retention?.P0?.hot_days || settings?.p0_hot_days || "90"));
  const [p0Warm, setP0Warm] = useState(String(settings?.retention?.P0?.warm_days || settings?.p0_warm_days || "365"));
  const [p1Hot, setP1Hot] = useState(String(settings?.retention?.P1?.hot_days || settings?.p1_hot_days || "60"));
  const [p1Warm, setP1Warm] = useState(String(settings?.retention?.P1?.warm_days || settings?.p1_warm_days || "180"));
  const [p2Hot, setP2Hot] = useState(String(settings?.retention?.P2?.hot_days || settings?.p2_hot_days || "30"));
  const [p2Warm, setP2Warm] = useState(String(settings?.retention?.P2?.warm_days || settings?.p2_warm_days || "90"));

  return (
    <div className="bg-white border border-slate-200 rounded-2xl shadow-sm p-6 space-y-4">
      <h2 className="text-lg font-semibold text-slate-900">数据保留策略</h2>
      <div className="space-y-4">
        <div className="grid grid-cols-3 gap-4 items-end">
          <div></div>
          <div>
            <label className="block text-sm font-medium text-slate-700 mb-1.5">热存储 (天)</label>
            <p className="text-xs text-slate-400">数据保存在主表，可快速查询</p>
          </div>
          <div>
            <label className="block text-sm font-medium text-slate-700 mb-1.5">温存储 (天)</label>
            <p className="text-xs text-slate-400">数据归档到历史表</p>
          </div>
        </div>
        {[
          { level: "P0", label: "P0 严重事件", hot: p0Hot, setHot: setP0Hot, warm: p0Warm, setWarm: setP0Warm },
          { level: "P1", label: "P1 重要事件", hot: p1Hot, setHot: setP1Hot, warm: p1Warm, setWarm: setP1Warm },
          { level: "P2", label: "P2 一般事件", hot: p2Hot, setHot: setP2Hot, warm: p2Warm, setWarm: setP2Warm },
        ].map((row) => (
          <div key={row.level} className="grid grid-cols-3 gap-4 items-center py-2 px-3 bg-slate-50 rounded-xl">
            <span className={`text-sm font-medium ${
              row.level === "P0" ? "text-red-600" : row.level === "P1" ? "text-orange-600" : "text-slate-600"
            }`}>{row.label}</span>
            <input
              type="number" value={row.hot} onChange={(e) => row.setHot(e.target.value)}
              className="border border-slate-200 rounded-lg px-3 py-2 focus:ring-2 focus:ring-indigo-500 outline-none text-sm bg-white"
            />
            <input
              type="number" value={row.warm} onChange={(e) => row.setWarm(e.target.value)}
              className="border border-slate-200 rounded-lg px-3 py-2 focus:ring-2 focus:ring-indigo-500 outline-none text-sm bg-white"
            />
          </div>
        ))}
      </div>
      <div className="flex justify-end pt-2">
        <button
          onClick={() =>
            onSave({
              retention: {
                P0: { hot_days: parseInt(p0Hot), warm_days: parseInt(p0Warm) },
                P1: { hot_days: parseInt(p1Hot), warm_days: parseInt(p1Warm) },
                P2: { hot_days: parseInt(p2Hot), warm_days: parseInt(p2Warm) },
              },
            })
          }
          disabled={saving}
          className="flex items-center gap-2 bg-indigo-600 hover:bg-indigo-700 text-white rounded-xl px-4 py-2 text-sm font-semibold transition-colors disabled:opacity-50"
        >
          <Save size={16} /> {saving ? "保存中..." : "保存保留策略"}
        </button>
      </div>
    </div>
  );
}
