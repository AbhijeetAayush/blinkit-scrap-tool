"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";

import { isRunTerminal } from "@/lib/run-status";
import { createClient } from "@/lib/supabase/client";
import type { RunRow } from "@/lib/types";

export function RunNowButton({
  keywordIds = [],
  pincodeIds = [],
  pages,
  brandId,
}: {
  keywordIds?: string[];
  pincodeIds?: string[];
  pages?: number;
  brandId?: string | null;
}) {
  const [busy, setBusy] = useState(false);
  const [watch, setWatch] = useState(false);
  const [watchId, setWatchId] = useState<string | null>(null);
  const [message, setMessage] = useState<string | null>(null);
  const [failed, setFailed] = useState(false);
  const router = useRouter();

  useEffect(() => {
    if (!watch) return;
    let ticks = 0;
    const tick = async () => {
      if (document.hidden) return;
      ticks += 1;
      const supabase = createClient();
      let q = supabase.from("runs").select("id, kind, status, error").order("started_at", { ascending: false }).limit(1);
      if (watchId) q = supabase.from("runs").select("id, kind, status, error").eq("id", watchId).limit(1);
      else if (brandId) q = q.eq("brand_id", brandId);
      const { data } = await q;
      const run = (data as Pick<RunRow, "id" | "kind" | "status" | "error">[] | null)?.[0];
      if (run && isRunTerminal(run.status)) {
        const bad = run.status === "error" || run.status === "budget" || run.status === "halted";
        setFailed(bad);
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
    };
    const timer = window.setInterval(() => void tick(), 2500);
    return () => window.clearInterval(timer);
  }, [watch, watchId, router, brandId]);

  if (keywordIds.length === 0 || pincodeIds.length === 0) {
    return (
      <Link href="/setup" prefetch className="btn">
        Select keywords and locations
      </Link>
    );
  }

  async function run() {
    const n = pages ?? keywordIds.length * pincodeIds.length;
    if (n > 50 && !window.confirm(`This is ${n} searches against the daily search budget. Continue?`)) return;
    setBusy(true);
    setWatch(false);
    setWatchId(null);
    setFailed(false);
    setMessage("Starting scrape…");
    try {
      const res = await fetch("/api/run", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ keyword_ids: keywordIds, pincode_ids: pincodeIds }),
      });
      const payload = (await res.json().catch(() => ({}))) as { error?: string; run_id?: string };
      if (!res.ok) {
        setFailed(true);
        setMessage(payload.error || "Could not enqueue run");
        setBusy(false);
        return;
      }
      setWatchId(payload.run_id ?? null);
      setMessage("Started. Working until scrapes finish. Shelf fills as rows land.");
      setWatch(true);
    } catch (err) {
      setFailed(true);
      setMessage(err instanceof Error ? err.message : "Network error");
      setBusy(false);
    }
  }

  return (
    <div className="flex flex-col gap-2 sm:flex-row sm:items-center">
      <button type="button" onClick={() => void run()} disabled={busy} className="btn disabled:opacity-50">
        {busy ? "Working…" : "Run scrape"}
      </button>
      {message ? <p className={`text-sm ${failed ? "text-oos" : "text-ink/70"}`}>{message}</p> : null}
    </div>
  );
}
