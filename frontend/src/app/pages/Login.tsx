import { useState } from "react";
import { useNavigate, useSearchParams } from "react-router";
import { Sparkles, ArrowRight, Loader2 } from "lucide-react";
import { motion } from "motion/react";
import { register as apiRegister, login as apiLogin } from "../api/auth";
import { useAuth } from "../store/auth";
import { toast } from "sonner";

export function Login() {
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  const { setAuth } = useAuth();

  const [mode, setMode] = useState<"login" | "register">("login");
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [loading, setLoading] = useState(false);

  const redirect = searchParams.get("redirect") || "/";

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!username.trim() || !password.trim()) return;
    setLoading(true);
    try {
      const data =
        mode === "login"
          ? await apiLogin(username, password)
          : await apiRegister(username, password);
      setAuth(data.token.token, data.user);
      toast.success(mode === "login" ? "登录成功" : "注册成功");
      navigate(redirect, { replace: true });
    } catch (err: any) {
      const msg = err.response?.data?.message || "操作失败";
      toast.error(msg);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-[#07090E] text-slate-50 font-sans selection:bg-amber-500/30 overflow-x-hidden flex items-center justify-center">
      <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-[800px] h-[800px] bg-amber-600/10 blur-[120px] rounded-full pointer-events-none mix-blend-screen" />

      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        className="relative z-10 w-full max-w-md mx-4"
      >
        <div className="text-center mb-8">
          <div className="inline-flex items-center gap-2 px-4 py-1.5 rounded-full bg-white/5 border border-white/10 text-amber-200/80 text-sm font-medium mb-6">
            <Sparkles className="w-4 h-4" />
            MADF 圆桌论坛
          </div>
          <h1 className="text-3xl font-bold text-white mb-2">
            {mode === "login" ? "欢迎回来" : "创建账号"}
          </h1>
          <p className="text-slate-400 text-sm">
            {mode === "login" ? "登录以继续讨论" : "注册以开始使用"}
          </p>
        </div>

        <form
          onSubmit={handleSubmit}
          className="bg-white/[0.03] border border-white/10 rounded-2xl p-6 space-y-4 backdrop-blur-xl"
        >
          <div>
            <label className="block text-sm font-medium text-slate-300 mb-1.5">
              用户名
            </label>
            <input
              type="text"
              required
              value={username}
              onChange={(e) => setUsername(e.target.value)}
              className="w-full px-4 py-3 bg-white/5 border border-white/10 rounded-xl focus:ring-2 focus:ring-amber-500/50 outline-none text-white placeholder-slate-500"
              placeholder="输入用户名"
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-slate-300 mb-1.5">
              密码
            </label>
            <input
              type="password"
              required
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              className="w-full px-4 py-3 bg-white/5 border border-white/10 rounded-xl focus:ring-2 focus:ring-amber-500/50 outline-none text-white placeholder-slate-500"
              placeholder="输入密码（至少6位）"
            />
          </div>

          <button
            type="submit"
            disabled={loading}
            className="w-full py-3.5 bg-gradient-to-r from-amber-700/80 to-rose-800/80 hover:from-amber-600 hover:to-rose-700 text-white rounded-xl font-medium text-lg transition-all flex items-center justify-center gap-2 disabled:opacity-50"
          >
            {loading ? (
              <Loader2 className="w-5 h-5 animate-spin" />
            ) : (
              <>
                {mode === "login" ? "登录" : "注册"}
                <ArrowRight className="w-5 h-5" />
              </>
            )}
          </button>

          <div className="text-center">
            <button
              type="button"
              onClick={() => setMode(mode === "login" ? "register" : "login")}
              className="text-sm text-slate-400 hover:text-amber-200 transition-colors"
            >
              {mode === "login" ? "没有账号？立即注册" : "已有账号？去登录"}
            </button>
          </div>
        </form>
      </motion.div>
    </div>
  );
}
