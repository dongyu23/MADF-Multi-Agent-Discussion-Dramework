import client from "./client";

export async function getDiscussions(page = 1, pageSize = 20) {
  const res = await client.get("/discussions", { params: { page, page_size: pageSize } });
  return res.data.data;
}

export async function getDiscussion(id: string) {
  const res = await client.get(`/discussions/${id}`);
  return res.data.data;
}

export async function createDiscussion(topic: string, characterIds: string[], duration: number) {
  const res = await client.post("/discussions", {
    topic,
    character_ids: characterIds,
    duration,
  });
  return res.data.data;
}

export async function getMessages(id: string) {
  const res = await client.get(`/discussions/${id}/messages`);
  return res.data.data;
}

export async function intervene(id: string, content: string) {
  const res = await client.post(`/discussions/${id}/intervene`, { content });
  return res.data.data;
}

export async function deleteDiscussion(id: string) {
  const res = await client.delete(`/discussions/${id}`);
  return res.data.data;
}

export function buildStreamUrl(id: string, after?: string) {
  let url = `/api/v1/discussions/${id}/stream`;
  if (after) url += `?after=${encodeURIComponent(after)}`;
  return url;
}
