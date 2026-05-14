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
        const redirect = encodeURIComponent(window.location.pathname + window.location.search);
        window.location.href = `/login?redirect=${redirect}`;
      }
    }
    return Promise.reject(error);
  }
);

export default client;
