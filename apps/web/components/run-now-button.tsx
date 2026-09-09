"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";

import { createClient } from "@/lib/supabase/client";
import { useBrandId } from "@/lib/use-brand";
import type { RunRow } from "@/lib/types";

export function RunNowButton({
  keywordIds = [],
  pincodeIds = [],
  pages,
}: {
  keywordIds?: string[];
  pincodeIds?: string[];
  pages?: number;
}) {
  const [busy, setBusy] = useState(false);
  const [watch, setWatch] = useState(false);
  const [message, setMessage] = useState<string | null>(null);
  const [failed, setFailed] = useState(false);
  const router = useRouter();
  const { brandId } = useBrandId();

  useEffect(() => {
    if (!watch) return;
    let ticks = 0;
    const timer = window.setInterval(() => {
      ticks += 1;
      void (async () => {
        const supabase = createClient();
        let q = supabase.from("runs").select("*").order("started_at", { ascending: false }).limit(1);
        if (brandId) q = q.eq("brand_id", brandId);
        const { data } = await q;
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
  }, [watch, router, brandId]);

  if (keywordIds.length === 0 || pincodeIds.length === 0) {
    return (
      <Link href="/setup" className="rounded-full bg-ink px-4 py-2 text-sm text-lime">
        Select keywords and locations
      </Link>
    );
  }

  async function run() {
    const n = pages ?? keywordIds.length * pincodeIds.length;
    if (n > 50 && !window.confirm(`This is ${n} ScrapingBee searches. Continue?`)) return;
    setBusy(true);
    setWatch(false);
    setFailed(false);
    setMessage("Starting scrape…");
    try {
      const res = await fetch("/api/run", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ keyword_ids: keywordIds, pincode_ids: pincodeIds }),
      });
      const payload = (await res.json().catch(() => ({}))) as { error?: string };
      if (!res.ok) {
        setFailed(true);
        setMessage(payload.error || "Could not enqueue run");
        setBusy(false);
        return;
      }
      setMessage("Started. Scrape can take a minute per location. Shelf fills when the run finishes.");
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
