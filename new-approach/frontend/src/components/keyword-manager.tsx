"use client";

import { FormEvent, memo, useEffect, useMemo, useRef, useState } from "react";

import { api, ApiError } from "@/lib/api-client";
import { headerIndex, parseCsv } from "@/lib/csv";
import { debounce } from "@/lib/debounce";
import { normalizeKeyword, uniqueKeywords } from "@/lib/normalize-keyword";
import type { ItemsResponse, Keyword } from "@/lib/types";

const PAGE = 50;
const CHUNK = 200;
const MAX_FILE = 2_000_000;

type BulkResponse = { read: number; saved: number };
type IdsResponse = { ids: string[] };

export const KeywordManager = memo(function KeywordManager({
  onSelectionChange,
}: {
  onSelectionChange?: (ids: string[]) => void;
}) {
  const [rows, setRows] = useState<Keyword[]>([]);
  const [page, setPage] = useState(0);
  const [search, setSearch] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [info, setInfo] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [manual, setManual] = useState("");
  const [selected, setSelected] = useState<Set<string>>(() => new Set());
  const searchRef = useRef(search);
  searchRef.current = search;

  function emit(next: Set<string>) {
    setSelected(next);
    onSelectionChange?.(Array.from(next));
  }

  async function load(offset: number, q = searchRef.current) {
    try {
      const params = new URLSearchParams({
        offset: String(offset),
        limit: String(PAGE),
      });
      if (q.trim()) params.set("q", q.trim());
      const data = await api<ItemsResponse<Keyword>>(`/keywords?${params}`);
      setError(null);
      setRows(data.items);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Failed to load keywords");
    }
  }

  const debouncedLoad = useMemo(
    () =>
      debounce((q: string) => {
        setPage(0);
        void load(0, q);
      }, 180),
    [],
  );

  useEffect(() => {
    void load(0, "");
    return () => debouncedLoad.cancel();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  function toggle(id: string) {
    const next = new Set(selected);
    if (next.has(id)) next.delete(id);
    else next.add(id);
    emit(next);
  }

  function selectVisible() {
    const next = new Set(selected);
    rows.forEach((r) => next.add(r.id));
    emit(next);
  }

  async function selectMatching() {
    try {
      const params = new URLSearchParams({ limit: "2000" });
      if (search.trim()) params.set("q", search.trim());
      const data = await api<IdsResponse>(`/keywords/ids?${params}`);
      const ids = data.ids;
      if (ids.length > 50 && !window.confirm(`Select ${ids.length} matching keywords?`)) return;
      const next = new Set(selected);
      ids.forEach((id) => next.add(id));
      emit(next);
      setInfo(`Selected ${ids.length} matching keywords.`);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Failed to select matching");
    }
  }

  async function addManual(event: FormEvent) {
    event.preventDefault();
    const query = normalizeKeyword(manual);
    if (!query) {
      setError("Keyword must be at least 3 characters and not 'Others'.");
      return;
    }
    setBusy(true);
    setError(null);
    try {
      await api<Keyword>("/keywords", {
        method: "POST",
        body: JSON.stringify({ query }),
      });
      setManual("");
      setInfo("Keyword saved.");
      await load(page * PAGE);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Failed to add keyword");
    } finally {
      setBusy(false);
    }
  }

  async function onFile(file: File | null) {
    if (!file) return;
    if (file.size > MAX_FILE) {
      setError("CSV must be under 2MB.");
      return;
    }
    setBusy(true);
    setError(null);
    setInfo("Importing…");
    try {
      const text = await file.text();
      const table = parseCsv(text);
      if (!table.length) {
        setError("CSV is empty.");
        return;
      }
      let start = 0;
      let col = 0;
      const header = table[0].map((c) => c.trim());
      const idx = headerIndex(header, "keyword", "query");
      if (idx >= 0) {
        col = idx;
        start = 1;
      }
      const raw = table.slice(start).map((r) => r[col] ?? "");
      const unique = uniqueKeywords(raw);
      let saved = 0;
      for (let i = 0; i < unique.length; i += CHUNK) {
        const chunk = unique.slice(i, i + CHUNK);
        const res = await api<BulkResponse>("/keywords/bulk", {
          method: "POST",
          body: JSON.stringify({ queries: chunk }),
        });
        saved += res.saved;
      }
      setInfo(
        `Read ${raw.length} rows, skipped junk/dupes, saved ${saved} unique keywords. Nothing is selected — check the ones to scrape.`,
      );
      setPage(0);
      await load(0);
    } catch (err) {
      setInfo(null);
      setError(err instanceof ApiError ? err.message : err instanceof Error ? err.message : "CSV import failed");
    } finally {
      setBusy(false);
    }
  }

  async function toggleActive(row: Keyword) {
    try {
      await api<Keyword>(`/keywords/${row.id}`, {
        method: "PATCH",
        body: JSON.stringify({ active: !row.active }),
      });
      await load(page * PAGE);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Failed to update keyword");
    }
  }

  const showPager = page > 0 || rows.length === PAGE;

  return (
    <section>
      <form onSubmit={addManual} className="flex flex-wrap gap-2 rounded border border-zinc-200 bg-white p-4">
        <input
          className="input min-w-[220px] flex-1"
          placeholder="Add keyword (e.g. mini mogra rice 5 kg)"
          value={manual}
          onChange={(e) => setManual(e.target.value)}
        />
        <button type="submit" disabled={busy} className="btn btn-primary">
          Add keyword
        </button>
        <label className="btn cursor-pointer text-sm">
          Upload CSV
          <input
            type="file"
            accept=".csv,text/csv"
            className="hidden"
            onChange={(e) => void onFile(e.target.files?.[0] ?? null)}
          />
        </label>
      </form>
      <p className="mt-2 text-xs text-zinc-500">
        CSV header: Keyword. After upload, checkboxes stay off until you select.
      </p>
      {error ? <p className="mt-2 text-sm text-red-600">{error}</p> : null}
      {info ? <p className="mt-2 text-sm text-zinc-600">{info}</p> : null}

      <div className="mt-4 flex flex-wrap gap-2">
        <input
          className="input max-w-xs"
          placeholder="Search keywords"
          value={search}
          onChange={(e) => {
            const q = e.target.value;
            setSearch(q);
            debouncedLoad(q);
          }}
        />
        <button type="button" className="btn" onClick={selectVisible}>
          Select visible
        </button>
        <button type="button" className="btn" onClick={() => void selectMatching()}>
          Select matching search
        </button>
        <button type="button" className="btn" onClick={() => emit(new Set())}>
          Clear selection
        </button>
        <span className="self-center text-sm text-zinc-500">{selected.size} selected</span>
      </div>

      <div className="table-wrap mt-4">
        <table className="data">
          <thead>
            <tr>
              <th className="w-16">Scrape</th>
              <th>Keyword</th>
              <th className="w-20">Active</th>
            </tr>
          </thead>
          <tbody>
            {rows.length === 0 ? (
              <tr>
                <td className="text-zinc-500" colSpan={3}>
                  No keywords yet. Upload keywords.csv or add one by hand.
                </td>
              </tr>
            ) : (
              rows.map((row) => (
                <tr key={row.id}>
                  <td>
                    <input type="checkbox" checked={selected.has(row.id)} onChange={() => toggle(row.id)} />
                  </td>
                  <td>{row.query}</td>
                  <td>
                    <button type="button" className="text-sky-700 underline" onClick={() => void toggleActive(row)}>
                      {row.active ? "on" : "off"}
                    </button>
                  </td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>
      {showPager ? (
        <div className="mt-4 flex gap-2">
          <button
            type="button"
            className="btn"
            disabled={page === 0}
            onClick={() => {
              const next = Math.max(0, page - 1);
              setPage(next);
              void load(next * PAGE);
            }}
          >
            Previous page
          </button>
          <button
            type="button"
            className="btn"
            disabled={rows.length < PAGE}
            onClick={() => {
              const next = page + 1;
              setPage(next);
              void load(next * PAGE);
            }}
          >
            Next page
          </button>
        </div>
      ) : null}
    </section>
  );
});
