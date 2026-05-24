"use client";

import { useState } from "react";
import { api, type Entry, type AmplificationQuestion } from "@/lib/api";

interface Props {
  onComplete: (entry: Entry) => void;
}

const TYPES = [
  { value: "dream",       label: "Dream",       icon: "🌙", desc: "Sleep visions & nocturnal imagery" },
  { value: "psychedelic", label: "Psychedelic",  icon: "🌀", desc: "Expanded states & visionary experience" },
  { value: "meditation",  label: "Meditation",   icon: "◎",  desc: "Inner observation & stillness" },
] as const;

const MAX_CHARS = 5000;

export default function EntryForm({ onComplete }: Props) {
  // Step machine: "input" | "amplify"
  const [step, setStep] = useState<"input" | "amplify">("input");
  const [entryType, setEntryType] = useState<string>("dream");
  const [text, setText] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState(false);

  // Amplification state
  const [entryId, setEntryId] = useState<string | null>(null);
  const [questions, setQuestions] = useState<AmplificationQuestion[]>([]);
  const [associations, setAssociations] = useState<Record<string, string>>({});

  async function handleInitialSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!text.trim()) return;

    setLoading(true);
    setError(null);

    try {
      // Step 1: Submit raw text
      const result = await api.entries.create({
        raw_text: text.trim(),
        entry_type: entryType,
      });

      setEntryId(result.entry_id);

      if (result.amplification_questions && result.amplification_questions.length > 0) {
        setQuestions(result.amplification_questions);
        // Pre-fill association inputs
        const initialAssoc: Record<string, string> = {};
        result.amplification_questions.forEach((q) => {
          initialAssoc[q.symbol] = "";
        });
        setAssociations(initialAssoc);
        setStep("amplify");
      } else {
        // No questions, proceed directly to complete the analysis with empty associations
        const finalEntry = await api.entries.amplify({
          entry_id: result.entry_id,
          personal_associations: {},
        });
        onComplete(finalEntry);
        resetForm();
      }
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Something went wrong");
    } finally {
      setLoading(false);
    }
  }

  async function handleAmplifySubmit(skip: boolean) {
    if (!entryId) return;

    setLoading(true);
    setError(null);

    try {
      const finalAssociations = skip ? {} : associations;
      const finalEntry = await api.entries.amplify({
        entry_id: entryId,
        personal_associations: finalAssociations,
      });
      onComplete(finalEntry);
      resetForm();
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Something went wrong");
    } finally {
      setLoading(false);
    }
  }

  function resetForm() {
    setText("");
    setEntryId(null);
    setQuestions([]);
    setAssociations({});
    setStep("input");
    setSuccess(true);
    setTimeout(() => setSuccess(false), 3000);
  }

  const charCount = text.length;
  const charPct   = (charCount / MAX_CHARS) * 100;
  const nearLimit = charPct > 80;

  if (step === "amplify") {
    return (
      <div style={{ display: "flex", flexDirection: "column", gap: 24 }} className="animate-fade-in">
        <div style={{ paddingBottom: 16, borderBottom: "1px solid var(--border-subtle)" }}>
          <h3 style={{ fontSize: 16, fontWeight: 600, color: "#c4b5fd", margin: "0 0 6px" }}>
            Personal Amplification
          </h3>
          <p style={{ fontSize: 13, color: "var(--text-muted)", margin: 0, lineHeight: 1.5 }}>
            To map your psyche accurately, we query your personal associations.
            Archetypal default definitions are only applied when your own associations are absent.
          </p>
        </div>

        <div style={{ display: "flex", flexDirection: "column", gap: 20 }}>
          {questions.map((q) => (
            <div key={q.symbol} style={{ display: "flex", flexDirection: "column", gap: 8 }}>
              <label style={{ fontSize: 13, fontWeight: 600, color: "var(--text-secondary)" }}>
                Symbol: <span style={{ color: "#c4b5fd" }}>&quot;{q.symbol}&quot;</span>
              </label>
              <p style={{ fontSize: 12, color: "var(--text-muted)", margin: "0 0 4px", fontStyle: "italic" }}>
                {q.question}
              </p>
              <input
                type="text"
                className="input-dark"
                placeholder="What is your immediate association, history, or memory with this symbol?"
                value={associations[q.symbol] || ""}
                onChange={(e) =>
                  setAssociations((prev) => ({ ...prev, [q.symbol]: e.target.value }))
                }
                disabled={loading}
                style={{ fontSize: 13 }}
              />
            </div>
          ))}
        </div>

        {error && (
          <p style={{
            color: "#f87171", fontSize: 13, padding: "10px 14px",
            background: "rgba(248,113,113,0.1)", borderRadius: 8,
            border: "1px solid rgba(248,113,113,0.3)",
            margin: 0
          }}>
            {error}
          </p>
        )}

        <div style={{ display: "flex", gap: 12, marginTop: 8 }}>
          <button
            type="button"
            className="btn-primary"
            onClick={() => handleAmplifySubmit(false)}
            disabled={loading}
            style={{ flex: 1, minWidth: 150 }}
          >
            {loading ? "Analysing with Gemma..." : "Submit & Interpret"}
          </button>
          <button
            type="button"
            onClick={() => handleAmplifySubmit(true)}
            disabled={loading}
            style={{
              flex: 1,
              padding: "10px 16px",
              borderRadius: 8,
              border: "1px solid var(--border-subtle)",
              background: "rgba(255,255,255,0.02)",
              color: "var(--text-secondary)",
              cursor: "pointer",
              transition: "all 0.2s"
            }}
            onMouseEnter={(e) => (e.currentTarget.style.background = "rgba(255,255,255,0.05)")}
            onMouseLeave={(e) => (e.currentTarget.style.background = "rgba(255,255,255,0.02)")}
          >
            Skip to Defaults
          </button>
        </div>
      </div>
    );
  }

  return (
    <form onSubmit={handleInitialSubmit} style={{ display: "flex", flexDirection: "column", gap: 20 }}>

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
        {loading ? "Querying unconscious..." : "Record entry"}
      </button>
    </form>
  );
}
