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

// ── section card wrapper ──────────────────────────────────────────────────────

function Section({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <section className="glass-card" style={{ padding: "24px 28px" }}>
      <h2 style={{
        fontSize: 11, fontWeight: 700, letterSpacing: "0.1em",
        textTransform: "uppercase", color: "var(--text-muted)",
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

        {/* Integration Risk Banner */}
        {analysis?.integration_risk && analysis.integration_risk.overall_risk_level !== "none" && (
          <section className="glass-card animate-fade-up" style={{
            padding: "24px 28px",
            border: `1px solid ${
              analysis.integration_risk.overall_risk_level === "high"
                ? "rgba(239, 68, 68, 0.4)"
                : analysis.integration_risk.overall_risk_level === "moderate"
                ? "rgba(245, 158, 11, 0.4)"
                : "rgba(99, 102, 241, 0.4)"
            }`,
            background: `${
              analysis.integration_risk.overall_risk_level === "high"
                ? "rgba(239, 68, 68, 0.04)"
                : analysis.integration_risk.overall_risk_level === "moderate"
                ? "rgba(245, 158, 11, 0.04)"
                : "rgba(99, 102, 241, 0.04)"
            }`,
          }}>
            <div style={{ display: "flex", alignItems: "center", gap: 10, marginBottom: 16 }}>
              <span style={{
                fontSize: 16,
                color: 
                  analysis.integration_risk.overall_risk_level === "high"
                    ? "#ef4444"
                    : analysis.integration_risk.overall_risk_level === "moderate"
                    ? "#f59e0b"
                    : "#6366f1"
              }}>
                ⚠️
              </span>
              <h2 style={{
                fontSize: 11, fontWeight: 700, letterSpacing: "0.1em",
                textTransform: "uppercase", 
                color: 
                  analysis.integration_risk.overall_risk_level === "high"
                    ? "#ef4444"
                    : analysis.integration_risk.overall_risk_level === "moderate"
                    ? "#f59e0b"
                    : "#818cf8",
                margin: 0,
              }}>
                Clinical Integration Advisory — {analysis.integration_risk.overall_risk_level} Risk
              </h2>
            </div>

            <div style={{ display: "flex", flexDirection: "column", gap: 14 }}>
              {/* Flags check */}
              {Object.entries({
                "Spiritual Inflation": analysis.integration_risk.spiritual_inflation,
                "Ego Dissolution": analysis.integration_risk.ego_dissolution_without_regrounding,
                "Shadow Bypassing": analysis.integration_risk.shadow_bypassing,
                "Premature Closure": analysis.integration_risk.premature_closure
              }).map(([label, flag]) => {
                if (!flag || !flag.present) return null;
                return (
                  <div key={label} style={{
                    padding: "12px 16px",
                    borderRadius: 10,
                    background: "rgba(0,0,0,0.2)",
                    border: "1px solid rgba(255,255,255,0.04)"
                  }}>
                    <div style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: 4 }}>
                      <span style={{ fontSize: 13, fontWeight: 600, color: "#f87171" }}>
                        ✦ {label}
                      </span>
                      {flag.severity && (
                        <span style={{
                          fontSize: 9, padding: "1px 5px", borderRadius: 4,
                          background: flag.severity === "high" ? "rgba(239,68,68,0.2)" : "rgba(245,158,11,0.2)",
                          color: flag.severity === "high" ? "#f87171" : "#fbbf24",
                          fontWeight: 600,
                          textTransform: "uppercase"
                        }}>
                          {flag.severity}
                        </span>
                      )}
                      {/* Form check for shadow bypassing */}
                      {"form" in flag && flag.form && (
                        <span style={{
                          fontSize: 9, padding: "1px 5px", borderRadius: 4,
                          background: "rgba(139,92,246,0.15)",
                          color: "#c4b5fd"
                        }}>
                          form: {flag.form}
                        </span>
                      )}
                    </div>
                    {flag.evidence && (
                      <p style={{ fontSize: 12, color: "var(--text-secondary)", margin: 0, lineHeight: 1.5 }}>
                        <strong style={{ color: "var(--text-muted)" }}>Evidence:</strong> {flag.evidence}
                      </p>
                    )}
                  </div>
                );
              })}

              {/* Guidance */}
              <div style={{
                marginTop: 6,
                paddingTop: 14,
                borderTop: "1px solid rgba(255,255,255,0.06)"
              }}>
                <p style={{ fontSize: 11, fontWeight: 700, textTransform: "uppercase", color: "var(--text-muted)", margin: "0 0 6px", letterSpacing: "0.05em" }}>
                  Regrounding & Integration Guidance
                </p>
                <p style={{ fontSize: 13, color: "var(--text-primary)", lineHeight: 1.7, margin: 0 }}>
                  {analysis.integration_risk.integration_guidance}
                </p>
              </div>
            </div>
          </section>
        )}

        {/* Ego Strength Section */}
        {analysis?.ego_strength_signal !== undefined && (
          <Section title="Ego Strength Signal">
            <div style={{ display: "flex", flexDirection: "column", gap: 16 }}>
              <div style={{ display: "flex", gap: 6, width: "100%" }}>
                {[1, 2, 3, 4, 5, 6].map((lvl) => {
                  const isActive = (analysis.ego_strength_signal ?? 0) >= lvl;
                  const isExact = analysis.ego_strength_signal === lvl;
                  return (
                    <div
                      key={lvl}
                      style={{
                        flex: 1,
                        height: 12,
                        borderRadius: 4,
                        background: isExact
                          ? "linear-gradient(90deg, var(--neon-cyan), var(--neon-pulse))"
                          : isActive
                          ? "var(--neon-violet)"
                          : "rgba(255,255,255,0.06)",
                        border: isExact ? "1px solid #fff" : "1px solid transparent",
                        boxShadow: isExact ? "0 0 12px var(--neon-pulse)" : "none",
                        transition: "all 0.4s ease",
                      }}
                    />
                  );
                })}
              </div>
              <div>
                <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 6 }}>
                  <span style={{ fontSize: 14, fontWeight: 600, color: "#22d3ee" }}>
                    Stage {analysis.ego_strength_signal}: {[
                      "Absent (Pure Observation)",
                      "Passive / Overwhelmed",
                      "Failing to Act",
                      "Holding Ground",
                      "Engaging Confrontation",
                      "Integrating Resolving"
                    ][analysis.ego_strength_signal - 1] ?? ""}
                  </span>
                  <span style={{ fontSize: 11, color: "var(--text-muted)", letterSpacing: "0.05em", textTransform: "uppercase" }}>
                    Ego-Unconscious Boundary
                  </span>
                </div>
                <p style={{ fontSize: 13, color: "var(--text-secondary)", margin: 0, lineHeight: 1.6 }}>
                  {[
                    "Pure observation with no active dream-ego presence or choices.",
                    "Ego is paralyzed, fleeing, or completely overwhelmed by unconscious content.",
                    "Ego attempts to take action but fails, remains unprepared, or lacks agency.",
                    "Ego maintains presence, boundary, and containment under high psychological pressure.",
                    "Ego actively confronts, questions, dialogues, or makes conscious choices during the experience.",
                    "Ego successfully resolves structural conflicts, receives symbols, or collaborates with the unconscious."
                  ][analysis.ego_strength_signal - 1] ?? ""}
                </p>
              </div>
            </div>
          </Section>
        )}

        {/* Lysis / Compensation Panel */}
        {((entry.entry_type === "dream" && analysis?.lysis_assessment) || analysis?.compensation_axis) && (
          <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(280px, 1fr))", gap: 20 }}>
            {entry.entry_type === "dream" && analysis?.lysis_assessment && (
              <Section title="Dream Structural Resolution (Lysis)">
                <div style={{ display: "flex", flexDirection: "column", gap: 12 }}>
                  <div>
                    <span style={{
                      display: "inline-block",
                      fontSize: 11,
                      fontWeight: 700,
                      textTransform: "uppercase",
                      padding: "4px 10px",
                      borderRadius: 8,
                      letterSpacing: "0.05em",
                      background: 
                        analysis.lysis_assessment === "resolved" 
                          ? "rgba(16,185,129,0.15)" 
                          : analysis.lysis_assessment === "unresolved" 
                          ? "rgba(239,68,68,0.15)" 
                          : "rgba(245,158,11,0.15)",
                      color: 
                        analysis.lysis_assessment === "resolved" 
                          ? "#34d399" 
                          : analysis.lysis_assessment === "unresolved" 
                          ? "#f87171" 
                          : "#fbbf24",
                      border: 
                        analysis.lysis_assessment === "resolved" 
                          ? "1px solid rgba(16,185,129,0.3)" 
                          : analysis.lysis_assessment === "unresolved" 
                          ? "1px solid rgba(239,68,68,0.3)" 
                          : "1px solid rgba(245,158,11,0.3)",
                      boxShadow: 
                        analysis.lysis_assessment === "resolved"
                          ? "0 0 10px rgba(16,185,129,0.1)"
                          : "none"
                    }}>
                      {analysis.lysis_assessment}
                    </span>
                  </div>
                  <p style={{ fontSize: 13, color: "var(--text-secondary)", lineHeight: 1.6, margin: 0 }}>
                    {analysis.lysis_assessment === "resolved" && (
                      "The dream reaches a structural resolution, indicating the conscious ego successfully metabolizes or integrates this unconscious message."
                    )}
                    {analysis.lysis_assessment === "unresolved" && (
                      "The dream ends in suspended action, threat, or interruption, suggesting an active psychic conflict or complex requiring deeper conscious containment."
                    )}
                    {analysis.lysis_assessment === "ambiguous" && (
                      "The structural resolution is transitional or open-ended. The symbol system is in flux, representing an unfolding integration process."
                    )}
                  </p>
                </div>
              </Section>
            )}

            {analysis?.compensation_axis && (
              <Section title="Psychic Compensation Axis">
                <div style={{
                  borderLeft: "3px solid var(--neon-violet)",
                  paddingLeft: 16,
                  display: "flex",
                  flexDirection: "column",
                  gap: 6
                }}>
                  <p style={{
                    fontSize: 13,
                    color: "#c4b5fd",
                    lineHeight: 1.6,
                    margin: 0,
                    fontStyle: "italic"
                  }}>
                    “{analysis.compensation_axis}”
                  </p>
                  <span style={{ fontSize: 10, color: "var(--text-muted)", textTransform: "uppercase", letterSpacing: "0.05em" }}>
                    {"Psyche's correction to conscious one-sidedness"}
                  </span>
                </div>
              </Section>
            )}
          </div>
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

      </div>

      <style>{`@keyframes pulse { 0%, 100% { opacity: 1; } 50% { opacity: 0.3; } }`}</style>
    </div>
  );
}
