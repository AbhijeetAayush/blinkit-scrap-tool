"use client";

import { FormEvent, useEffect, useState } from "react";

import { createClient } from "@/lib/supabase/client";
import { headerIndex, parseCsv } from "@/lib/csv";
import type { CoveragePin } from "@/lib/types";

const PAGE = 50;
const CHUNK = 200;
const MAX_FILE = 2_000_000;

function roundCoord(n: number): number {
  return Math.round(n * 1e6) / 1e6;
}

export function CoverageManager({
  brandId,
  selected,
  onSelectionChange,
  onCount,
}: {
  brandId: string;
  selected?: Set<string>;
  onSelectionChange?: (next: Set<string>) => void;
  onCount?: (n: number) => void;
}) {
  const [rows, setRows] = useState<CoveragePin[]>([]);
  const [page, setPage] = useState(0);
  const [search, setSearch] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [info, setInfo] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [form, setForm] = useState({
    store_name: "",
    pincode: "",
    city: "",
    locality: "",
    lat: "",
    lon: "",
    platform: "blinkit",
    tier: "hot",
  });

  async function load(offset: number, q = search) {
    const supabase = createClient();
    let list = supabase
      .from("pincodes")
      .select("*")
      .eq("brand_id", brandId)
      .order("pincode")
      .range(offset, offset + PAGE - 1);
    let countQ = supabase.from("pincodes").select("id", { count: "exact", head: true }).eq("brand_id", brandId);
    if (q.trim()) {
      const term = `%${q.trim()}%`;
      list = list.or(`pincode.ilike.${term},locality.ilike.${term},store_name.ilike.${term}`);
      countQ = countQ.or(`pincode.ilike.${term},locality.ilike.${term},store_name.ilike.${term}`);
    }
    const [{ data, error: qError }, { count, error: cError }] = await Promise.all([list, countQ]);
    const err = qError || cError;
    if (err) setError(err.message);
    else {
      setError(null);
      setRows((data as CoveragePin[]) ?? []);
      onCount?.(count ?? 0);
    }
  }

  useEffect(() => {
    void load(0);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [brandId]);

  function toggle(id: string) {
    if (!onSelectionChange) return;
    const next = new Set(chosen);
    if (next.has(id)) next.delete(id);
    else next.add(id);
    onSelectionChange(next);
  }

  function selectVisible() {
    if (!onSelectionChange) return;
    const next = new Set(chosen);
    rows.forEach((r) => next.add(r.id));
    onSelectionChange(next);
  }

  async function selectMatching() {
    const supabase = createClient();
    let q = supabase.from("pincodes").select("id").eq("brand_id", brandId).eq("active", true);
    if (search.trim()) {
      const term = `%${search.trim()}%`;
      q = q.or(`pincode.ilike.${term},locality.ilike.${term},store_name.ilike.${term}`);
    }
    const { data, error: qError } = await q.limit(2000);
    if (qError) {
      setError(qError.message);
      return;
    }
    const ids = (data ?? []).map((r) => r.id as string);
    if (ids.length > 50 && !window.confirm(`Select ${ids.length} locations?`)) return;
    const next = new Set(chosen);
    ids.forEach((id) => next.add(id));
    onSelectionChange?.(next);
    setInfo(`Selected ${ids.length} locations.`);
  }

  async function onSubmit(event: FormEvent) {
    event.preventDefault();
    setBusy(true);
    setError(null);
    const lat = roundCoord(Number(form.lat));
    const lon = roundCoord(Number(form.lon));
    if (!Number.isFinite(lat) || !Number.isFinite(lon)) {
      setError("Latitude and longitude must be numbers");
      setBusy(false);
      return;
    }
    const supabase = createClient();
    const { error: insertError } = await supabase.from("pincodes").upsert(
      {
        brand_id: brandId,
        platform: form.platform,
        pincode: form.pincode.trim(),
        city: form.city || null,
        locality: form.locality || null,
        store_name: form.store_name || null,
        lat,
        lon,
        tier: form.tier,
      },
      { onConflict: "brand_id,platform,lat,lon" },
    );
    setBusy(false);
    if (insertError) {
      setError(insertError.message);
      return;
    }
    setForm({ ...form, store_name: "", pincode: "", city: "", locality: "", lat: "", lon: "" });
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
    const text = await file.text();
    const table = parseCsv(text);
    if (table.length < 2) {
      setBusy(false);
      setError("CSV needs a header and at least one store row.");
      return;
    }
    const header = table[0];
    const storeIdx = headerIndex(header, "store name", "store_name");
    const areaIdx = headerIndex(header, "area", "locality");
    const pinIdx = headerIndex(header, "pincode", "pin");
    const latIdx = headerIndex(header, "latitude", "lat");
    const lonIdx = headerIndex(header, "longitude", "lon", "lng");
    if (pinIdx < 0 || latIdx < 0 || lonIdx < 0) {
      setBusy(false);
      setError("CSV must include Pincode, Latitude, Longitude (Pune file format).");
      return;
    }
    const payloads: Record<string, unknown>[] = [];
    let skipped = 0;
    for (const row of table.slice(1)) {
      const lat = roundCoord(Number(row[latIdx]));
      const lon = roundCoord(Number(row[lonIdx]));
      const pincode = (row[pinIdx] || "").trim();
      if (!pincode || !Number.isFinite(lat) || !Number.isFinite(lon)) {
        skipped += 1;
        continue;
      }
      payloads.push({
        brand_id: brandId,
        platform: "blinkit",
        pincode,
        store_name: storeIdx >= 0 ? (row[storeIdx] || "").trim() || null : null,
        locality: areaIdx >= 0 ? (row[areaIdx] || "").trim() || null : null,
        lat,
        lon,
        tier: "hot",
        active: true,
      });
    }
    const supabase = createClient();
    for (let i = 0; i < payloads.length; i += CHUNK) {
      const { error: writeError } = await supabase
        .from("pincodes")
        .upsert(payloads.slice(i, i + CHUNK), { onConflict: "brand_id,platform,lat,lon" });
      if (writeError) {
        setBusy(false);
        setError(writeError.message);
        return;
      }
    }
    setBusy(false);
    setInfo(`Saved ${payloads.length} locations${skipped ? `, skipped ${skipped}` : ""}. Nothing is selected — check stores to scrape.`);
    setPage(0);
    await load(0);
  }

  const chosen = selected ?? new Set<string>();
  const canSelect = Boolean(onSelectionChange);

  async function toggleActive(pin: CoveragePin) {
    const supabase = createClient();
    await supabase.from("pincodes").update({ active: !pin.active }).eq("id", pin.id);
    await load(page * PAGE);
  }

  const showPager = page > 0 || rows.length === PAGE;

  return (
    <section>
      <form onSubmit={onSubmit} className="grid gap-3 rounded-2xl border border-ink/10 bg-white/60 p-4 md:grid-cols-3">
        <input
          className="rounded-lg border border-ink/15 px-3 py-2"
          placeholder="Store name"
          value={form.store_name}
          onChange={(e) => setForm({ ...form, store_name: e.target.value })}
        />
        <input
          className="rounded-lg border border-ink/15 px-3 py-2"
          placeholder="Pincode"
          value={form.pincode}
          onChange={(e) => setForm({ ...form, pincode: e.target.value })}
          required
        />
        <input
          className="rounded-lg border border-ink/15 px-3 py-2"
          placeholder="Area / locality"
          value={form.locality}
          onChange={(e) => setForm({ ...form, locality: e.target.value })}
        />
        <input
          className="rounded-lg border border-ink/15 px-3 py-2"
          placeholder="Latitude"
          value={form.lat}
          onChange={(e) => setForm({ ...form, lat: e.target.value })}
          required
        />
        <input
          className="rounded-lg border border-ink/15 px-3 py-2"
          placeholder="Longitude"
          value={form.lon}
          onChange={(e) => setForm({ ...form, lon: e.target.value })}
          required
        />
        <select
          className="rounded-lg border border-ink/15 px-3 py-2"
          value={form.tier}
          onChange={(e) => setForm({ ...form, tier: e.target.value })}
        >
          <option value="hot">hot</option>
          <option value="warm">warm</option>
          <option value="cold">cold</option>
        </select>
        <button type="submit" disabled={busy} className="rounded-full bg-ink px-4 py-2 text-lime disabled:opacity-50">
          {busy ? "Saving…" : "Add location"}
        </button>
        <label className="rounded-full border border-ink/20 px-4 py-2 text-sm text-center">
          Upload CSV
          <input type="file" accept=".csv,text/csv" className="hidden" onChange={(e) => void onFile(e.target.files?.[0] ?? null)} />
        </label>
      </form>
      <p className="mt-2 text-xs text-ink/55">CSV: Store Name, Area, Pincode, Latitude, Longitude.</p>
      {error ? <p className="mt-3 text-sm text-oos">{error}</p> : null}
      {info ? <p className="mt-2 text-sm text-ink/70">{info}</p> : null}

      <div className="mt-4 flex flex-wrap gap-2">
        <input
          className="rounded-lg border border-ink/15 px-3 py-2 text-sm"
          placeholder="Search pin / area / store"
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
        {canSelect ? (
          <>
            <button type="button" className="rounded-full border border-ink/20 px-3 py-1 text-sm" onClick={selectVisible}>
              Select visible
            </button>
            <button type="button" className="rounded-full border border-ink/20 px-3 py-1 text-sm" onClick={() => void selectMatching()}>
              Select matching search
            </button>
            <button type="button" className="rounded-full border border-ink/20 px-3 py-1 text-sm" onClick={() => onSelectionChange?.(new Set())}>
              Clear selection
            </button>
            <span className="self-center text-sm text-ink/60">{chosen.size} selected</span>
          </>
        ) : null}
      </div>

      <div className="mt-4 overflow-x-auto rounded-2xl border border-ink/10 bg-white/70">
        <table className="w-full text-left text-sm">
          <thead className="bg-ink/5 text-ink/60">
            <tr>
              {canSelect ? <th className="px-3 py-2">Scrape</th> : null}
              <th className="px-3 py-2">Store</th>
              <th className="px-3 py-2">Pin</th>
              <th className="px-3 py-2">Area</th>
              <th className="px-3 py-2">Lat / lon</th>
              <th className="px-3 py-2">Active</th>
            </tr>
          </thead>
          <tbody>
            {rows.length === 0 ? (
              <tr>
                <td className="px-3 py-4 text-ink/50" colSpan={6}>
                  No locations yet. Upload blinkit_pune_stores.csv or add lat/lon by hand.
                </td>
              </tr>
            ) : (
              rows.map((pin) => (
                <tr key={pin.id} className="border-t border-ink/5">
                  {canSelect ? (
                    <td className="px-3 py-2">
                      <input type="checkbox" checked={chosen.has(pin.id)} onChange={() => toggle(pin.id)} />
                    </td>
                  ) : null}
                  <td className="px-3 py-2">{pin.store_name}</td>
                  <td className="px-3 py-2">
                    <a className="underline" href={`/pins/${pin.pincode}`}>
                      {pin.pincode}
                    </a>
                  </td>
                  <td className="px-3 py-2">{pin.locality}</td>
                  <td className="px-3 py-2 tabular">
                    {pin.lat}, {pin.lon}
                  </td>
                  <td className="px-3 py-2">
                    <button type="button" className="underline" onClick={() => void toggleActive(pin)}>
                      {pin.active ? "on" : "off"}
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
