import { createContext, useContext, useState, useEffect, type ReactNode } from "react";
import { getMe } from "../api/auth";
import { prefetchInitialRecommendations } from "../lib/recommendation-cache";

interface User {
  id: string;
  username: string;
  phone?: string;
}

interface AuthContextType {
  user: User | null;
  loading: boolean;
  token: string | null;
  setAuth: (token: string, user: User) => void;
  logout: () => void;
}

const AuthContext = createContext<AuthContextType>({
  user: null,
  loading: true,
  token: null,
  setAuth: () => {},
  logout: () => {},
});

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [token, setToken] = useState<string | null>(() => localStorage.getItem("token"));
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let cancelled = false;
    if (token) {
      setLoading(true);
      getMe()
        .then((data) => {
          if (!cancelled) {
            setUser(data.user || data);
            void prefetchInitialRecommendations().catch(() => {});
          }
        })
        .catch(() => {
          localStorage.removeItem("token");
          if (!cancelled) {
            setToken(null);
            setUser(null);
          }
        })
        .finally(() => {
          if (!cancelled) setLoading(false);
        });
    } else {
      setUser(null);
      setLoading(false);
    }
    return () => {
      cancelled = true;
    };
  }, [token]);

  useEffect(() => {
    const clearAuth = () => {
      setToken(null);
      setUser(null);
      setLoading(false);
    };
    const syncStorage = (event: StorageEvent) => {
      if (event.key === "token") {
        setToken(event.newValue);
        if (!event.newValue) setUser(null);
      }
    };
    window.addEventListener("madf-auth-cleared", clearAuth);
    window.addEventListener("storage", syncStorage);
    return () => {
      window.removeEventListener("madf-auth-cleared", clearAuth);
      window.removeEventListener("storage", syncStorage);
    };
  }, []);

  const setAuth = (newToken: string, newUser: User) => {
    localStorage.setItem("token", newToken);
    setToken(newToken);
    setUser(newUser);
    void prefetchInitialRecommendations().catch(() => {});
  };

  const logout = () => {
    localStorage.removeItem("token");
    setToken(null);
    setUser(null);
  };

  return (
    <AuthContext.Provider value={{ user, loading, token, setAuth, logout }}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  return useContext(AuthContext);
}
