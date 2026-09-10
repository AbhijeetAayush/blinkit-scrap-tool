"use client";

import { useCallback, useState } from "react";
import Link from "next/link";

import { CoverageManager } from "@/components/coverage-manager";
import { KeywordManager } from "@/components/keyword-manager";
import { api, ApiError } from "@/lib/api-client";
import type { Run } from "@/lib/types";

export default function SetupPage() {
  const [keywordIds, setKeywordIds] = useState<string[]>([]);
  const [locationIds, setLocationIds] = useState<string[]>([]);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [info, setInfo] = useState<string | null>(null);

  const onKeywords = useCallback((ids: string[]) => setKeywordIds(ids), []);
  const onLocations = useCallback((ids: string[]) => setLocationIds(ids), []);

  const pages = keywordIds.length * locationIds.length;
  const canRun = keywordIds.length > 0 && locationIds.length > 0 && !busy;

  async function startRun() {
    setBusy(true);
    setError(null);
    setInfo(null);
    try {
      const run = await api<Run>("/runs", {
        method: "POST",
        body: JSON.stringify({
          keyword_ids: keywordIds,
          location_ids: locationIds,
        }),
      });
      setInfo(`Run ${run.id.slice(0, 8)}… queued (${run.status}). Open Runs to watch progress.`);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Failed to start run");
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="space-y-9">
      <header>
        <h1 className="text-2xl font-semibold tracking-tight">Keywords and locations</h1>
        <p className="mt-1 max-w-2xl text-sm text-zinc-500">
          Upload CSVs or add rows by hand. Check the keywords and stores you want, then run. Every
          product on those Blinkit search pages is saved.
        </p>
      </header>

      <section>
        <h2 className="text-lg font-medium">Keywords</h2>
        <p className="mb-3 text-sm text-zinc-500">
          Upload keywords.csv (header Keyword) or type one. Then check rows to scrape.
        </p>
        <KeywordManager onSelectionChange={onKeywords} />
      </section>

      <section>
        <h2 className="text-lg font-medium">Locations</h2>
        <p className="mb-3 text-sm text-zinc-500">
          Upload blinkit_pune_stores.csv (Store Name, Area, Pincode, Latitude, Longitude) or add
          lat/lon.
        </p>
        <CoverageManager onSelectionChange={onLocations} />
      </section>

      <section className="rounded border border-zinc-200 bg-white p-5">
        <h2 className="text-lg font-medium">Run scrape</h2>
        {!canRun && !busy ? (
          <p className="mt-2 text-sm text-zinc-500">Check at least one keyword and one location.</p>
        ) : (
          <p className="mt-2 text-sm text-zinc-500">
            About {pages} searches ({keywordIds.length} keywords × {locationIds.length} locations).
          </p>
        )}
        {error ? <p className="mt-2 text-sm text-red-600">{error}</p> : null}
        {info ? (
          <p className="mt-2 text-sm text-zinc-600">
            {info}{" "}
            <Link href="/runs" className="text-sky-700 underline">
              Go to Runs
            </Link>
          </p>
        ) : null}
        <div className="mt-4">
          <button type="button" className="btn btn-primary" disabled={!canRun} onClick={() => void startRun()}>
            {busy ? "Starting…" : "Start run"}
          </button>
        </div>
      </section>
    </div>
  );
}
