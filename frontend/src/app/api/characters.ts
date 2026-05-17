import client from "./client";

export interface CharacterItem {
  id: string;
  owner_id: string;
  name: string;
  description: string;
  tags: string[];
  is_public: boolean;
  status: string;
  created_at: string;
  quotes?: string[];
}

export async function getMyCharacters(page = 1, pageSize = 50) {
  const res = await client.get("/characters", { params: { page, page_size: pageSize } });
  return res.data.data;
}

export async function getCharacter(id: string) {
  const res = await client.get(`/characters/${id}`);
  return res.data.data;
}

export async function generateCharacter(query: string) {
  const res = await client.post("/characters/generate", { query });
  return res.data.data;
}

export async function createCharacter(data: { name: string; description?: string; tags?: string[]; is_public?: boolean }) {
  const res = await client.post("/characters", data);
  return res.data.data;
}

export async function updateCharacter(id: string, data: { description?: string; is_public?: boolean }) {
  const res = await client.put(`/characters/${id}`, data);
  return res.data.data;
}

export async function deleteCharacter(id: string) {
  const res = await client.delete(`/characters/${id}`);
  return res.data.data;
}

export async function getCharacterFiles(id: string, filePath?: string) {
  const params = filePath ? { path: filePath } : {};
  const res = await client.get(`/characters/${id}/files`, { params });
  return res.data.data;
}

export async function getGallery(search?: string, tag?: string, pageSize = 20, after?: string) {
  const res = await client.get("/characters/gallery", {
    params: { search, tag, page_size: pageSize, after },
  });
  return res.data.data;
}

export async function copyCharacter(id: string) {
  const res = await client.post(`/characters/${id}/copy`);
  return res.data.data;
}

export async function getRecommendations(excludeNames?: string[]) {
  const params: Record<string, string> = {};
  if (excludeNames?.length) params.exclude = excludeNames.join(",");
  const res = await client.get("/characters/recommendations", { timeout: 180_000, params });
  return res.data.data;
}
