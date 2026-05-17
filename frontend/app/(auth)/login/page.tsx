"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { createClient } from "@/lib/supabase/client";

export default function LoginPage() {
  const router = useRouter();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  async function handleLogin(e: React.FormEvent) {
    e.preventDefault();
    setError(null);
    setLoading(true);

    const supabase = createClient();
    const { error: authError } = await supabase.auth.signInWithPassword({
      email,
      password,
    });

    if (authError) {
      setError(authError.message);
      setLoading(false);
      return;
    }

    router.push("/journal");
    router.refresh();
  }

  return (
    <main style={{ minHeight: "100vh", display: "flex", alignItems: "center", justifyContent: "center", padding: "24px" }}>
      <div className="glass-card animate-fade-up" style={{ width: "100%", maxWidth: "420px", padding: "48px 40px" }}>

        {/* Logo mark */}
        <div style={{ textAlign: "center", marginBottom: "32px" }}>
          <div style={{
            width: 56, height: 56, borderRadius: "50%", margin: "0 auto 16px",
            background: "radial-gradient(circle, rgba(139,92,246,0.4) 0%, rgba(34,211,238,0.1) 100%)",
            border: "1px solid var(--border-active)",
            display: "flex", alignItems: "center", justifyContent: "center",
            fontSize: 24,
          }}>
            ◎
          </div>
          <h1 style={{ fontSize: 22, fontWeight: 700, color: "var(--text-primary)", margin: 0 }}>
            Welcome back
          </h1>
          <p style={{ color: "var(--text-muted)", fontSize: 14, marginTop: 6 }}>
            Re-enter your inner world
          </p>
        </div>

        <form onSubmit={handleLogin} style={{ display: "flex", flexDirection: "column", gap: 16 }}>
          <div>
            <label style={{ display: "block", fontSize: 13, fontWeight: 500, color: "var(--text-secondary)", marginBottom: 6 }}>
              Email
            </label>
            <input
              id="email"
              type="email"
              className="input-dark"
              placeholder="you@example.com"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              required
              autoComplete="email"
            />
          </div>

          <div>
            <label style={{ display: "block", fontSize: 13, fontWeight: 500, color: "var(--text-secondary)", marginBottom: 6 }}>
              Password
            </label>
            <input
              id="password"
              type="password"
              className="input-dark"
              placeholder="••••••••"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              required
              autoComplete="current-password"
            />
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

          <button
            id="login-submit"
            type="submit"
            className="btn-primary"
            disabled={loading}
            style={{ marginTop: 8, width: "100%", textAlign: "center" }}
          >
            {loading ? "Entering the depths…" : "Sign in"}
          </button>
        </form>

        <p style={{ textAlign: "center", marginTop: 24, fontSize: 14, color: "var(--text-muted)" }}>
          No account?{" "}
          <Link href="/register" style={{ color: "#a78bfa", textDecoration: "none", fontWeight: 500 }}>
            Begin the journey
          </Link>
        </p>
      </div>
    </main>
  );
}
