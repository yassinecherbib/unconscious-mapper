/**
 * Inner Voice (chat) page — Phase 4 placeholder.
 * Will render the topology-aware SSE chat interface.
 */
export default function ChatPage() {
  return (
    <div style={{ maxWidth: 720, margin: "0 auto" }}>
      <header style={{ marginBottom: 40 }}>
        <h1 style={{
          fontSize: 28, fontWeight: 700, margin: 0,
          background: "linear-gradient(135deg, #e2e8f0 0%, #c084fc 100%)",
          WebkitBackgroundClip: "text",
          WebkitTextFillColor: "transparent",
          backgroundClip: "text",
        }}>
          Inner Voice
        </h1>
        <p style={{ color: "var(--text-muted)", fontSize: 14, marginTop: 6 }}>
          Your unconscious speaks back — grounded in your own symbolic history.
        </p>
      </header>

      <div className="glass-card" style={{
        display: "flex", flexDirection: "column", alignItems: "center",
        justifyContent: "center", padding: "80px 40px", textAlign: "center",
        border: "1px dashed var(--border-subtle)",
      }}>
        <div className="animate-float" style={{ fontSize: 48, marginBottom: 20 }}>◎</div>
        <p style={{ fontSize: 16, fontWeight: 600, color: "var(--text-secondary)" }}>
          Coming in Phase 4
        </p>
        <p style={{ fontSize: 13, color: "var(--text-muted)", maxWidth: 420, marginTop: 8, lineHeight: 1.6 }}>
          After 7 entries across 7 days, the topology retrieval engine activates.
          Your symbols become the retrieval index — the AI speaks from within your
          own symbolic world, not from generic data.
        </p>
      </div>
    </div>
  );
}
