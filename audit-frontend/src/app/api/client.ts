import axios from "axios";

export const adminClient = axios.create({
  baseURL: "/audit/api/v1/admin",
  headers: { "Content-Type": "application/json" },
  timeout: 60000,
});

adminClient.interceptors.request.use((config) => {
  const token = localStorage.getItem("audit_token");
  if (token) config.headers.Authorization = `Bearer ${token}`;
  return config;
});

adminClient.interceptors.response.use(
  (r) => r,
  (error) => {
    if (error.response?.status === 401) {
      localStorage.removeItem("audit_token");
      localStorage.removeItem("audit_admin");
      window.location.href = "/audit/login";
    }
    return Promise.reject(error);
  }
);
