"use client";

import { FormEvent, useEffect, useState } from "react";

import { createClient } from "@/lib/supabase/client";
import type { CoveragePin } from "@/lib/types";

const PAGE = 50;

type Lookup = Record<string, { city?: string; locality?: string; lat: number; lon: number }>;

export function CoverageManager({
  brandId,
  onCount,
}: {
  brandId: string;
  onCount?: (n: number) => void;
}) {
  const [rows, setRows] = useState<CoveragePin[]>([]);
  const [page, setPage] = useState(0);
  const [lookup, setLookup] = useState<Lookup>({});
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [form, setForm] = useState({
    pincode: "",
    city: "",
    locality: "",
    lat: "",
    lon: "",
    platform: "blinkit",
    tier: "hot",
  });

  async function load(offset: number) {
    const supabase = createClient();
    const [{ data, error: qError }, { count }] = await Promise.all([
      supabase
        .from("pincodes")
        .select("*")
        .eq("brand_id", brandId)
        .order("pincode")
        .range(offset, offset + PAGE - 1),
      supabase.from("pincodes").select("id", { count: "exact", head: true }).eq("brand_id", brandId),
    ]);
    if (qError) setError(qError.message);
    else {
      setRows((data as CoveragePin[]) ?? []);
      onCount?.(count ?? 0);
    }
  }

  useEffect(() => {
    void fetch("/in_pincode_lookup.example.json")
      .then((r) => r.json())
      .then((j) => setLookup(j as Lookup))
      .catch(() => undefined);
    void load(0);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [brandId]);

  function applyLookup(pincode: string) {
    const hit = lookup[pincode];
    if (!hit) return;
    setForm((prev) => ({
      ...prev,
      pincode,
      city: hit.city ?? prev.city,
      locality: hit.locality ?? prev.locality,
      lat: String(hit.lat),
      lon: String(hit.lon),
    }));
  }

  async function onSubmit(event: FormEvent) {
    event.preventDefault();
    setBusy(true);
    setError(null);
    const lat = Number(form.lat);
    const lon = Number(form.lon);
    if (!Number.isFinite(lat) || !Number.isFinite(lon)) {
      setError("Latitude and longitude must be numbers");
      setBusy(false);
      return;
    }
    const supabase = createClient();
    const { error: insertError } = await supabase.from("pincodes").insert({
      brand_id: brandId,
      platform: form.platform,
      pincode: form.pincode.trim(),
      city: form.city || null,
      locality: form.locality || null,
      lat,
      lon,
      tier: form.tier,
    });
    setBusy(false);
    if (insertError) {
      setError(insertError.message);
      return;
    }
    setForm({ ...form, pincode: "", city: "", locality: "", lat: "", lon: "" });
    await load(page * PAGE);
  }

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
          placeholder="Pincode (e.g. 560034)"
          value={form.pincode}
          onChange={(e) => setForm({ ...form, pincode: e.target.value })}
          onBlur={(e) => applyLookup(e.target.value.trim())}
          required
        />
        <input
          className="rounded-lg border border-ink/15 px-3 py-2"
          placeholder="City"
          value={form.city}
          onChange={(e) => setForm({ ...form, city: e.target.value })}
        />
        <input
          className="rounded-lg border border-ink/15 px-3 py-2"
          placeholder="Locality"
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
        <input className="rounded-lg border border-ink/15 px-3 py-2" value={form.platform} readOnly />
        <button type="submit" disabled={busy} className="rounded-full bg-ink px-4 py-2 text-lime disabled:opacity-50">
          {busy ? "Saving…" : "Add pincode"}
        </button>
      </form>
      {error ? <p className="mt-3 text-sm text-oos">{error}</p> : null}

      <div className="mt-4 overflow-x-auto rounded-2xl border border-ink/10 bg-white/70">
        <table className="w-full text-left text-sm">
          <thead className="bg-ink/5 text-ink/60">
            <tr>
              <th className="px-3 py-2">Pin</th>
              <th className="px-3 py-2">City</th>
              <th className="px-3 py-2">Lat / lon</th>
              <th className="px-3 py-2">Tier</th>
              <th className="px-3 py-2">Active</th>
            </tr>
          </thead>
          <tbody>
            {rows.length === 0 ? (
              <tr>
                <td className="px-3 py-4 text-ink/50" colSpan={5}>
                  No pincodes yet. Use a real pin (not 000001) with latitude and longitude.
                </td>
              </tr>
            ) : (
              rows.map((pin) => (
                <tr key={pin.id} className="border-t border-ink/5">
                  <td className="px-3 py-2">
                    <a className="underline" href={`/pins/${pin.pincode}`}>
                      {pin.pincode}
                    </a>
                  </td>
                  <td className="px-3 py-2">{pin.city}</td>
                  <td className="px-3 py-2 tabular">
                    {pin.lat}, {pin.lon}
                  </td>
                  <td className="px-3 py-2">{pin.tier}</td>
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
              void load(next * PAGE);
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
              void load(next * PAGE);
            }}
          >
            Next page
          </button>
        </div>
      ) : null}
    </section>
  );
}
