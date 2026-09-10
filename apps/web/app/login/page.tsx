"use client";

import { FormEvent, useState } from "react";
import { useRouter } from "next/navigation";

import { authUserMessage, isSignupRetryError } from "@/lib/auth-message";
import { createClient } from "@/lib/supabase/client";

export default function LoginPage() {
  const router = useRouter();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [mode, setMode] = useState<"signin" | "signup">("signin");
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  async function onSubmit(event: FormEvent) {
    event.preventDefault();
    if (busy) return;
    setBusy(true);
    setError(null);
    try {
      const supabase = createClient();
      if (mode === "signin") {
        const { error: authError } = await supabase.auth.signInWithPassword({ email, password });
        if (authError) {
          setError(authUserMessage(authError.message));
          return;
        }
        router.push("/setup");
        router.refresh();
        return;
      }

      const { data, error: authError } = await supabase.auth.signUp({
        email,
        password,
        options: { emailRedirectTo: `${window.location.origin}/setup` },
      });
      if (authError) {
        if (isSignupRetryError(authError.message)) {
          const { data: signed, error: signInError } = await supabase.auth.signInWithPassword({
            email,
            password,
          });
          if (!signInError && signed.session) {
            router.push("/onboarding");
            router.refresh();
            return;
          }
          setError(authUserMessage(signInError?.message || authError.message));
          setMode("signin");
          return;
        }
        setError(authUserMessage(authError.message));
        return;
      }
      if (!data.session) {
        setError(
          "Account created. Confirm email is on, so check your inbox — or turn Confirm email off in Supabase Auth and sign in.",
        );
        setMode("signin");
        return;
      }
      router.push("/onboarding");
      router.refresh();
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="mx-auto max-w-md pt-16">
      <p className="text-xs font-medium uppercase tracking-[0.2em] text-moss">Digital shelf</p>
      <h1 className="mt-2 font-display text-4xl tracking-tight">Watch your SKUs on Blinkit</h1>
      <p className="mt-3 text-ink/70">Price, stock, rank, and brand rivals — not platform vs platform.</p>
      <form onSubmit={onSubmit} className="card mt-8 space-y-4 p-6">
        <label className="block text-sm">
          Email
          <input
            className="field mt-1 w-full"
            type="email"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            required
            autoComplete="email"
          />
        </label>
        <label className="block text-sm">
          Password
          <input
            className="field mt-1 w-full"
            type="password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            required
            minLength={8}
            autoComplete={mode === "signin" ? "current-password" : "new-password"}
          />
        </label>
        {error ? <p className="text-sm text-oos">{error}</p> : null}
        <button type="submit" disabled={busy} className="btn w-full disabled:opacity-50">
          {busy ? "Please wait…" : mode === "signin" ? "Sign in" : "Create account"}
        </button>
        <button
          type="button"
          className="w-full text-sm text-ink/60"
          onClick={() => {
            setMode(mode === "signin" ? "signup" : "signin");
            setError(null);
          }}
        >
          {mode === "signin" ? "Need an account?" : "Already have an account?"}
        </button>
      </form>
    </div>
  );
}
