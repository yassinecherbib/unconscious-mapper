"use client";

import { useState, useEffect } from "react";
import { useParams, useRouter } from "next/navigation";
import { api, type Entry, type AnalysisResult } from "@/lib/api";

// ── helpers ──────────────────────────────────────────────────────────────────

function formatDate(iso: string) {
  return new Date(iso).toLocaleDateString("en-GB", {
    weekday: "long",
    day:     "numeric",
    month:   "long",
    year:    "numeric",
    hour:    "2-digit",
    minute:  "2-digit",
  });
}

function ValenceBar({ value }: { value: number }) {
  // value: -1 to 1. Centre = neutral. Left = negative, right = positive.
  const pct = ((value + 1) / 2) * 100; // map -1..1 → 0..100
  const color = value < -0.2 ? "#f87171" : value > 0.2 ? "#86efac" : "#94a3b8";
  return (
    <div style={{
      height: 4, borderRadius: 2, background: "rgba(255,255,255,0.06)",
      position: "relative", overflow: "hidden",
    }}>
      <div style={{
        position: "absolute", left: 0, top: 0, bottom: 0,
        width: `${pct}%`, background: color, borderRadius: 2,
        transition: "width 0.6s ease",
      }} />
    </div>
  );
}

function ConfidenceBar({ value }: { value: number }) {
  const pct = Math.round(value * 100);
  return (
    <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
      <div style={{
        flex: 1, height: 4, borderRadius: 2, background: "rgba(255,255,255,0.06)",
        position: "relative", overflow: "hidden",
      }}>
        <div style={{
          position: "absolute", left: 0, top: 0, bottom: 0,
          width: `${pct}%`,
          background: "linear-gradient(90deg, #7c3aed, #a78bfa)",
          borderRadius: 2,
          transition: "width 0.6s ease",
        }} />
      </div>
      <span style={{ fontSize: 10, color: "var(--text-muted)", minWidth: 28 }}>{pct}%</span>
    </div>
  );
}

function EgoStrengthGauge({ score }: { score: number }) {
  // score: 1-10
  const pct = (score / 10) * 100;
  const color = score <= 3 ? "#f87171" : score <= 6 ? "#fbbf24" : "#86efac";
  return (
    <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
      <div style={{
        flex: 1, height: 6, borderRadius: 3,
        background: "rgba(255,255,255,0.06)",
        position: "relative", overflow: "hidden",
      }}>
        <div style={{
          position: "absolute", left: 0, top: 0, bottom: 0,
          width: `${pct}%`, background: color, borderRadius: 3,
          transition: "width 0.8s ease",
        }} />
      </div>
      <span style={{ fontSize: 14, fontWeight: 700, color, minWidth: 32 }}>{score}/10</span>
    </div>
  );
}

// ── section card wrapper ──────────────────────────────────────────────────────

function Section({ title, children, accent }: { title: string; children: React.ReactNode; accent?: string }) {
  return (
    <section className="glass-card" style={{ padding: "24px 28px" }}>
      <h2 style={{
        fontSize: 11, fontWeight: 700, letterSpacing: "0.1em",
        textTransform: "uppercase", color: accent ?? "var(--text-muted)",
        margin: "0 0 20px",
      }}>
        {title}
      </h2>
      {children}
    </section>
  );
}

// ── main view ─────────────────────────────────────────────────────────────────

// eslint-disable-next-line @typescript-eslint/no-explicit-any
function hasError(a: any): boolean {
  return a && typeof a === "object" && a.error === "parse_failed";
}

