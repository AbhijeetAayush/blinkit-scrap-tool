"use client";

import { useCallback, useEffect, useState } from "react";
import Link from "next/link";

import { CoverageManager } from "@/components/coverage-manager";
import { KeywordManager } from "@/components/keyword-manager";
import { api, ApiError } from "@/lib/api-client";
import type { ItemsResponse, Run, RunStatus } from "@/lib/types";

const TERMINAL: RunStatus[] = ["done", "error", "cancelled"];

function isTerminal(status: string) {
  return (TERMINAL as string[]).includes(status);
}

function statusClass(status: string) {
  return `badge badge-${status}`;
}

export default function RunsPage() {
  const [keywordIds, setKeywordIds] = useState<string[]>([]);
  const [locationIds, setLocationIds] = useState<string[]>([]);
  const [runs, setRuns] = useState<Run[]>([]);
  const [watchId, setWatchId] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  const onKeywords = useCallback((ids: string[]) => setKeywordIds(ids), []);
  const onLocations = useCallback((ids: string[]) => setLocationIds(ids), []);

  const loadRuns = useCallback(async () => {
    const runList = await api<ItemsResponse<Run>>("/runs");
    setRuns(runList.items);
  }, []);

  useEffect(() => {
    void loadRuns().catch((err) => {
      setError(err instanceof ApiError ? err.message : "Failed to load runs");
    });
  }, [loadRuns]);

  useEffect(() => {
    if (!watchId) return;

    const tick = async () => {
      try {
        const run = await api<Run>(`/runs/${watchId}`);
        setRuns((prev) => {
          const next = prev.filter((r) => r.id !== run.id);
          return [run, ...next];
        });
        if (isTerminal(run.status)) {
          setWatchId(null);
        }
      } catch (err) {
        setError(err instanceof ApiError ? err.message : "Failed to poll run");
        setWatchId(null);
      }
    };

    void tick();
    const id = window.setInterval(() => void tick(), 2000);
    return () => window.clearInterval(id);
  }, [watchId]);

  async function startRun() {
    setBusy(true);
    setError(null);
    try {
      const run = await api<Run>("/runs", {
        method: "POST",
        body: JSON.stringify({
          keyword_ids: keywordIds,
          location_ids: locationIds,
        }),
      });
      setRuns((prev) => [run, ...prev.filter((r) => r.id !== run.id)]);
      setWatchId(run.id);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Failed to start run");
    } finally {
      setBusy(false);
    }
  }

  const canStart = keywordIds.length > 0 && locationIds.length > 0 && !busy;
  const pages = keywordIds.length * locationIds.length;

  return (
    <div className="space-y-8">
      <header>
        <h1 className="text-2xl font-semibold tracking-tight">Runs</h1>
        <p className="mt-1 text-sm text-zinc-500">
          Select keywords and locations (same CSV upload + checkboxes as Setup), then start a
          harvest. Or manage lists on{" "}
          <Link href="/setup" className="text-sky-700 underline">
            Setup
          </Link>
          .
        </p>
      </header>

      {error ? <p className="text-sm text-red-600">{error}</p> : null}

      <section>
        <h2 className="mb-3 text-lg font-medium">Keywords</h2>
        <KeywordManager onSelectionChange={onKeywords} />
      </section>

      <section>
        <h2 className="mb-3 text-lg font-medium">Locations</h2>
        <CoverageManager onSelectionChange={onLocations} />
      </section>

      <div className="flex flex-wrap items-center gap-3 rounded border border-zinc-200 bg-white p-4">
        <button
          className="btn btn-primary"
          type="button"
          disabled={!canStart}
          onClick={() => void startRun()}
        >
          {busy ? "Starting…" : "Start run"}
        </button>
        <p className="text-sm text-zinc-500">
          {keywordIds.length} keywords × {locationIds.length} locations
          {pages > 0 ? ` ≈ ${pages} searches` : ""}
          {watchId ? " · polling active run…" : ""}
        </p>
      </div>

      <section className="space-y-3">
        <h2 className="text-lg font-medium">Recent runs</h2>
        <div className="table-wrap">
          <table className="data">
            <thead>
              <tr>
                <th>Started</th>
                <th>Status</th>
                <th>Jobs</th>
                <th>Pages ok</th>
                <th>Pages fail</th>
                <th>Error</th>
              </tr>
            </thead>
            <tbody>
              {runs.length === 0 ? (
                <tr>
                  <td colSpan={6} className="text-zinc-500">
                    No runs yet.
                  </td>
                </tr>
              ) : (
                runs.map((run) => (
                  <tr key={run.id} className={watchId === run.id ? "bg-sky-50" : undefined}>
                    <td className="whitespace-nowrap">
                      {run.started_at ? new Date(run.started_at).toLocaleString() : "—"}
                    </td>
                    <td>
                      <span className={statusClass(run.status)}>{run.status}</span>
                    </td>
                    <td>
                      {run.jobs_done}/{run.jobs_total}
                    </td>
                    <td>{run.pages_ok}</td>
                    <td>{run.pages_fail}</td>
                    <td className="max-w-xs truncate text-zinc-500">{run.error ?? "—"}</td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </section>
    </div>
  );
}
