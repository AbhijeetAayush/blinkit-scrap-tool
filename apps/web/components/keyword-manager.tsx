"use client";

import { FormEvent, useEffect, useState } from "react";

import { createClient } from "@/lib/supabase/client";
import { headerIndex, parseCsv } from "@/lib/csv";
import { normalizeKeyword, uniqueKeywords } from "@/lib/normalize-keyword";
import type { Keyword } from "@/lib/types";

const PAGE = 50;
const CHUNK = 200;
const MAX_FILE = 2_000_000;

export function KeywordManager({
  brandId,
  selected,
  onSelectionChange,
  onCount,
}: {
  brandId: string;
  selected: Set<string>;
  onSelectionChange: (next: Set<string>) => void;
  onCount?: (n: number) => void;
}) {
  const [rows, setRows] = useState<Keyword[]>([]);
  const [page, setPage] = useState(0);
  const [search, setSearch] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [info, setInfo] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [manual, setManual] = useState("");

  async function load(offset: number, q = search) {
    const supabase = createClient();
    let list = supabase
      .from("keywords")
      .select("*")
      .eq("brand_id", brandId)
      .order("query")
      .range(offset, offset + PAGE - 1);
    let countQ = supabase.from("keywords").select("id", { count: "exact", head: true }).eq("brand_id", brandId);
    if (q.trim()) {
      const term = `%${q.trim()}%`;
      list = list.ilike("query", term);
      countQ = countQ.ilike("query", term);
    }
    const [{ data, error: qError }, { count, error: cError }] = await Promise.all([list, countQ]);
    const err = qError || cError;
    if (err) setError(err.message);
    else {
      setError(null);
      setRows((data as Keyword[]) ?? []);
      onCount?.(count ?? 0);
    }
  }

  useEffect(() => {
    void load(0);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [brandId]);

  function toggle(id: string) {
    const next = new Set(selected);
    if (next.has(id)) next.delete(id);
    else next.add(id);
    onSelectionChange(next);
  }

  function selectVisible() {
    const next = new Set(selected);
    rows.forEach((r) => next.add(r.id));
    onSelectionChange(next);
  }

  async function selectMatching() {
    const supabase = createClient();
    let q = supabase.from("keywords").select("id").eq("brand_id", brandId).eq("active", true);
    if (search.trim()) q = q.ilike("query", `%${search.trim()}%`);
    const { data, error: qError } = await q.limit(2000);
    if (qError) {
      setError(qError.message);
      return;
    }
    const ids = (data ?? []).map((r) => r.id as string);
    if (ids.length > 50 && !window.confirm(`Select ${ids.length} matching keywords?`)) return;
    const next = new Set(selected);
    ids.forEach((id) => next.add(id));
    onSelectionChange(next);
    setInfo(`Selected ${ids.length} matching keywords.`);
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
    const supabase = createClient();
    const { error: writeError } = await supabase.from("keywords").upsert(
      { brand_id: brandId, query, active: true },
      { onConflict: "brand_id,query" },
    );
    setBusy(false);
    if (writeError) {
      setError(writeError.message);
      return;
    }
    setManual("");
    setInfo("Keyword saved.");
    await load(page * PAGE);
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
    const text = await file.text();
    const table = parseCsv(text);
    if (!table.length) {
      setBusy(false);
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
    const supabase = createClient();
    let upserted = 0;
    for (let i = 0; i < unique.length; i += CHUNK) {
      const chunk = unique.slice(i, i + CHUNK).map((query) => ({
        brand_id: brandId,
        query,
        active: true,
      }));
      const { error: writeError } = await supabase.from("keywords").upsert(chunk, { onConflict: "brand_id,query" });
      if (writeError) {
        setBusy(false);
        setError(writeError.message);
        return;
      }
      upserted += chunk.length;
    }
    setBusy(false);
    setInfo(`Read ${raw.length} rows, skipped junk/dupes, saved ${upserted} unique keywords. Nothing is selected — check the ones to scrape.`);
    setPage(0);
    await load(0);
  }

  async function toggleActive(row: Keyword) {
    const supabase = createClient();
    await supabase.from("keywords").update({ active: !row.active }).eq("id", row.id);
    await load(page * PAGE);
  }

  const showPager = page > 0 || rows.length === PAGE;

  return (
    <section>
      <form onSubmit={addManual} className="flex flex-wrap gap-2 rounded-2xl border border-ink/10 bg-white/60 p-4">
        <input
          className="min-w-[220px] flex-1 rounded-lg border border-ink/15 px-3 py-2"
          placeholder="Add keyword (e.g. mini mogra rice 5 kg)"
          value={manual}
          onChange={(e) => setManual(e.target.value)}
        />
        <button type="submit" disabled={busy} className="rounded-full bg-ink px-4 py-2 text-sm text-lime disabled:opacity-50">
          Add keyword
        </button>
        <label className="rounded-full border border-ink/20 px-4 py-2 text-sm">
          Upload CSV
          <input
            type="file"
            accept=".csv,text/csv"
            className="hidden"
            onChange={(e) => void onFile(e.target.files?.[0] ?? null)}
          />
        </label>
      </form>
      <p className="mt-2 text-xs text-ink/55">CSV header: Keyword. After upload, checkboxes stay off until you select.</p>
      {error ? <p className="mt-2 text-sm text-oos">{error}</p> : null}
      {info ? <p className="mt-2 text-sm text-ink/70">{info}</p> : null}

      <div className="mt-4 flex flex-wrap gap-2">
        <input
          className="rounded-lg border border-ink/15 px-3 py-2 text-sm"
          placeholder="Search keywords"
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          onKeyDown={(e) => {
            if (e.key === "Enter") {
              setPage(0);
              void load(0, search);
            }
          }}
        />
        <button type="button" className="rounded-full border border-ink/20 px-3 py-1 text-sm" onClick={() => { setPage(0); void load(0, search); }}>
          Search
        </button>
        <button type="button" className="rounded-full border border-ink/20 px-3 py-1 text-sm" onClick={selectVisible}>
          Select visible
        </button>
        <button type="button" className="rounded-full border border-ink/20 px-3 py-1 text-sm" onClick={() => void selectMatching()}>
          Select matching search
        </button>
        <button type="button" className="rounded-full border border-ink/20 px-3 py-1 text-sm" onClick={() => onSelectionChange(new Set())}>
          Clear selection
        </button>
        <span className="self-center text-sm text-ink/60">{selected.size} selected</span>
      </div>

      <div className="mt-4 overflow-x-auto rounded-2xl border border-ink/10 bg-white/70">
        <table className="w-full text-left text-sm">
          <thead className="bg-ink/5 text-ink/60">
            <tr>
              <th className="px-3 py-2">Scrape</th>
              <th className="px-3 py-2">Keyword</th>
              <th className="px-3 py-2">Active</th>
            </tr>
          </thead>
          <tbody>
            {rows.length === 0 ? (
              <tr>
                <td className="px-3 py-4 text-ink/50" colSpan={3}>
                  No keywords yet. Upload keywords.csv or add one by hand.
                </td>
              </tr>
            ) : (
              rows.map((row) => (
                <tr key={row.id} className="border-t border-ink/5">
                  <td className="px-3 py-2">
                    <input type="checkbox" checked={selected.has(row.id)} onChange={() => toggle(row.id)} />
                  </td>
                  <td className="px-3 py-2">{row.query}</td>
                  <td className="px-3 py-2">
                    <button type="button" className="underline" onClick={() => void toggleActive(row)}>
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
            className="rounded-full border border-ink/20 px-3 py-1 text-sm disabled:opacity-40"
            disabled={page === 0}
            onClick={() => {
              const next = Math.max(0, page - 1);
              setPage(next);
              void load(next * PAGE, search);
            }}
          >
            Previous page
          </button>
          <button
            type="button"
            className="rounded-full border border-ink/20 px-3 py-1 text-sm disabled:opacity-40"
            disabled={rows.length < PAGE}
            onClick={() => {
              const next = page + 1;
              setPage(next);
              void load(next * PAGE, search);
            }}
          >
            Next page
          </button>
        </div>
      ) : null}
    </section>
  );
}
