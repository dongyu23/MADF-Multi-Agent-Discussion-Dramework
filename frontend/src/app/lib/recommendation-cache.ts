import { getRecommendations } from "../api/characters";

export const RECS_KEY = "madf_recs";

export type RecItem = { name: string; description: string; query: string };

let initialRecommendationsPromise: Promise<RecItem[]> | null = null;

export function loadCachedRecommendations(): RecItem[] | null {
  try {
    const raw = sessionStorage.getItem(RECS_KEY);
    if (raw) return JSON.parse(raw) as RecItem[];
  } catch {
    // Ignore broken sessionStorage data; the next request will refresh it.
  }
  return null;
}

export function saveCachedRecommendations(items: RecItem[]) {
  try {
    sessionStorage.setItem(RECS_KEY, JSON.stringify(items));
  } catch {
    // Ignore quota/private-mode failures. Recommendations are optional.
  }
}

export function clearCachedRecommendations() {
  try {
    sessionStorage.removeItem(RECS_KEY);
  } catch {
    // Ignore storage failures.
  }
  initialRecommendationsPromise = null;
}

export function prefetchInitialRecommendations(force = false): Promise<RecItem[]> {
  const cached = loadCachedRecommendations();
  if (!force && cached?.length) return Promise.resolve(cached);
  if (!force && initialRecommendationsPromise) return initialRecommendationsPromise;

  initialRecommendationsPromise = getRecommendations()
    .then((data) => {
      const items: RecItem[] = data.items || [];
      if (items.length > 0) saveCachedRecommendations(items);
      return items;
    })
    .catch((error) => {
      initialRecommendationsPromise = null;
      throw error;
    });

  return initialRecommendationsPromise;
}

export async function fetchMoreRecommendations(existing: RecItem[]): Promise<RecItem[]> {
  const data = await getRecommendations(existing.map((item) => item.name));
  return data.items || [];
}
