"use client";

import { FormEvent, memo, useEffect, useMemo, useRef, useState } from "react";

import { createClient } from "@/lib/supabase/client";
import { debounce } from "@/lib/debounce";
import { headerIndex, parseCsv } from "@/lib/csv";
import type { CoveragePin } from "@/lib/types";

const PAGE = 50;
const CHUNK = 200;
const MAX_FILE = 2_000_000;

function roundCoord(n: number): number {
  return Math.round(n * 1e6) / 1e6;
}

export const CoverageManager = memo(function CoverageManager({
  brandId,
  onSelectionChange,
}: {
  brandId: string;
  onSelectionChange?: (ids: string[]) => void;
}) {
  const [rows, setRows] = useState<CoveragePin[]>([]);
  const [page, setPage] = useState(0);
  const [search, setSearch] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [info, setInfo] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [selected, setSelected] = useState<Set<string>>(() => new Set());
  const searchRef = useRef(search);
  searchRef.current = search;
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

  const canSelect = Boolean(onSelectionChange);

  function emit(next: Set<string>) {
    setSelected(next);
    onSelectionChange?.(Array.from(next));
  }

  async function load(offset: number, q = searchRef.current) {
    const supabase = createClient();
    let list = supabase
      .from("pincodes")
      .select("id, brand_id, platform, pincode, city, locality, store_name, lat, lon, tier, active")
      .eq("brand_id", brandId)
      .order("pincode")
      .range(offset, offset + PAGE - 1);
    if (q.trim()) {
      const term = `%${q.trim()}%`;
      list = list.or(`pincode.ilike.${term},locality.ilike.${term},store_name.ilike.${term}`);
    }
    const { data, error: qError } = await list;
    if (qError) setError(qError.message);
    else {
      setError(null);
      setRows((data as CoveragePin[]) ?? []);
    }
  }

  const debouncedLoad = useMemo(
    () =>
      debounce((q: string) => {
        setPage(0);
        void load(0, q);
      }, 180),
    [brandId],
  );

  useEffect(() => {
    void load(0, "");
    return () => debouncedLoad.cancel();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [brandId]);

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
    const next = new Set(selected);
    ids.forEach((id) => next.add(id));
    emit(next);
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

  async function toggleActive(pin: CoveragePin) {
    const supabase = createClient();
    await supabase.from("pincodes").update({ active: !pin.active }).eq("id", pin.id);
    await load(page * PAGE);
  }

  const showPager = page > 0 || rows.length === PAGE;

  return (
    <section>
      <form onSubmit={onSubmit} className="card grid gap-3 p-4 md:grid-cols-3">
        <input
          className="field"
          placeholder="Store name"
          value={form.store_name}
          onChange={(e) => setForm({ ...form, store_name: e.target.value })}
        />
        <input
          className="field"
          placeholder="Pincode"
          value={form.pincode}
          onChange={(e) => setForm({ ...form, pincode: e.target.value })}
          required
        />
        <input
          className="field"
          placeholder="Area / locality"
          value={form.locality}
          onChange={(e) => setForm({ ...form, locality: e.target.value })}
        />
        <input
          className="field"
          placeholder="Latitude"
          value={form.lat}
          onChange={(e) => setForm({ ...form, lat: e.target.value })}
          required
        />
        <input
          className="field"
          placeholder="Longitude"
          value={form.lon}
          onChange={(e) => setForm({ ...form, lon: e.target.value })}
          required
        />
        <select className="field" value={form.tier} onChange={(e) => setForm({ ...form, tier: e.target.value })}>
          <option value="hot">hot</option>
          <option value="warm">warm</option>
          <option value="cold">cold</option>
        </select>
        <button type="submit" disabled={busy} className="btn disabled:opacity-50">
          {busy ? "Saving…" : "Add location"}
        </button>
        <label className="btn-ghost cursor-pointer text-center text-sm">
          Upload CSV
          <input type="file" accept=".csv,text/csv" className="hidden" onChange={(e) => void onFile(e.target.files?.[0] ?? null)} />
        </label>
      </form>
      <p className="mt-2 text-xs text-ink/55">CSV: Store Name, Area, Pincode, Latitude, Longitude.</p>
      {error ? <p className="mt-3 text-sm text-oos">{error}</p> : null}
      {info ? <p className="mt-2 text-sm text-ink/70">{info}</p> : null}

      <div className="mt-4 flex flex-wrap gap-2">
        <input
          className="field"
          placeholder="Search pin / area / store"
          value={search}
          onChange={(e) => {
            const q = e.target.value;
            setSearch(q);
            debouncedLoad(q);
          }}
        />
        {canSelect ? (
          <>
            <button type="button" className="btn-ghost" onClick={selectVisible}>
              Select visible
            </button>
            <button type="button" className="btn-ghost" onClick={() => void selectMatching()}>
              Select matching search
            </button>
            <button type="button" className="btn-ghost" onClick={() => emit(new Set())}>
              Clear selection
            </button>
            <span className="self-center text-sm text-ink/60">{selected.size} selected</span>
          </>
        ) : null}
      </div>

      <div className="table-wrap mt-4">
        <table className="data-table">
          <thead>
            <tr>
              {canSelect ? <th>Scrape</th> : null}
              <th>Store</th>
              <th>Pin</th>
              <th>Area</th>
              <th>Lat / lon</th>
              <th>Active</th>
            </tr>
          </thead>
          <tbody>
            {rows.length === 0 ? (
              <tr>
                <td className="empty-cell" colSpan={6}>
                  No locations yet. Upload blinkit_pune_stores.csv or add lat/lon by hand.
                </td>
              </tr>
            ) : (
              rows.map((pin) => (
                <tr key={pin.id}>
                  {canSelect ? (
                    <td>
                      <input type="checkbox" checked={selected.has(pin.id)} onChange={() => toggle(pin.id)} />
                    </td>
                  ) : null}
                  <td>{pin.store_name}</td>
                  <td>
                    <a className="link" href={`/pins/${pin.pincode}`}>
                      {pin.pincode}
                    </a>
                  </td>
                  <td>{pin.locality}</td>
                  <td className="tabular">
                    {pin.lat}, {pin.lon}
                  </td>
                  <td>
                    <button type="button" className="link" onClick={() => void toggleActive(pin)}>
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
            className="btn-ghost disabled:opacity-40"
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
            className="btn-ghost disabled:opacity-40"
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
