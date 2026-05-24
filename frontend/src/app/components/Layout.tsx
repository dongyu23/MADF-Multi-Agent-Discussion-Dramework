import { Suspense, useEffect } from "react";
import { Link, Outlet, NavLink, useLocation, useNavigate } from "react-router";
import {
  MessageSquare,
  Users,
  Library,
  LogOut,
  Sparkles,
  LayoutDashboard,
  Loader2,
  House,
} from "lucide-react";
import { useAuth } from "../store/auth";

function PageFallback() {
  return (
    <div className="flex h-full w-full items-center justify-center py-20">
      <Loader2 className="animate-spin text-[#207362]" size={28} />
    </div>
  );
}

export function Layout() {
  const location = useLocation();
  const navigate = useNavigate();
  const { user, loading, token, logout } = useAuth();

  useEffect(() => {
    if (loading || (user && token)) return;
    const redirect = encodeURIComponent(location.pathname + location.search);
    navigate(`/login?redirect=${redirect}`, { replace: true });
  }, [loading, user, token, location.pathname, location.search, navigate]);

  const handleLogout = () => {
    logout();
    navigate("/login");
  };

  const navItems = [
    { to: "/dashboard", icon: <LayoutDashboard size={20} />, label: "仪表盘" },
    { to: "/discussions", icon: <MessageSquare size={20} />, label: "讨论管理" },
    { to: "/characters", icon: <Users size={20} />, label: "我的角色" },
    { to: "/gallery", icon: <Library size={20} />, label: "技能画廊" },
  ];

  if (loading || !user || !token) {
    return (
      <div className="flex h-screen w-screen items-center justify-center bg-[#f6f3ec]">
        <Loader2 className="animate-spin text-[#207362]" size={32} />
      </div>
    );
  }

  return (
    <div className="flex h-screen bg-[#f6f3ec] font-sans text-[#1d1a16]">
      <aside className="flex w-[76px] shrink-0 flex-col border-r border-[#2f281f] bg-[#1d1a16] text-[#e8dec9] shadow-[18px_0_60px_rgba(29,26,22,0.12)] md:w-64">
        <div className="flex h-16 items-center border-b border-white/10 px-4 md:px-6">
          <Link to="/dashboard" className="flex min-w-0 items-center gap-3 text-[#f0d9ad] transition-colors hover:text-white">
            <span className="flex h-9 w-9 shrink-0 items-center justify-center rounded-lg bg-[#f0d9ad] text-[#1d1a16]">
              <Sparkles size={19} />
            </span>
            <span className="hidden truncate text-xl font-semibold tracking-tight md:block">MADF</span>
          </Link>
        </div>

        <nav className="flex-1 space-y-1 overflow-y-auto px-3 py-4">
          {navItems.map((item) => {
            const isActive =
              item.to === "/"
                ? location.pathname === "/"
                : location.pathname.startsWith(item.to);
            return (
              <NavLink
                key={item.to}
                to={item.to}
                className={`flex items-center justify-center gap-3 rounded-lg px-3 py-2.5 text-sm font-semibold transition md:justify-start ${
                  isActive
                    ? "bg-[#f0d9ad] text-[#1d1a16] shadow-[0_10px_24px_rgba(0,0,0,0.18)]"
                    : "text-[#cdbfa9] hover:bg-white/8 hover:text-white"
                }`}
                title={item.label}
              >
                {item.icon}
                <span className="hidden md:inline">{item.label}</span>
              </NavLink>
            );
          })}
        </nav>

        <div className="border-t border-white/10 p-3 md:p-4">
          {user && (
            <div className="mb-2 hidden rounded-lg border border-white/10 bg-white/[0.06] px-3 py-2 md:block">
              <div className="text-[11px] font-semibold uppercase tracking-[0.18em] text-[#8f7d62]">Signed in</div>
              <div className="truncate text-sm font-semibold text-[#f0d9ad]">{user.username}</div>
            </div>
          )}
          <Link
            to="/"
            className="mb-1 flex w-full items-center justify-center gap-3 rounded-lg px-3 py-2.5 text-sm font-semibold text-[#cdbfa9] transition hover:bg-white/8 hover:text-white md:justify-start"
            title="展示首页"
          >
            <House size={20} />
            <span className="hidden md:inline">展示首页</span>
          </Link>
          <button
            onClick={handleLogout}
            className="flex w-full items-center justify-center gap-3 rounded-lg px-3 py-2.5 text-sm font-semibold text-[#cdbfa9] transition hover:bg-white/8 hover:text-white md:justify-start"
            title="退出登录"
          >
            <LogOut size={20} />
            <span className="hidden md:inline">退出登录</span>
          </button>
        </div>
      </aside>

      <main className="flex min-w-0 flex-1 flex-col overflow-hidden">
        <div className="relative flex-1 overflow-auto bg-[#f6f3ec]">
          <Suspense fallback={<PageFallback />}>
            <Outlet />
          </Suspense>
        </div>
      </main>
    </div>
  );
}
