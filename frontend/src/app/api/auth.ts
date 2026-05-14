import client from "./client";

export async function register(username: string, password: string, phone?: string) {
  const res = await client.post("/auth/register", { username, password, phone });
  return res.data.data;
}

export async function login(username: string, password: string) {
  const res = await client.post("/auth/login", { username, password });
  return res.data.data;
}

export async function getMe() {
  const res = await client.get("/auth/me");
  return res.data.data;
}
