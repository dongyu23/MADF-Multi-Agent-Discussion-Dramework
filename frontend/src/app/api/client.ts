import axios from "axios";

// In dev: Vite proxies /api to localhost:8000. In Docker: Nginx proxies /api to backend:8000.
const BASE = "/api/v1";

const client = axios.create({
  baseURL: BASE,
  headers: { "Content-Type": "application/json" },
  timeout: 30000,
});

client.interceptors.request.use((config) => {
  const token = localStorage.getItem("token");
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

client.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 401) {
      const code = error.response.data?.code;
      if (code === 1002 || code === 1003) {
        localStorage.removeItem("token");
        window.dispatchEvent(new Event("madf-auth-cleared"));
        const params = new URLSearchParams(window.location.search);
        const currentPath = window.location.pathname;
        const redirectTarget =
          currentPath === "/login" || currentPath === "/register"
            ? params.get("redirect") || "/dashboard"
            : currentPath + window.location.search;
        const loginUrl = `/login?redirect=${encodeURIComponent(redirectTarget)}`;
        if (window.location.pathname + window.location.search !== loginUrl) {
          window.location.replace(loginUrl);
        }
      }
    }
    return Promise.reject(error);
  }
);

export default client;
