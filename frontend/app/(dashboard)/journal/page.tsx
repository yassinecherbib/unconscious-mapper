"use client";

import { useState, useEffect, useCallback } from "react";
import EntryForm from "@/app/components/EntryForm";
import EntryCard from "@/app/components/EntryCard";
import { api, type Entry } from "@/lib/api";

export default function JournalPage() {
  const [entries, setEntries]   = useState<Entry[]>([]);
  const [loading, setLoading]   = useState(true);
  const [error, setError]       = useState<string | null>(null);

  const fetchEntries = useCallback(async () => {
    try {
      const data = await api.entries.list();
      setEntries(data);
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Failed to load entries");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchEntries();
  }, [fetchEntries]);

  async function handleNewEntry(data: { raw_text: string; entry_type: string }) {
    const entry = await api.entries.create(data);
    setEntries((prev) => [entry, ...prev]);
  }

  return (
    <div style={{ maxWidth: 760, margin: "0 auto" }}>

      {/* Page header */}
      <header style={{ marginBottom: 40 }}>
        <h1 style={{
          fontSize: 28, fontWeight: 700, margin: 0,
          background: "linear-gradient(135deg, #e2e8f0 0%, #a78bfa 100%)",
          WebkitBackgroundClip: "text",
          WebkitTextFillColor: "transparent",
          backgroundClip: "text",
        }}>
          Dream Journal
        </h1>
        <p style={{ color: "var(--text-muted)", fontSize: 14, marginTop: 6 }}>
          Record your inner experiences. Each entry deepens the map.
        </p>
      </header>

      {/* Entry form */}
      <section className="glass-card" style={{ padding: "28px 32px", marginBottom: 36 }}>
        <h2 style={{ fontSize: 14, fontWeight: 600, color: "var(--text-secondary)", margin: "0 0 20px", letterSpacing: "0.05em", textTransform: "uppercase" }}>
          New entry
        </h2>
        <EntryForm onSubmit={handleNewEntry} />
      </section>

      {/* Entry list */}
      <section>
        <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: 16 }}>
          <h2 style={{ fontSize: 14, fontWeight: 600, color: "var(--text-secondary)", margin: 0, letterSpacing: "0.05em", textTransform: "uppercase" }}>
            Past entries
          </h2>
          {entries.length > 0 && (
            <span style={{ fontSize: 12, color: "var(--text-muted)" }}>
              {entries.length} recorded
            </span>
          )}
        </div>

        {loading && (
          <div style={{ textAlign: "center", padding: "48px 0" }}>
            <div className="animate-neural" style={{
              width: 32, height: 32, borderRadius: "50%", margin: "0 auto",
              border: "2px solid var(--neon-violet)", borderTopColor: "transparent",
              animation: "spin 1s linear infinite",
            }} />
            <p style={{ color: "var(--text-muted)", fontSize: 13, marginTop: 12 }}>
              Reaching into the archive…
            </p>
          </div>
        )}

        {error && (
          <p style={{ color: "#f87171", fontSize: 14, padding: "16px", background: "rgba(248,113,113,0.1)", borderRadius: 10 }}>
            {error}
          </p>
        )}

        {!loading && !error && entries.length === 0 && (
          <div style={{
            textAlign: "center", padding: "64px 32px",
            border: "1px dashed var(--border-subtle)", borderRadius: 16,
          }}>
            <div className="animate-float" style={{ fontSize: 40, marginBottom: 16 }}>◎</div>
            <p style={{ color: "var(--text-secondary)", fontSize: 15, fontWeight: 500 }}>
              Your map is empty
            </p>
            <p style={{ color: "var(--text-muted)", fontSize: 13, marginTop: 6 }}>
              Write your first entry above to begin the mapping
            </p>
          </div>
        )}

        <div style={{ display: "flex", flexDirection: "column", gap: 14 }}>
          {entries.map((entry, i) => (
            <div
              key={entry.id}
              className="animate-fade-up"
              style={{ animationDelay: `${i * 50}ms` }}
            >
              <EntryCard entry={entry} />
            </div>
          ))}
        </div>
      </section>

      {/* Spin animation for loader */}
      <style>{`
        @keyframes spin { to { transform: rotate(360deg); } }
      `}</style>
    </div>
  );
}
