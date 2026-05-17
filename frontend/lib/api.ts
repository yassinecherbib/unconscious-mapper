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
    create: (data: {
      raw_text: string;
      entry_type: string;
      personal_associations?: { symbol: string; meaning: string }[];
    }) =>
      apiFetch<Entry>("/entries", {
        method: "POST",
        body: JSON.stringify(data),
      }),
    list: () => apiFetch<Entry[]>("/entries"),
    get: (id: string) => apiFetch<Entry>(`/entries/${id}`),
    amplify: (data: { raw_text: string; entry_type: string }) =>
      apiFetch<AmplifyResponse>("/entries/amplify", {
        method: "POST",
        body: JSON.stringify(data),
      }),
  },
  graph: {
    get: () => apiFetch<GraphData>("/graph"),
    complexes: () => apiFetch<ComplexData[]>("/graph/complexes"),
  },
  chat: {
    /** Stream chat — returns a ReadableStream reader. */
    stream: async (message: string, seedEntryId?: string) => {
      const token = await getToken();
      const url = seedEntryId
        ? `${API_URL}/chat/stream?seed_entry_id=${seedEntryId}`
        : `${API_URL}/chat/stream`;

      const res = await fetch(url, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          ...(token ? { Authorization: `Bearer ${token}` } : {}),
        },
        body: JSON.stringify({ message }),
      });

      if (!res.ok) {
        const err = await res.json().catch(() => ({ detail: "Chat failed" }));
        throw new Error(err.detail ?? `HTTP ${res.status}`);
      }

      return res.body!.getReader();
    },
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
  integration_risk?: { integration_guidance?: string } | null;
  integration_guidance?: string;
  created_at: string;
}

export interface AnalysisResult {
  symbols: { name: string; category: string; significance: string }[];
  archetypes: {
    name: string;
    confidence: number;
    evidence: string;
    projection_status?: string;
  }[];
  emotions: { name: string; valence: number; intensity: number }[];
  themes: string[];
  jungian_summary: string;
  connections_to_previous: string[];
  ego_strength_signal?: { score: number; evidence: string } | null;
  lysis_assessment?: {
    phase: string;
    confidence: number;
    evidence: string;
  } | null;
  compensation_axis?: {
    conscious_attitude: string;
    compensating_content: string;
  } | null;
  error?: string;
}

export interface GraphData {
  nodes: { id: string; value: number; avg_intensity?: number }[];
  edges: {
    source: string;
    target: string;
    value: number;
    avg_intensity?: number;
    avg_valence?: number;
    dominant_emotion?: string;
  }[];
}

export interface ComplexData {
  id: string;
  name: string;
  summary: string;
  symbols: string[];
  overdetermined_symbols?: string[];
  affective_core?: string;
  projection_status?: string;
  golden_shadow?: boolean;
  golden_shadow_owned?: boolean;
  individuation_note?: string;
  created_at: string;
}

export interface AmplifyResponse {
  symbols_to_amplify: {
    symbol: string;
    question: string;
    context_hint: string;
  }[];
}

export interface UnlockProgress {
  entry_count: number;
  days_elapsed: number;
  unlocked: boolean;
}
