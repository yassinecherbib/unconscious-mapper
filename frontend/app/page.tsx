import { redirect } from "next/navigation";
import { createClient } from "@/lib/supabase/server";

/**
 * Root page — checks session server-side and redirects:
 * - Authenticated   → /journal
 * - Unauthenticated → /login
 */
export default async function RootPage() {
  const supabase = await createClient();
  const { data: { user } } = await supabase.auth.getUser();

  if (user) {
    redirect("/journal");
  } else {
    redirect("/login");
  }
}
