import { createBrowserClient } from "@supabase/ssr";

/**
 * Browser-side Supabase client.
 * Used in Client Components ("use client") for auth operations.
 * The publishable key is safe to expose in the browser.
 */
export function createClient() {
  return createBrowserClient(
    process.env.NEXT_PUBLIC_SUPABASE_URL!,
    process.env.NEXT_PUBLIC_SUPABASE_PUBLISHABLE_KEY!
  );
}
