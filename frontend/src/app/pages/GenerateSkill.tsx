import { useState } from "react";
import { Link, useNavigate } from "react-router";
import { Sparkles, ArrowLeft, Loader2 } from "lucide-react";
import { generateCharacter } from "../api/characters";
import { toast } from "sonner";

export function GenerateSkill() {
  const navigate = useNavigate();
  const [submitting, setSubmitting] = useState(false);
  const [query, setQuery] = useState("");

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!query.trim()) return;
    setSubmitting(true);
    try {
      const data = await generateCharacter(query.trim());
      navigate(`/characters/${data.id}`, { replace: true });
    } catch (err: any) {
      toast.error(err.response?.data?.message || "启动生成失败");
      setSubmitting(false);
    }
  };

  return (
    <div className="p-8 max-w-4xl mx-auto space-y-6">
      <div className="flex items-center gap-4">
        <Link to="/characters" className="w-10 h-10 bg-white border border-slate-200 rounded-full flex items-center justify-center text-slate-500 hover:text-slate-900 transition-colors shadow-sm">
          <ArrowLeft size={20} />
        </Link>
        <div>
          <h1 className="text-2xl font-bold text-slate-900">生成技能</h1>
          <p className="text-slate-500 mt-1">从互联网信息中提取新的智能体人格</p>
        </div>
      </div>

      <div className="bg-white border border-slate-200 rounded-3xl p-8 shadow-sm">
        <form onSubmit={handleSubmit} className="space-y-6">
          <div>
            <label className="block text-sm font-medium text-slate-900 mb-2">目标人格 / 主题</label>
            <input type="text" required value={query} onChange={(e) => setQuery(e.target.value)}
              className="w-full px-4 py-3 border border-slate-200 rounded-xl focus:ring-2 focus:ring-indigo-600 outline-none text-lg"
              placeholder="例如：史蒂夫·乔布斯，产品管理专家..." />
          </div>
          <button type="submit" disabled={submitting}
            className="w-full bg-indigo-600 hover:bg-indigo-700 disabled:opacity-50 text-white py-4 rounded-xl font-bold text-lg flex items-center justify-center gap-3 transition-colors shadow-md">
            {submitting ? <Loader2 className="animate-spin" size={24} /> : <Sparkles size={24} />}
            {submitting ? "正在启动..." : "启动生成流水线"}
          </button>
        </form>
      </div>
    </div>
  );
}