export default function EntryDetailPage() {
  const { id }   = useParams<{ id: string }>();
  const router   = useRouter();
  const [entry, setEntry] = useState<Entry | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError]     = useState<string | null>(null);

  useEffect(() => {
    api.entries.get(id)
      .then(setEntry)
      .catch((err: unknown) =>
        setError(err instanceof Error ? err.message : "Entry not found")
      )
      .finally(() => setLoading(false));
  }, [id]);

  // ── loading ──
  if (loading) {
    return (
      <div style={{ textAlign: "center", padding: "80px 0" }}>
        <div style={{
          width: 36, height: 36, borderRadius: "50%", margin: "0 auto",
          border: "2px solid var(--neon-violet)", borderTopColor: "transparent",
          animation: "spin 1s linear infinite",
        }} />
        <p style={{ color: "var(--text-muted)", fontSize: 13, marginTop: 14 }}>
          Retrieving entry from the archive…
        </p>
        <style>{`@keyframes spin { to { transform: rotate(360deg); } }`}</style>
      </div>
    );
  }

  // ── error / not found ──
  if (error || !entry) {
    return (
      <div style={{ textAlign: "center", padding: "80px 0" }}>
        <p style={{ color: "#f87171", fontSize: 14 }}>{error ?? "Entry not found"}</p>
        <button className="btn-primary" style={{ marginTop: 20 }} onClick={() => router.back()}>
          ← Back
        </button>
      </div>
    );
  }

  const analysis: AnalysisResult | null =
    !hasError(entry.analysis) ? (entry.analysis as AnalysisResult | null) : null;

  const TYPE_GLYPH: Record<string, string> = {
    dream: "🌙", psychedelic: "🌀", meditation: "◎",
  };

  return (
    <div style={{ maxWidth: 720, margin: "0 auto" }}>

      {/* Back */}
      <button
        onClick={() => router.back()}
        style={{
          background: "none", border: "none", cursor: "pointer",
          color: "var(--text-muted)", fontSize: 13, padding: 0,
          marginBottom: 24, display: "flex", alignItems: "center", gap: 6,
        }}
      >
        ← Journal
      </button>

      {/* Header */}
      <header style={{ marginBottom: 32 }}>
        <div style={{ display: "flex", alignItems: "center", gap: 10, marginBottom: 10 }}>
          <span style={{ fontSize: 22 }}>{TYPE_GLYPH[entry.entry_type] ?? "◎"}</span>
          <span style={{
            fontSize: 11, fontWeight: 600, letterSpacing: "0.08em",
            textTransform: "uppercase", color: "var(--text-muted)",
          }}>
            {entry.entry_type}
          </span>
        </div>
        <time style={{ fontSize: 13, color: "var(--text-muted)" }}>
          {formatDate(entry.created_at)}
        </time>
      </header>

      <div style={{ display: "flex", flexDirection: "column", gap: 20 }}>

        {/* Raw text */}
        <Section title="Entry">
          <p style={{
            fontSize: 15, color: "var(--text-secondary)", lineHeight: 1.8,
            margin: 0, whiteSpace: "pre-wrap",
          }}>
            {entry.raw_text}
          </p>
        </Section>

        {/* Analysis unavailable */}
        {!analysis && entry.analysis && hasError(entry.analysis) && (
          <div className="glass-card" style={{ padding: "20px 24px", borderColor: "rgba(248,113,113,0.3)" }}>
            <p style={{ color: "#f87171", fontSize: 13, margin: 0 }}>
              ⚠ Jungian analysis could not be completed for this entry.
              The raw text has been preserved.
            </p>
          </div>
        )}

        {/* Analysis not yet run */}
        {!entry.analysis && (
          <div className="glass-card" style={{ padding: "20px 24px" }}>
            <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
              <span style={{
                display: "inline-block", width: 8, height: 8, borderRadius: "50%",
                background: "var(--neon-violet)",
                animation: "pulse 1.5s ease-in-out infinite",
              }} />
              <p style={{ color: "var(--text-muted)", fontSize: 13, margin: 0 }}>
                Analysis in progress — this usually takes a few seconds.
              </p>
            </div>
          </div>
        )}

        {/* Jungian summary */}
        {analysis?.jungian_summary && (
          <Section title="Jungian Reading">
            <p style={{
              fontSize: 14, color: "#c4b5fd", lineHeight: 1.8,
              margin: 0, fontStyle: "italic",
            }}>
              {analysis.jungian_summary}
            </p>
          </Section>
        )}

        {/* ─── Dig Deeper — Chat button ─────────────────────────── */}
        {analysis && (
          <button
            onClick={() => router.push(`/chat?entry=${entry.id}`)}
            className="glass-card"
            style={{
              padding: "18px 24px",
              cursor: "pointer",
              border: "1px solid rgba(192,132,252,0.25)",
              background: "linear-gradient(135deg, rgba(124,58,237,0.08), rgba(192,132,252,0.06))",
              display: "flex", alignItems: "center", gap: 14,
              transition: "all 0.2s",
              textAlign: "left",
            }}
            onMouseEnter={(e) => {
              e.currentTarget.style.borderColor = "rgba(192,132,252,0.5)";
              e.currentTarget.style.transform = "translateY(-1px)";
            }}
            onMouseLeave={(e) => {
              e.currentTarget.style.borderColor = "rgba(192,132,252,0.25)";
              e.currentTarget.style.transform = "translateY(0)";
            }}
          >
            <span style={{
              fontSize: 28, width: 48, height: 48, borderRadius: "50%",
              background: "rgba(192,132,252,0.12)",
              display: "flex", alignItems: "center", justifyContent: "center",
              flexShrink: 0,
            }}>
              ◎
            </span>
            <div>
              <div style={{ fontSize: 14, fontWeight: 600, color: "#c4b5fd" }}>
                Dig Deeper — Inner Voice
              </div>
              <div style={{ fontSize: 12, color: "var(--text-muted)", marginTop: 2, lineHeight: 1.4 }}>
                Open a dialogue anchored to this entry. The AI will draw from its
                symbols, emotions, and archetypal context to speak from within your psyche.
              </div>
            </div>
            <span style={{ color: "#c4b5fd", fontSize: 16, marginLeft: "auto", flexShrink: 0 }}>→</span>
          </button>
        )}

        {/* Ego Strength Signal */}
        {analysis?.ego_strength_signal && (
          <Section title="Ego Strength" accent="#86efac">
            <EgoStrengthGauge score={analysis.ego_strength_signal.score} />
            <p style={{ fontSize: 12, color: "var(--text-secondary)", margin: "12px 0 0", lineHeight: 1.6 }}>
              {analysis.ego_strength_signal.evidence}
            </p>
          </Section>
        )}

        {/* Compensation Axis */}
        {analysis?.compensation_axis && (
          <Section title="Compensation Axis" accent="#fbbf24">
            <div style={{ display: "flex", gap: 16, alignItems: "stretch" }}>
              <div style={{
                flex: 1, padding: "14px 16px", borderRadius: 10,
                background: "rgba(248,113,113,0.06)", border: "1px solid rgba(248,113,113,0.15)",
              }}>
                <div style={{ fontSize: 10, fontWeight: 600, color: "#f87171", textTransform: "uppercase", letterSpacing: "0.08em", marginBottom: 6 }}>
                  Conscious Attitude
                </div>
                <p style={{ fontSize: 13, color: "var(--text-secondary)", margin: 0, lineHeight: 1.5 }}>
                  {analysis.compensation_axis.conscious_attitude}
                </p>
              </div>
              <div style={{
                display: "flex", alignItems: "center", fontSize: 18, color: "var(--text-muted)",
                flexShrink: 0, padding: "0 4px",
              }}>
                ⇄
              </div>
              <div style={{
                flex: 1, padding: "14px 16px", borderRadius: 10,
                background: "rgba(134,239,172,0.06)", border: "1px solid rgba(134,239,172,0.15)",
              }}>
                <div style={{ fontSize: 10, fontWeight: 600, color: "#86efac", textTransform: "uppercase", letterSpacing: "0.08em", marginBottom: 6 }}>
                  Compensating Content
                </div>
                <p style={{ fontSize: 13, color: "var(--text-secondary)", margin: 0, lineHeight: 1.5 }}>
                  {analysis.compensation_axis.compensating_content}
                </p>
              </div>
            </div>
          </Section>
        )}

        {/* Lysis Assessment */}
        {analysis?.lysis_assessment && (
          <Section title="Lysis (Resolution Phase)" accent="#a78bfa">
            <div style={{ display: "flex", alignItems: "center", gap: 12, marginBottom: 10 }}>
              <span style={{
                fontSize: 12, padding: "3px 10px", borderRadius: 8,
                background: "rgba(167,139,250,0.15)", color: "#c4b5fd",
                fontWeight: 600, textTransform: "uppercase", letterSpacing: "0.05em",
              }}>
                {analysis.lysis_assessment.phase}
              </span>
              <ConfidenceBar value={analysis.lysis_assessment.confidence} />
            </div>
            <p style={{ fontSize: 12, color: "var(--text-secondary)", margin: 0, lineHeight: 1.6 }}>
              {analysis.lysis_assessment.evidence}
            </p>
          </Section>
        )}

        {/* Symbols */}
        {analysis?.symbols && analysis.symbols.length > 0 && (
          <Section title={`Symbols — ${analysis.symbols.length} extracted`}>
            <div style={{ display: "flex", flexDirection: "column", gap: 14 }}>
              {analysis.symbols.map((sym) => (
                <div key={sym.name} style={{
                  padding: "12px 16px", borderRadius: 10,
                  background: "rgba(139,92,246,0.06)",
                  border: "1px solid rgba(139,92,246,0.15)",
                }}>
                  <div style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: 5 }}>
                    <span style={{ fontSize: 13, fontWeight: 600, color: "#c4b5fd" }}>
                      {sym.name}
                    </span>
                    <span style={{
                      fontSize: 10, padding: "1px 6px", borderRadius: 8,
                      background: "rgba(139,92,246,0.15)",
                      color: "#a78bfa",
                    }}>
                      {sym.category}
                    </span>
                  </div>
                  <p style={{ fontSize: 12, color: "var(--text-secondary)", margin: 0, lineHeight: 1.6 }}>
                    {sym.significance}
                  </p>
                </div>
              ))}
            </div>
          </Section>
        )}

        {/* Archetypes */}
        {analysis?.archetypes && analysis.archetypes.length > 0 && (
          <Section title="Archetypes">
            <div style={{ display: "flex", flexDirection: "column", gap: 16 }}>
              {analysis.archetypes.map((arch) => (
                <div key={arch.name}>
                  <div style={{ display: "flex", justifyContent: "space-between", marginBottom: 6 }}>
                    <span style={{ fontSize: 13, fontWeight: 600, color: "#fcd34d" }}>
                      ◈ {arch.name}
                    </span>
                    {arch.projection_status && (
                      <span style={{
                        fontSize: 10, padding: "1px 6px", borderRadius: 8,
                        background: "rgba(251,191,36,0.1)", color: "#fbbf24",
                      }}>
                        {arch.projection_status}
                      </span>
                    )}
                  </div>
                  <ConfidenceBar value={arch.confidence} />
                  <p style={{ fontSize: 12, color: "var(--text-secondary)", margin: "8px 0 0", lineHeight: 1.6 }}>
                    {arch.evidence}
                  </p>
                </div>
              ))}
            </div>
          </Section>
        )}

        {/* Emotions */}
        {analysis?.emotions && analysis.emotions.length > 0 && (
          <Section title="Emotional Landscape">
            <div style={{ display: "flex", flexDirection: "column", gap: 14 }}>
              {analysis.emotions.map((em) => (
                <div key={em.name}>
                  <div style={{ display: "flex", justifyContent: "space-between", marginBottom: 6 }}>
                    <span style={{ fontSize: 13, fontWeight: 500, color: "var(--text-secondary)" }}>
                      {em.name}
                    </span>
                    <span style={{ fontSize: 11, color: "var(--text-muted)" }}>
                      intensity {Math.round(em.intensity * 100)}%
                    </span>
                  </div>
                  <ValenceBar value={em.valence} />
                </div>
              ))}
            </div>
          </Section>
        )}

        {/* Themes */}
        {analysis?.themes && analysis.themes.length > 0 && (
          <Section title="Themes">
            <div style={{ display: "flex", flexWrap: "wrap", gap: 8 }}>
              {analysis.themes.map((t) => (
                <span key={t} style={{
                  fontSize: 13, padding: "5px 14px", borderRadius: 20,
                  background: "rgba(99,102,241,0.1)",
                  color: "#a5b4fc",
                  border: "1px solid rgba(99,102,241,0.25)",
                }}>
                  {t}
                </span>
              ))}
            </div>
          </Section>
        )}

        {/* Connections to previous entries */}
        {analysis?.connections_to_previous && analysis.connections_to_previous.length > 0 && (
          <Section title="Connected Entries">
            <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
              {analysis.connections_to_previous.map((uuid) => (
                <button
                  key={uuid}
                  onClick={() => router.push(`/journal/${uuid}`)}
                  style={{
                    background: "rgba(139,92,246,0.06)",
                    border: "1px solid rgba(139,92,246,0.2)",
                    borderRadius: 8, padding: "8px 14px",
                    cursor: "pointer", textAlign: "left",
                    color: "#c4b5fd", fontSize: 12,
                    fontFamily: "monospace",
                    transition: "background 0.15s",
                  }}
                  onMouseEnter={(e) => (e.currentTarget.style.background = "rgba(139,92,246,0.12)")}
                  onMouseLeave={(e) => (e.currentTarget.style.background = "rgba(139,92,246,0.06)")}
                >
                  → {uuid}
                </button>
              ))}
            </div>
          </Section>
        )}

        {/* Integration guidance (if risk was assessed) */}
        {entry.integration_guidance && (
          <Section title="Integration Guidance" accent="#f87171">
            <p style={{
              fontSize: 13, color: "var(--text-secondary)", lineHeight: 1.7, margin: 0,
              padding: "14px 16px", borderRadius: 10,
              background: "rgba(248,113,113,0.06)", border: "1px solid rgba(248,113,113,0.15)",
            }}>
              {entry.integration_guidance}
            </p>
          </Section>
        )}

      </div>

      <style>{`@keyframes pulse { 0%, 100% { opacity: 1; } 50% { opacity: 0.3; } }`}</style>
    </div>
  );
}
