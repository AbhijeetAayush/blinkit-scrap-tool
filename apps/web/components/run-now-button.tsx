"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";

import { createClient } from "@/lib/supabase/client";
import type { RunRow } from "@/lib/types";

export function RunNowButton() {
  const [busy, setBusy] = useState(false);
  const [watch, setWatch] = useState(false);
  const [message, setMessage] = useState<string | null>(null);
  const [failed, setFailed] = useState(false);
  const router = useRouter();

  useEffect(() => {
    if (!watch) return;
    let ticks = 0;
    const timer = window.setInterval(() => {
      ticks += 1;
      void (async () => {
        const supabase = createClient();
        const { data } = await supabase.from("runs").select("*").order("started_at", { ascending: false }).limit(1);
        const run = (data as RunRow[] | null)?.[0];
        if (run && run.status !== "running") {
          setMessage(`Last run: ${run.kind} · ${run.status}${run.error ? ` · ${run.error}` : ""}. Open Shelf if rows appeared.`);
          setWatch(false);
          setBusy(false);
          router.refresh();
          return;
        }
        if (ticks >= 48) {
          setMessage("Still working. Open Runs for status, then refresh Shelf in a minute.");
          setWatch(false);
          setBusy(false);
        }
      })();
    }, 2500);
    return () => window.clearInterval(timer);
  }, [watch, router]);

  async function run() {
    setBusy(true);
    setWatch(false);
    setFailed(false);
    setMessage("Starting scrape…");
    try {
      const res = await fetch("/api/run", { method: "POST" });
      const payload = (await res.json().catch(() => ({}))) as { error?: string };
      if (!res.ok) {
        setFailed(true);
        setMessage(payload.error || "Could not enqueue run");
        setBusy(false);
        return;
      }
      setMessage("Started. Store mapping and scrape can take a minute. Shelf fills when the run finishes.");
      setWatch(true);
    } catch (err) {
      setFailed(true);
      setMessage(err instanceof Error ? err.message : "Network error");
      setBusy(false);
    }
  }

  return (
    <div className="flex flex-col gap-2 sm:flex-row sm:items-center">
      <button
        type="button"
        onClick={() => void run()}
        disabled={busy}
        className="rounded-full bg-ink px-4 py-2 text-sm text-lime disabled:opacity-50"
      >
        {busy ? "Working…" : "Run scrape"}
      </button>
      {message ? <p className={`text-sm ${failed ? "text-oos" : "text-ink/70"}`}>{message}</p> : null}
    </div>
  );
}
