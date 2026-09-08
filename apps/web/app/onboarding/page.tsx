"use client";

import { FormEvent, useState } from "react";
import { useRouter } from "next/navigation";

import { SetupStepper } from "@/components/setup-stepper";
import { createClient } from "@/lib/supabase/client";

export default function OnboardingPage() {
  const router = useRouter();
  const [name, setName] = useState("");
  const [homeCity, setHomeCity] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  async function onSubmit(event: FormEvent) {
    event.preventDefault();
    if (busy) return;
    setBusy(true);
    setError(null);
    try {
      const supabase = createClient();
      const {
        data: { user },
      } = await supabase.auth.getUser();
      if (!user) {
        router.push("/login");
        return;
      }
      const { data: existing } = await supabase
        .from("brand_members")
        .select("brand_id")
        .eq("user_id", user.id)
        .limit(1)
        .maybeSingle();
      if (existing) {
        router.push("/setup");
        router.refresh();
        return;
      }
      const { data: brandId, error: rpcError } = await supabase.rpc("onboard_brand", {
        p_name: name,
        p_home_city: homeCity || null,
      });
      if (rpcError || !brandId) {
        setError(
          rpcError?.message?.includes("onboard_brand")
            ? "Database is missing onboard_brand. Run supabase/migrations/0002_rls_onboard_obs_unique.sql in the SQL editor."
            : (rpcError?.message ?? "Could not create brand"),
        );
        return;
      }
      router.push("/setup");
      router.refresh();
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="mx-auto max-w-lg">
      <SetupStepper current="onboarding" />
      <h1 className="font-display text-3xl">Name the brand you track</h1>
      <p className="mt-2 text-ink/70">
        Add SKUs, a pincode, and run the scrape on the next screen — one page.
      </p>
      <form onSubmit={onSubmit} className="mt-8 space-y-4 rounded-2xl border border-ink/10 bg-white/60 p-6">
        <label className="block text-sm">
          Brand name
          <input
            className="mt-1 w-full rounded-lg border border-ink/15 px-3 py-2"
            value={name}
            onChange={(e) => setName(e.target.value)}
            required
          />
        </label>
        <label className="block text-sm">
          Home city
          <input
            className="mt-1 w-full rounded-lg border border-ink/15 px-3 py-2"
            value={homeCity}
            onChange={(e) => setHomeCity(e.target.value)}
          />
        </label>
        {error ? <p className="text-sm text-oos">{error}</p> : null}
        <button type="submit" disabled={busy} className="rounded-full bg-ink px-4 py-2 text-lime disabled:opacity-50">
          {busy ? "Saving…" : "Continue"}
        </button>
      </form>
    </div>
  );
}
