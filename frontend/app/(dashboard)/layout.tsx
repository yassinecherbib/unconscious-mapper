import { redirect } from "next/navigation";
import Link from "next/link";
import { createClient } from "@/lib/supabase/server";

const NAV_ITEMS = [
  { href: "/journal", label: "Journal",    icon: "✦" },
  { href: "/map",     label: "Symbol Map",  icon: "◈" },
  { href: "/chat",    label: "Inner Voice", icon: "◎" },
];

export default async function DashboardLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  const supabase = await createClient();
  const { data: { user } } = await supabase.auth.getUser();

  if (!user) redirect("/login");

  // Fetch profile for unlock progress indicator in sidebar
  const { data: profile } = await supabase
    .from("profiles")
    .select("entry_count, chat_unlocked")
    .eq("id", user.id)
    .single();

  const entryCount   = profile?.entry_count   ?? 0;
  const chatUnlocked = profile?.chat_unlocked  ?? false;
  const progress     = Math.min((entryCount / 7) * 100, 100);

  async function signOut() {
    "use server";
    const sb = await createClient();
    await sb.auth.signOut();
    redirect("/login");
  }

  return (
    <div style={{ display: "flex", minHeight: "100vh" }}>
      {/* ── Sidebar ──────────────────────────────────────────── */}
      <aside style={{
        width: 220,
        flexShrink: 0,
        padding: "28px 16px",
        display: "flex",
        flexDirection: "column",
        borderRight: "1px solid var(--border-subtle)",
        background: "rgba(7,7,15,0.7)",
        backdropFilter: "blur(12px)",
        position: "sticky",
        top: 0,
        height: "100vh",
      }}>
        {/* Brand */}
        <div style={{ padding: "0 8px 28px", borderBottom: "1px solid var(--border-subtle)" }}>
          <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
            <span style={{ fontSize: 22 }}>◎</span>
            <div>
              <div style={{ fontSize: 13, fontWeight: 700, color: "var(--text-primary)", lineHeight: 1.2 }}>Unconscious</div>
              <div style={{ fontSize: 11, color: "var(--text-muted)" }}>Mind Mapper</div>
            </div>
          </div>
        </div>

        {/* Nav links */}
        <nav style={{ display: "flex", flexDirection: "column", gap: 4, marginTop: 20, flex: 1 }}>
          {NAV_ITEMS.map(({ href, label, icon }) => (
            <Link key={href} href={href} className="nav-link">
              <span style={{ fontSize: 16, width: 20, textAlign: "center" }}>{icon}</span>
              <span>{label}</span>
              {href === "/chat" && !chatUnlocked && (
                <span style={{
                  marginLeft: "auto", fontSize: 10, padding: "2px 6px",
                  borderRadius: 4, background: "var(--neon-dim)",
                  color: "var(--text-muted)",
                }}>
                  locked
                </span>
              )}
            </Link>
          ))}
        </nav>

        {/* Unlock progress */}
        {!chatUnlocked && (
          <div style={{ padding: "16px 8px", borderTop: "1px solid var(--border-subtle)" }}>
            <div style={{ display: "flex", justifyContent: "space-between", marginBottom: 6 }}>
              <span style={{ fontSize: 11, color: "var(--text-muted)" }}>Unlock progress</span>
              <span style={{ fontSize: 11, color: "#a78bfa" }}>{entryCount}/7</span>
            </div>
            <div className="progress-bar">
              <div className="progress-bar-fill" style={{ width: `${progress}%` }} />
            </div>
            <p style={{ fontSize: 10, color: "var(--text-muted)", marginTop: 6, lineHeight: 1.4 }}>
              7 entries across 7 days to unlock Inner Voice
            </p>
          </div>
        )}

        {/* User + sign out */}
        <div style={{ paddingTop: 16, borderTop: "1px solid var(--border-subtle)" }}>
          <p style={{ fontSize: 11, color: "var(--text-muted)", padding: "0 8px", marginBottom: 8, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>
            {user.email}
          </p>
          <form action={signOut}>
            <button type="submit" className="btn-ghost" style={{ width: "100%", fontSize: 12, padding: "8px 14px" }}>
              Sign out
            </button>
          </form>
        </div>
      </aside>

      {/* ── Main content ──────────────────────────────────────── */}
      <main style={{ flex: 1, overflowY: "auto", padding: "40px 48px" }}>
        {children}
      </main>
    </div>
  );
}
