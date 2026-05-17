import { createClient } from "@/lib/supabase/client";

const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

/** Get the current user's access token from the browser session. */
async function getToken(): Promise<string | null> {
  const supabase = createClient();
  const {
    data: { session },
  } = await supabase.auth.getSession();
  return session?.access_token ?? null;
}

/** Core fetch wrapper — injects JWT, throws on non-2xx. */
async function apiFetch<T>(path: string, options?: RequestInit): Promise<T> {
  const token = await getToken();

  const res = await fetch(`${API_URL}${path}`, {
    ...options,
    headers: {
      "Content-Type": "application/json",
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
      ...options?.headers,
    },
  });

  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: "Request failed" }));
    throw new Error(err.detail ?? `HTTP ${res.status}`);
  }

  return res.json() as Promise<T>;
}

/** Typed API surface — used by all client components. */
export const api = {
  entries: {
    create: (data: { raw_text: string; entry_type: string }) =>
      apiFetch<Entry>("/entries", {
        method: "POST",
        body: JSON.stringify(data),
      }),
    list: () => apiFetch<Entry[]>("/entries"),
    get: (id: string) => apiFetch<Entry>(`/entries/${id}`),
  },
  graph: {
    get: () => apiFetch<GraphData>("/graph"),
  },
  unlock: {
    progress: () => apiFetch<UnlockProgress>("/entries/unlock/progress"),
  },
};

// ── Shared types ──────────────────────────────────────────────────────────────

export interface Entry {
  id: string;
  user_id: string;
  raw_text: string;
  entry_type: "dream" | "psychedelic" | "meditation";
  analysis: AnalysisResult | null;
  created_at: string;
}

export interface AnalysisResult {
  symbols: { name: string; category: string; significance: string }[];
  archetypes: { name: string; confidence: number; evidence: string }[];
  emotions: { name: string; valence: number; intensity: number }[];
  themes: string[];
  jungian_summary: string;
  connections_to_previous: string[];
}

export interface GraphData {
  nodes: { id: string; value: number }[];
  edges: { source: string; target: string; value: number }[];
}

export interface UnlockProgress {
  entry_count: number;
  days_elapsed: number;
  unlocked: boolean;
}
