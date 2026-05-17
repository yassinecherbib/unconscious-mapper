"use client";

import { useRouter } from "next/navigation";
import type { Entry } from "@/lib/api";

interface Props {
  entry: Entry;
}

const TYPE_STYLES: Record<string, { badge: string; glyph: string }> = {
  dream:       { badge: "badge-dream",       glyph: "🌙" },
  psychedelic: { badge: "badge-psychedelic", glyph: "🌀" },
  meditation:  { badge: "badge-meditation",  glyph: "◎" },
};

function formatDate(iso: string) {
  return new Date(iso).toLocaleDateString("en-GB", {
    day:    "numeric",
    month:  "short",
    year:   "numeric",
    hour:   "2-digit",
    minute: "2-digit",
  });
}

function excerpt(text: string, max = 160) {
  return text.length > max ? text.slice(0, max).trimEnd() + "…" : text;
}

// eslint-disable-next-line @typescript-eslint/no-explicit-any
function hasError(a: any): boolean {
  return a && typeof a === "object" && a.error === "parse_failed";
}

export default function EntryCard({ entry }: Props) {
  const router     = useRouter();
  const style      = TYPE_STYLES[entry.entry_type] ?? TYPE_STYLES.dream;
  const analysis   = entry.analysis;
  const summary    = analysis?.jungian_summary ?? "";
  const themes     = analysis?.themes ?? [];
  const symbols    = analysis?.symbols ?? [];
  const archetypes = analysis?.archetypes ?? [];

  return (
    <article
      className="glass-card"
      role="button"
      tabIndex={0}
      onClick={() => router.push(`/journal/${entry.id}`)}
      onKeyDown={(e) => e.key === "Enter" && router.push(`/journal/${entry.id}`)}
      style={{
        padding: "20px 24px",
        cursor: "pointer",
        transition: "border-color 0.2s, transform 0.15s",
      }}
      onMouseEnter={(e) => (e.currentTarget.style.transform = "translateY(-2px)")}
      onMouseLeave={(e) => (e.currentTarget.style.transform = "translateY(0)")}
    >
      {/* Header row */}
      <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: 12 }}>
        <span
          className={style.badge}
          style={{ fontSize: 11, fontWeight: 600, padding: "3px 10px", borderRadius: 20, letterSpacing: "0.05em" }}
        >
          {style.glyph} {entry.entry_type}
        </span>
        <time style={{ fontSize: 11, color: "var(--text-muted)" }} dateTime={entry.created_at}>
          {formatDate(entry.created_at)}
        </time>
      </div>

      {/* Text excerpt */}
      <p style={{ fontSize: 14, color: "var(--text-secondary)", lineHeight: 1.65, margin: 0 }}>
        {excerpt(entry.raw_text)}
      </p>

      {/* Jungian summary */}
      {summary && (
        <p style={{
          fontSize: 12, color: "#a78bfa", lineHeight: 1.6,
          marginTop: 12, paddingTop: 12,
          borderTop: "1px solid var(--border-subtle)",
          fontStyle: "italic",
        }}>
          {summary}
        </p>
      )}

      {/* Symbol chips — top 4 */}
      {symbols.length > 0 && (
        <div style={{ display: "flex", flexWrap: "wrap", gap: 5, marginTop: 10 }}>
          {symbols.slice(0, 4).map((s) => (
            <span key={s.name} style={{
              fontSize: 10, padding: "2px 7px", borderRadius: 12,
              background: "rgba(139,92,246,0.08)",
              color: "#c4b5fd",
              border: "1px solid rgba(139,92,246,0.2)",
            }}>
              {s.name}
            </span>
          ))}
          {symbols.length > 4 && (
            <span style={{ fontSize: 10, color: "var(--text-muted)", alignSelf: "center" }}>
              +{symbols.length - 4} more
            </span>
          )}
        </div>
      )}

      {/* Archetype chips — top 2 */}
      {archetypes.length > 0 && (
        <div style={{ display: "flex", flexWrap: "wrap", gap: 5, marginTop: 6 }}>
          {archetypes.slice(0, 2).map((a) => (
            <span key={a.name} style={{
              fontSize: 10, padding: "2px 7px", borderRadius: 12,
              background: "rgba(245,158,11,0.08)",
              color: "#fcd34d",
              border: "1px solid rgba(245,158,11,0.2)",
            }}>
              ◈ {a.name}
            </span>
          ))}
        </div>
      )}

      {/* Theme tags */}
      {themes.length > 0 && (
        <div style={{ display: "flex", flexWrap: "wrap", gap: 6, marginTop: 8 }}>
          {themes.map((t) => (
            <span key={t} style={{
              fontSize: 10, padding: "2px 8px", borderRadius: 12,
              background: "rgba(99,102,241,0.1)",
              color: "#a5b4fc",
              border: "1px solid rgba(99,102,241,0.2)",
            }}>
              {t}
            </span>
          ))}
        </div>
      )}

      {/* Analysis states */}
      {!analysis && (
        <div style={{ marginTop: 10, display: "flex", alignItems: "center", gap: 6 }}>
          <span style={{
            display: "inline-block", width: 6, height: 6, borderRadius: "50%",
            background: "var(--neon-violet)",
            animation: "pulse 1.5s ease-in-out infinite",
          }} />
          <span style={{ fontSize: 11, color: "var(--text-muted)" }}>Analysing…</span>
        </div>
      )}

      {hasError(analysis) && (
        <div style={{ marginTop: 10 }}>
          <span style={{ fontSize: 11, color: "#f87171" }}>⚠ Analysis unavailable</span>
        </div>
      )}
    </article>
  );
}
