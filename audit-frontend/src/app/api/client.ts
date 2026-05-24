import axios from "axios";
import { AUDIT_API_BASE, AUDIT_LOGIN_PATH } from "./base";

export const adminClient = axios.create({
  baseURL: `${AUDIT_API_BASE}/admin`,
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
      window.location.href = AUDIT_LOGIN_PATH;
    }
    return Promise.reject(error);
  }
);
