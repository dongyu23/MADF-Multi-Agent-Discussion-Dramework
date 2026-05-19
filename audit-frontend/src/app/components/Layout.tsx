import { Suspense } from "react";
import { Link, Outlet, NavLink, useLocation, useNavigate } from "react-router";
import {
  LayoutDashboard,
  Users,
  MessageSquare,
  Shield,
  Activity,
  UserCog,
  Settings,
  LogOut,
  Loader2,
} from "lucide-react";
import { useAuditAuth } from "../store/audit-auth";

function PageFallback() {
  return (
    <div className="flex items-center justify-center h-full w-full py-20">
      <Loader2 className="animate-spin text-indigo-400" size={28} />
    </div>
  );
}

export function AuditLayout() {
  const location = useLocation();
  const navigate = useNavigate();
  const { admin, logout } = useAuditAuth();

  const handleLogout = () => {
    logout();
    navigate("/login");
  };

  const navItems = [
    { to: "/", icon: <LayoutDashboard size={20} />, label: "仪表盘" },
    { to: "/users", icon: <Users size={20} />, label: "用户管理" },
    { to: "/discussions", icon: <MessageSquare size={20} />, label: "讨论监控" },
    { to: "/audit", icon: <Shield size={20} />, label: "审计与追溯" },
    { to: "/health", icon: <Activity size={20} />, label: "系统健康" },
    { to: "/admins", icon: <UserCog size={20} />, label: "管理员" },
    { to: "/settings", icon: <Settings size={20} />, label: "系统设置" },
  ];

  return (
    <div className="flex h-screen bg-slate-50 font-sans text-slate-900">
      <aside className="w-64 bg-white border-r border-slate-200 flex flex-col">
        <div className="h-16 flex items-center px-6 border-b border-slate-200">
          <Link
            to="/"
            className="flex items-center gap-2 text-indigo-600 font-bold text-xl hover:text-indigo-700 transition-colors"
          >
            <Shield className="text-indigo-600" />
            MADF 管理
          </Link>
        </div>

        <nav className="flex-1 overflow-y-auto py-4 px-3 space-y-1">
          {navItems.map((item) => {
            const isActive =
              item.to === "/"
                ? location.pathname === "/"
                : location.pathname.startsWith(item.to);
            return (
              <NavLink
                key={item.to}
                to={item.to}
                className={`flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm font-medium transition-colors ${
                  isActive
                    ? "bg-indigo-50 text-indigo-700"
                    : "text-slate-600 hover:bg-slate-100 hover:text-slate-900"
                }`}
              >
                {item.icon}
                {item.label}
              </NavLink>
            );
          })}
        </nav>

        <div className="p-4 border-t border-slate-200">
          {admin && (
            <div className="px-3 py-2">
              <div className="text-sm font-medium text-slate-700 truncate">
                {admin.display_name || admin.username}
              </div>
              <div className="text-xs text-slate-400">{admin.role}</div>
            </div>
          )}
          <button
            onClick={handleLogout}
            className="flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm font-medium text-slate-600 hover:bg-slate-100 hover:text-slate-900 transition-colors w-full"
          >
            <LogOut size={20} />
            退出登录
          </button>
        </div>
      </aside>

      <main className="flex-1 overflow-auto bg-slate-50">
        <Suspense fallback={<PageFallback />}>
          <Outlet />
        </Suspense>
      </main>
    </div>
  );
}
