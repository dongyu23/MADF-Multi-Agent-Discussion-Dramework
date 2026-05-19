import { createContext, useContext, useState, useCallback, type ReactNode } from "react";
import { loginAudit } from "../api/admin";

interface AdminUser { id: string; username: string; display_name?: string; role: string; }
interface AuthCtx { admin: AdminUser | null; token: string | null; login: (u: string, p: string) => Promise<void>; logout: () => void; isAuthenticated: boolean; }

const Ctx = createContext<AuthCtx>({ admin: null, token: null, login: async () => {}, logout: () => {}, isAuthenticated: false });

export function AuthProvider({ children }: { children: ReactNode }) {
  const [token, setToken] = useState<string | null>(() => localStorage.getItem("audit_token"));
  const [admin, setAdmin] = useState<AdminUser | null>(() => {
    try { const r = localStorage.getItem("audit_admin"); return r ? JSON.parse(r) : null; } catch { return null; }
  });

  const loginFn = useCallback(async (username: string, password: string) => {
    const data = await loginAudit(username, password);
    localStorage.setItem("audit_token", data.token);
    localStorage.setItem("audit_admin", JSON.stringify(data.admin_user));
    setToken(data.token); setAdmin(data.admin_user);
  }, []);

  const logoutFn = useCallback(() => {
    localStorage.removeItem("audit_token"); localStorage.removeItem("audit_admin");
    setToken(null); setAdmin(null);
  }, []);

  return <Ctx.Provider value={{ admin, token, login: loginFn, logout: logoutFn, isAuthenticated: !!token }}>{children}</Ctx.Provider>;
}

export function useAuditAuth() { return useContext(Ctx); }
