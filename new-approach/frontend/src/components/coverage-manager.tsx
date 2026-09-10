"use client";

import { FormEvent, memo, useEffect, useMemo, useRef, useState } from "react";

import { api, ApiError } from "@/lib/api-client";
import { headerIndex, parseCsv } from "@/lib/csv";
import { debounce } from "@/lib/debounce";
import type { ItemsResponse, Location } from "@/lib/types";

const PAGE = 50;
const CHUNK = 200;
const MAX_FILE = 2_000_000;

function roundCoord(n: number): number {
  return Math.round(n * 1e6) / 1e6;
}

type BulkItem = {
  platform: string;
  pincode: string;
  lat: number;
  lon: number;
  store_name: string | null;
};

type BulkResponse = { read: number; saved: number; skipped: number };
type IdsResponse = { ids: string[] };

export const CoverageManager = memo(function CoverageManager({
  onSelectionChange,
}: {
  onSelectionChange?: (ids: string[]) => void;
}) {
  const [rows, setRows] = useState<Location[]>([]);
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
    lat: "",
    lon: "",
    platform: "blinkit",
  });

  const canSelect = Boolean(onSelectionChange);

  function emit(next: Set<string>) {
    setSelected(next);
    onSelectionChange?.(Array.from(next));
  }

  async function load(offset: number, q = searchRef.current) {
    try {
      const params = new URLSearchParams({
        offset: String(offset),
        limit: String(PAGE),
        platform: "blinkit",
      });
      if (q.trim()) params.set("q", q.trim());
      const data = await api<ItemsResponse<Location>>(`/locations?${params}`);
      setError(null);
      setRows(data.items);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Failed to load locations");
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
      const params = new URLSearchParams({ limit: "2000", platform: "blinkit" });
      if (search.trim()) params.set("q", search.trim());
      const data = await api<IdsResponse>(`/locations/ids?${params}`);
      const ids = data.ids;
      if (ids.length > 50 && !window.confirm(`Select ${ids.length} locations?`)) return;
      const next = new Set(selected);
      ids.forEach((id) => next.add(id));
      emit(next);
      setInfo(`Selected ${ids.length} locations.`);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Failed to select matching");
    }
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
    try {
      await api<Location>("/locations", {
        method: "POST",
        body: JSON.stringify({
          platform: form.platform,
          pincode: form.pincode.trim(),
          lat,
          lon,
          store_name: form.store_name.trim() || null,
        }),
      });
      setForm({ ...form, store_name: "", pincode: "", lat: "", lon: "" });
      await load(page * PAGE);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Failed to add location");
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
      if (table.length < 2) {
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
        setError("CSV must include Pincode, Latitude, Longitude (Pune file format).");
        return;
      }
      const payloads: BulkItem[] = [];
      let skipped = 0;
      for (const row of table.slice(1)) {
        const lat = roundCoord(Number(row[latIdx]));
        const lon = roundCoord(Number(row[lonIdx]));
        const pincode = (row[pinIdx] || "").trim();
        if (!pincode || !Number.isFinite(lat) || !Number.isFinite(lon)) {
          skipped += 1;
          continue;
        }
        const store = storeIdx >= 0 ? (row[storeIdx] || "").trim() : "";
        const area = areaIdx >= 0 ? (row[areaIdx] || "").trim() : "";
        let storeName: string | null = null;
        if (store && area) storeName = `${store} · ${area}`;
        else if (store) storeName = store;
        else if (area) storeName = area;

        payloads.push({
          platform: "blinkit",
          pincode,
          lat,
          lon,
          store_name: storeName,
        });
      }
      let saved = 0;
      let apiSkipped = 0;
      for (let i = 0; i < payloads.length; i += CHUNK) {
        const chunk = payloads.slice(i, i + CHUNK);
        const res = await api<BulkResponse>("/locations/bulk", {
          method: "POST",
          body: JSON.stringify({ locations: chunk }),
        });
        saved += res.saved;
        apiSkipped += res.skipped;
      }
      const totalSkipped = skipped + apiSkipped;
      setInfo(
        `Saved ${saved} locations${totalSkipped ? `, skipped ${totalSkipped}` : ""}. Nothing is selected — check stores to scrape.`,
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

  async function toggleActive(pin: Location) {
    try {
      await api<Location>(`/locations/${pin.id}`, {
        method: "PATCH",
        body: JSON.stringify({ active: !pin.active }),
      });
      await load(page * PAGE);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Failed to update location");
    }
  }

  const showPager = page > 0 || rows.length === PAGE;
  const colSpan = canSelect ? 5 : 4;

  return (
    <section>
      <form
        onSubmit={onSubmit}
        className="grid gap-3 rounded border border-zinc-200 bg-white p-4 md:grid-cols-3"
      >
        <input
          className="input"
          placeholder="Store name"
          value={form.store_name}
          onChange={(e) => setForm({ ...form, store_name: e.target.value })}
        />
        <input
          className="input"
          placeholder="Pincode"
          value={form.pincode}
          onChange={(e) => setForm({ ...form, pincode: e.target.value })}
          required
        />
        <input
          className="input"
          placeholder="Latitude"
          value={form.lat}
          onChange={(e) => setForm({ ...form, lat: e.target.value })}
          required
        />
        <input
          className="input"
          placeholder="Longitude"
          value={form.lon}
          onChange={(e) => setForm({ ...form, lon: e.target.value })}
          required
        />
        <button type="submit" disabled={busy} className="btn btn-primary">
          {busy ? "Saving…" : "Add location"}
        </button>
        <label className="btn cursor-pointer text-center text-sm">
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
        CSV: Store Name, Area, Pincode, Latitude, Longitude.
      </p>
      {error ? <p className="mt-3 text-sm text-red-600">{error}</p> : null}
      {info ? <p className="mt-2 text-sm text-zinc-600">{info}</p> : null}

      <div className="mt-4 flex flex-wrap gap-2">
        <input
          className="input max-w-xs"
          placeholder="Search pin / store"
          value={search}
          onChange={(e) => {
            const q = e.target.value;
            setSearch(q);
            debouncedLoad(q);
          }}
        />
        {canSelect ? (
          <>
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
          </>
        ) : null}
      </div>

      <div className="table-wrap mt-4">
        <table className="data">
          <thead>
            <tr>
              {canSelect ? <th className="w-16">Scrape</th> : null}
              <th>Store</th>
              <th>Pin</th>
              <th>Lat / lon</th>
              <th className="w-20">Active</th>
            </tr>
          </thead>
          <tbody>
            {rows.length === 0 ? (
              <tr>
                <td className="text-zinc-500" colSpan={colSpan}>
                  No locations yet. Upload blinkit_pune_stores.csv or add lat/lon by hand.
                </td>
              </tr>
            ) : (
              rows.map((pin) => (
                <tr key={pin.id}>
                  {canSelect ? (
                    <td>
                      <input
                        type="checkbox"
                        checked={selected.has(pin.id)}
                        onChange={() => toggle(pin.id)}
                      />
                    </td>
                  ) : null}
                  <td>{pin.store_name ?? "—"}</td>
                  <td>{pin.pincode}</td>
                  <td className="tabular-nums">
                    {pin.lat}, {pin.lon}
                  </td>
                  <td>
                    <button
                      type="button"
                      className="text-sky-700 underline"
                      onClick={() => void toggleActive(pin)}
                    >
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
