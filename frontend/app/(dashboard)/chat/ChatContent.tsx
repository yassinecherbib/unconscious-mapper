"use client";

import { useState, useRef, useEffect } from "react";
import { useSearchParams } from "next/navigation";
import { api } from "@/lib/api";

interface ChatMsg {
  role: "user" | "assistant" | "system";
  content: string;
  timestamp: number;
}

function formatTime(ts: number) {
  return new Date(ts).toLocaleTimeString("en-GB", {
    hour: "2-digit",
    minute: "2-digit",
  });
}

export default function ChatContent() {
  const searchParams = useSearchParams();
  const seedEntryId = searchParams.get("entry");

  const [messages, setMessages] = useState<ChatMsg[]>([]);
  const [input, setInput] = useState("");
  const [streaming, setStreaming] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [unlocked, setUnlocked] = useState<boolean | null>(null);
  const scrollRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLTextAreaElement>(null);

  // Check unlock status on mount
  useEffect(() => {
    api.unlock
      .progress()
      .then((p) => setUnlocked(p.unlocked))
      .catch(() => setUnlocked(false));
  }, []);

  // Auto-scroll on new messages
  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }
  }, [messages]);

  // If entry-anchored, add system context note
  useEffect(() => {
    if (seedEntryId && messages.length === 0) {
      setMessages([
        {
          role: "system",
          content: `Session anchored to entry ${seedEntryId.slice(0, 8)}… — the AI will draw from that entry's symbolic context.`,
          timestamp: Date.now(),
        },
      ]);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [seedEntryId]);

  async function sendMessage() {
    const text = input.trim();
    if (!text || streaming) return;

    setInput("");
    setError(null);

    const userMsg: ChatMsg = {
      role: "user",
      content: text,
      timestamp: Date.now(),
    };
    setMessages((prev) => [...prev, userMsg]);

    // Add placeholder for assistant
    const assistantMsg: ChatMsg = {
      role: "assistant",
      content: "",
      timestamp: Date.now(),
    };
    setMessages((prev) => [...prev, assistantMsg]);
    setStreaming(true);

    try {
      const reader = await api.chat.stream(
        text,
        seedEntryId ?? undefined
      );
      const decoder = new TextDecoder();

      while (true) {
        const { value, done } = await reader.read();
        if (done) break;

        const chunk = decoder.decode(value);
        // Parse SSE lines
        const lines = chunk.split("\n");
        for (const line of lines) {
          if (line.startsWith("data: ")) {
            const payload = line.slice(6);
            if (payload === "[DONE]") continue;
            if (payload.startsWith("[ERROR]")) {
              setError(payload.slice(8));
              continue;
            }
            // Append text to last assistant message
            setMessages((prev) => {
              const updated = [...prev];
              const last = updated[updated.length - 1];
              if (last?.role === "assistant") {
                updated[updated.length - 1] = {
                  ...last,
                  content: last.content + payload,
                };
              }
              return updated;
            });
          }
        }
      }
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : "Connection failed";
      setError(msg);
      // Remove empty assistant placeholder on error
      setMessages((prev) => {
        const last = prev[prev.length - 1];
        if (last?.role === "assistant" && !last.content) {
          return prev.slice(0, -1);
        }
        return prev;
      });
    } finally {
      setStreaming(false);
      inputRef.current?.focus();
    }
  }

  function handleKeyDown(e: React.KeyboardEvent<HTMLTextAreaElement>) {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      sendMessage();
    }
  }

  // ── Locked state ──
  if (unlocked === false) {
    return (
      <div style={{ maxWidth: 720, margin: "0 auto" }}>
        <header style={{ marginBottom: 40 }}>
          <h1
            style={{
              fontSize: 28,
              fontWeight: 700,
              margin: 0,
              background: "linear-gradient(135deg, #e2e8f0 0%, #c084fc 100%)",
              WebkitBackgroundClip: "text",
              WebkitTextFillColor: "transparent",
              backgroundClip: "text",
            }}
          >
            Inner Voice
          </h1>
          <p style={{ color: "var(--text-muted)", fontSize: 14, marginTop: 6 }}>
            Your unconscious speaks back — grounded in your own symbolic history.
          </p>
        </header>

        <div
          className="glass-card"
          style={{
            display: "flex",
            flexDirection: "column",
            alignItems: "center",
            justifyContent: "center",
            padding: "80px 40px",
            textAlign: "center",
            border: "1px dashed var(--border-subtle)",
          }}
        >
          <div className="animate-float" style={{ fontSize: 48, marginBottom: 20 }}>◎</div>
          <p style={{ fontSize: 16, fontWeight: 600, color: "var(--text-secondary)" }}>
            Inner Voice is Locked
          </p>
          <p style={{ fontSize: 13, color: "var(--text-muted)", maxWidth: 420, marginTop: 8, lineHeight: 1.6 }}>
            Submit at least 7 journal entries across 7 days to unlock the
            topology retrieval engine. Your symbols become the retrieval
            index — the AI speaks from within your own symbolic world.
          </p>
        </div>
      </div>
    );
  }

  // ── Loading unlock check ──
  if (unlocked === null) {
    return (
      <div style={{ display: "flex", alignItems: "center", justifyContent: "center", height: "60vh" }}>
        <div style={{
          width: 32, height: 32, borderRadius: "50%",
          border: "2px solid var(--neon-violet)", borderTopColor: "transparent",
          animation: "spin 1s linear infinite",
        }} />
        <style>{`@keyframes spin { to { transform: rotate(360deg); } }`}</style>
      </div>
    );
  }

  // ── Chat UI ──
  return (
    <div style={{
      display: "flex", flexDirection: "column",
      height: "calc(100vh - 80px)", maxWidth: 800, margin: "0 auto",
    }}>
      {/* Header */}
      <header style={{ flexShrink: 0, marginBottom: 16 }}>
        <h1 style={{
          fontSize: 22, fontWeight: 700, margin: 0,
          background: "linear-gradient(135deg, #e2e8f0 0%, #c084fc 100%)",
          WebkitBackgroundClip: "text",
          WebkitTextFillColor: "transparent",
          backgroundClip: "text",
        }}>
          Inner Voice
        </h1>
        <p style={{ color: "var(--text-muted)", fontSize: 13, margin: "4px 0 0" }}>
          {seedEntryId
            ? `Anchored to entry ${seedEntryId.slice(0, 8)}… — context-aware dialogue`
            : "Topology-aware dialogue grounded in your symbolic history"}
        </p>
      </header>

      {/* Messages area */}
      <div
        ref={scrollRef}
        className="glass-card"
        style={{
          flex: 1, overflowY: "auto", padding: "24px 28px",
          display: "flex", flexDirection: "column", gap: 20, marginBottom: 16,
        }}
      >
        {messages.length === 0 && (
          <div style={{
            flex: 1, display: "flex", flexDirection: "column",
            alignItems: "center", justifyContent: "center", gap: 12, opacity: 0.6,
          }}>
            <div style={{ fontSize: 36 }}>◎</div>
            <p style={{
              fontSize: 14, color: "var(--text-muted)", textAlign: "center",
              maxWidth: 360, lineHeight: 1.6,
            }}>
              Ask about your symbols, dreams, or patterns. The AI draws
              from your personal symbolic history — not generic data.
            </p>
            <div style={{
              display: "flex", flexWrap: "wrap", gap: 8, marginTop: 8, justifyContent: "center",
            }}>
              {[
                "What patterns do you see in my dreams?",
                "Tell me about my shadow material",
                "What is my psyche compensating for?",
              ].map((q) => (
                <button
                  key={q}
                  onClick={() => {
                    setInput(q);
                    inputRef.current?.focus();
                  }}
                  style={{
                    background: "rgba(139,92,246,0.08)",
                    border: "1px solid rgba(139,92,246,0.2)",
                    borderRadius: 20, padding: "6px 14px",
                    color: "#c4b5fd", fontSize: 12, cursor: "pointer",
                    transition: "all 0.15s",
                  }}
                  onMouseEnter={(e) => (e.currentTarget.style.background = "rgba(139,92,246,0.15)")}
                  onMouseLeave={(e) => (e.currentTarget.style.background = "rgba(139,92,246,0.08)")}
                >
                  {q}
                </button>
              ))}
            </div>
          </div>
        )}

        {messages.map((msg, i) => (
          <div
            key={i}
            style={{
              display: "flex", flexDirection: "column",
              alignItems: msg.role === "user" ? "flex-end" : "flex-start",
            }}
          >
            {/* Role label */}
            <span style={{
              fontSize: 10, fontWeight: 600, letterSpacing: "0.08em",
              textTransform: "uppercase", marginBottom: 4,
              color: msg.role === "user" ? "#a78bfa" : msg.role === "system" ? "#94a3b8" : "#c084fc",
            }}>
              {msg.role === "user" ? "You" : msg.role === "system" ? "System" : "Inner Voice"}
            </span>

            {/* Message bubble */}
            <div style={{
              maxWidth: "85%", padding: "12px 16px",
              borderRadius: msg.role === "user" ? "16px 16px 4px 16px" : "16px 16px 16px 4px",
              background: msg.role === "user"
                ? "rgba(139,92,246,0.15)"
                : msg.role === "system"
                  ? "rgba(148,163,184,0.08)"
                  : "rgba(192,132,252,0.08)",
              border: msg.role === "user"
                ? "1px solid rgba(139,92,246,0.25)"
                : msg.role === "system"
                  ? "1px solid rgba(148,163,184,0.15)"
                  : "1px solid rgba(192,132,252,0.15)",
            }}>
              <p style={{
                fontSize: 14, lineHeight: 1.7, margin: 0, whiteSpace: "pre-wrap",
                color: msg.role === "system" ? "var(--text-muted)" : "var(--text-secondary)",
              }}>
                {msg.content}
                {streaming && i === messages.length - 1 && msg.role === "assistant" && (
                  <span style={{
                    display: "inline-block", width: 6, height: 14,
                    background: "#c084fc", marginLeft: 2,
                    animation: "blink 1s step-end infinite",
                    verticalAlign: "text-bottom",
                  }} />
                )}
              </p>
            </div>

            {/* Timestamp */}
            <span style={{ fontSize: 10, color: "var(--text-muted)", marginTop: 3, opacity: 0.6 }}>
              {formatTime(msg.timestamp)}
            </span>
          </div>
        ))}
      </div>

      {/* Error */}
      {error && (
        <div style={{
          padding: "8px 14px", background: "rgba(248,113,113,0.1)",
          border: "1px solid rgba(248,113,113,0.3)", borderRadius: 8, marginBottom: 12,
        }}>
          <p style={{ color: "#f87171", fontSize: 12, margin: 0 }}>⚠ {error}</p>
        </div>
      )}

      {/* Input area */}
      <div className="glass-card" style={{
        flexShrink: 0, padding: "16px 20px",
        display: "flex", gap: 12, alignItems: "flex-end",
      }}>
        <textarea
          ref={inputRef}
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={handleKeyDown}
          placeholder="Ask about your symbols, patterns, or inner world…"
          rows={1}
          disabled={streaming}
          style={{
            flex: 1, background: "rgba(7,7,15,0.6)",
            border: "1px solid var(--border-subtle)", borderRadius: 12,
            padding: "12px 16px", color: "var(--text-secondary)",
            fontSize: 14, fontFamily: "inherit", lineHeight: 1.5,
            resize: "none", outline: "none", transition: "border-color 0.2s",
            maxHeight: 120, overflow: "auto",
          }}
          onFocus={(e) => (e.currentTarget.style.borderColor = "rgba(139,92,246,0.5)")}
          onBlur={(e) => (e.currentTarget.style.borderColor = "var(--border-subtle)")}
        />
        <button
          onClick={sendMessage}
          disabled={streaming || !input.trim()}
          style={{
            background: streaming
              ? "rgba(139,92,246,0.1)"
              : "linear-gradient(135deg, #7c3aed, #a855f7)",
            border: "none", borderRadius: 12,
            padding: "12px 20px", color: "#fff",
            fontSize: 14, fontWeight: 600,
            cursor: streaming || !input.trim() ? "not-allowed" : "pointer",
            opacity: streaming || !input.trim() ? 0.5 : 1,
            transition: "all 0.2s", whiteSpace: "nowrap",
          }}
        >
          {streaming ? "◎ …" : "Send"}
        </button>
      </div>

      <style>{`
        @keyframes blink { 50% { opacity: 0; } }
        @keyframes spin { to { transform: rotate(360deg); } }
      `}</style>
    </div>
  );
}
