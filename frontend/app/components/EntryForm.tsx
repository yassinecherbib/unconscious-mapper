"use client";

import { useState } from "react";

interface Props {
  onSubmit: (data: { raw_text: string; entry_type: string }) => Promise<void>;
}

const TYPES = [
  { value: "dream",       label: "Dream",       icon: "🌙", desc: "Sleep visions & nocturnal imagery" },
  { value: "psychedelic", label: "Psychedelic",  icon: "🌀", desc: "Expanded states & visionary experience" },
  { value: "meditation",  label: "Meditation",   icon: "◎",  desc: "Inner observation & stillness" },
] as const;

const MAX_CHARS = 5000;

export default function EntryForm({ onSubmit }: Props) {
  const [entryType, setEntryType] = useState<string>("dream");
  const [text, setText] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState(false);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!text.trim()) return;

    setLoading(true);
    setError(null);
    setSuccess(false);

    try {
      await onSubmit({ raw_text: text.trim(), entry_type: entryType });
      setText("");
      setSuccess(true);
      setTimeout(() => setSuccess(false), 3000);
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Something went wrong");
    } finally {
      setLoading(false);
    }
  }

  const charCount = text.length;
  const charPct   = (charCount / MAX_CHARS) * 100;
  const nearLimit = charPct > 80;

  return (
    <form onSubmit={handleSubmit} style={{ display: "flex", flexDirection: "column", gap: 20 }}>

      {/* Type selector */}
      <div>
        <label style={{ display: "block", fontSize: 12, fontWeight: 600, color: "var(--text-muted)", letterSpacing: "0.08em", textTransform: "uppercase", marginBottom: 10 }}>
          Entry type
        </label>
        <div style={{ display: "grid", gridTemplateColumns: "repeat(3, 1fr)", gap: 10 }}>
          {TYPES.map(({ value, label, icon, desc }) => (
            <button
              key={value}
              type="button"
              id={`type-${value}`}
              onClick={() => setEntryType(value)}
              style={{
                padding: "14px 10px",
                borderRadius: 12,
                border: entryType === value ? "1px solid var(--border-active)" : "1px solid var(--border-subtle)",
                background: entryType === value ? "rgba(139,92,246,0.15)" : "rgba(7,7,15,0.5)",
                cursor: "pointer",
                textAlign: "left",
                transition: "all 0.2s",
              }}
            >
              <div style={{ fontSize: 20, marginBottom: 4 }}>{icon}</div>
              <div style={{ fontSize: 13, fontWeight: 600, color: entryType === value ? "#c4b5fd" : "var(--text-secondary)" }}>
                {label}
              </div>
              <div style={{ fontSize: 10, color: "var(--text-muted)", marginTop: 2, lineHeight: 1.3 }}>
                {desc}
              </div>
            </button>
          ))}
        </div>
      </div>

      {/* Text area */}
      <div>
        <label style={{ display: "block", fontSize: 12, fontWeight: 600, color: "var(--text-muted)", letterSpacing: "0.08em", textTransform: "uppercase", marginBottom: 10 }}>
          Describe your experience
        </label>
        <textarea
          id="entry-text"
          className="input-dark"
          rows={8}
          placeholder="Let the images surface. Write whatever comes — no editing, no censoring. The unconscious speaks in fragments…"
          value={text}
          onChange={(e) => setText(e.target.value)}
          maxLength={MAX_CHARS}
          required
          style={{ fontFamily: "inherit", lineHeight: 1.7, fontSize: 14 }}
        />
        {/* Character count */}
        <div style={{ display: "flex", justifyContent: "flex-end", marginTop: 6 }}>
          <span style={{ fontSize: 11, color: nearLimit ? "#f87171" : "var(--text-muted)" }}>
            {charCount.toLocaleString()} / {MAX_CHARS.toLocaleString()}
          </span>
        </div>
      </div>

      {error && (
        <p style={{
          color: "#f87171", fontSize: 13, padding: "10px 14px",
          background: "rgba(248,113,113,0.1)", borderRadius: 8,
          border: "1px solid rgba(248,113,113,0.3)",
        }}>
          {error}
        </p>
      )}

      {success && (
        <p style={{
          color: "#86efac", fontSize: 13, padding: "10px 14px",
          background: "rgba(134,239,172,0.1)", borderRadius: 8,
          border: "1px solid rgba(134,239,172,0.3)",
        }}>
          ✓ Entry recorded — the map grows
        </p>
      )}

      <button
        id="entry-submit"
        type="submit"
        className="btn-primary"
        disabled={loading || !text.trim()}
        style={{ alignSelf: "flex-start", minWidth: 160 }}
      >
        {loading ? "Analysing with Gemma…" : "Record entry"}
      </button>
    </form>
  );
}
