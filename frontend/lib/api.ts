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
type ApiFetchOptions = RequestInit & {
  timeoutMs?: number;
};

const DEFAULT_TIMEOUT_MS = 60000;

async function apiFetch<T>(path: string, options: ApiFetchOptions = {}): Promise<T> {
  const { timeoutMs = DEFAULT_TIMEOUT_MS, ...fetchOptions } = options;
  const token = await getToken();
  const controller = new AbortController();
  const timeoutId = setTimeout(() => controller.abort(), timeoutMs);

  try {
    const res = await fetch(`${API_URL}${path}`, {
      ...fetchOptions,
      signal: controller.signal,
      headers: {
        "Content-Type": "application/json",
        ...(token ? { Authorization: `Bearer ${token}` } : {}),
        ...fetchOptions.headers,
      },
    });

    clearTimeout(timeoutId);

    if (!res.ok) {
      let detail = "Request failed";
      try {
        const err = await res.json();
        detail = err.detail ?? `HTTP ${res.status}`;
      } catch {
        try {
          const text = await res.text();
          if (text) {
            detail = text.substring(0, 200);
          }
        } catch {}
      }
      throw new Error(detail);
    }

    return res.json() as Promise<T>;
  } catch (err: unknown) {
    clearTimeout(timeoutId);
    if (
      err &&
      typeof err === "object" &&
      "name" in err &&
      err.name === "AbortError"
    ) {
      throw new Error(`Request timed out after ${Math.round(timeoutMs / 1000)} seconds. The server might be busy or cold-starting.`);
    }
    throw err;
  }
}

/** Typed API surface — used by all client components. */
export const api = {
  entries: {
    create: (data: { raw_text: string; entry_type: string }) =>
      apiFetch<{ entry_id: string; amplification_questions: AmplificationQuestion[] }>("/entries", {
        method: "POST",
        body: JSON.stringify(data),
        timeoutMs: 90000,
      }),
    amplify: (data: { entry_id: string; personal_associations: Record<string, string> }) =>
      apiFetch<Entry>("/entries/amplify", {
        method: "POST",
        body: JSON.stringify(data),
        timeoutMs: 240000,
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
  chat: {
    getLongitudinal: () => apiFetch<LongitudinalAnalysis>("/chat/longitudinal"),
  }
};

// ── Shared types ──────────────────────────────────────────────────────────────

export interface AmplificationQuestion {
  symbol: string;
  question: string;
}

export interface Entry {
  id: string;
  user_id: string;
  raw_text: string;
  entry_type: "dream" | "psychedelic" | "meditation";
  analysis: AnalysisResult | null;
  created_at: string;
}

export interface Symbol {
  name: string;
  category: string;
  significance: string;
}

export interface Archetype {
  name: string;
  confidence: number;
  evidence: string;
  projection_status?: "projected" | "integrating" | "ambiguous";
}

export interface SymbolArchetypeAttribution {
  symbol: string;
  archetype: string;
  confidence: number;
  evidence: string;
}

export interface Emotion {
  name: string;
  valence: number;
  intensity: number;
}

export interface Flag {
  present: boolean;
  form?: string;
  severity?: string;
  evidence?: string;
}

export interface IntegrationRiskResult {
  spiritual_inflation: Flag;
  ego_dissolution_without_regrounding: Flag;
  shadow_bypassing: Flag;
  premature_closure: Flag;
  integration_guidance: string;
  overall_risk_level: "none" | "low" | "moderate" | "high";
}

export interface AnalysisResult {
  symbols: Symbol[];
  archetypes: Archetype[];
  emotions: Emotion[];
  themes: string[];
  compensation_axis?: string;
  ego_strength_signal?: number;
  lysis_assessment?: "resolved" | "unresolved" | "ambiguous";
  jungian_summary: string;
  connections_to_previous: string[];
  symbol_archetype_attributions?: SymbolArchetypeAttribution[];
  integration_risk?: IntegrationRiskResult;
  error?: string;
}

export interface GraphNode {
  id: string;
  label?: string;
  type?: "symbol" | "archetype";
  value: number;
  dominant_archetype?: string | null;
  dominant_confidence?: number;
  is_bridge?: boolean;
  bridge_score?: number;
}

export interface GraphEdge {
  source: string;
  target: string;
  value: number;
  type?: "cooccurrence" | "attribution";
  decayed_value?: number;
  recency_weight?: number;
  confidence?: number;
}

export interface GraphData {
  nodes: GraphNode[];
  edges: GraphEdge[];
  meta?: {
    half_life_days?: number;
    legacy_inference_multiplier?: number;
  };
}

export interface UnlockProgress {
  entry_count: number;
  days_elapsed: number;
  unlocked: boolean;
}

export interface LongitudinalAnalysis {
  result: {
    individuation_arc_summary: string;
    dynamic_shadow_tracker: string;
    transpersonal_integration_state: string;
    clinical_risk_advisory?: string;
  };
  season_signal: "ego_inflection" | "archetype_rotation" | "lysis_shift";
  trigger_reasons: string[];
  created_at: string;
}
