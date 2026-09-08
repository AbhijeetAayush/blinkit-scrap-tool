"use client";

import { FormEvent, useEffect, useState } from "react";

import { createClient } from "@/lib/supabase/client";
import type { Sku, SkuRole } from "@/lib/types";

const PAGE = 50;

export function SkuManager({
  brandId,
  onCount,
}: {
  brandId: string;
  onCount?: (n: number) => void;
}) {
  const [rows, setRows] = useState<Sku[]>([]);
  const [page, setPage] = useState(0);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [editingId, setEditingId] = useState<string | null>(null);
  const [form, setForm] = useState({
    sku_role: "self" as SkuRole,
    display_name: "",
    search_query: "",
    brand_name: "",
    pack_raw: "",
    pack_ml: "",
    kvi_flag: true,
    blinkit_product_id: "",
  });

  async function load(offset: number) {
    const supabase = createClient();
    const [{ data, error: qError }, { count }] = await Promise.all([
      supabase
        .from("skus")
        .select("*")
        .eq("brand_id", brandId)
        .order("created_at", { ascending: false })
        .range(offset, offset + PAGE - 1),
      supabase.from("skus").select("id", { count: "exact", head: true }).eq("brand_id", brandId),
    ]);
    if (qError) setError(qError.message);
    else {
      setRows((data as Sku[]) ?? []);
      onCount?.(count ?? 0);
    }
  }

  useEffect(() => {
    void load(0);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [brandId]);

  async function onSubmit(event: FormEvent) {
    event.preventDefault();
    setBusy(true);
    setError(null);
    const supabase = createClient();
    const payload = {
      brand_id: brandId,
      sku_role: form.sku_role,
      display_name: form.display_name,
      search_query: form.search_query,
      brand_name: form.brand_name,
      pack_raw: form.pack_raw || null,
      pack_ml: form.pack_ml ? Number(form.pack_ml) : null,
      kvi_flag: form.kvi_flag,
      blinkit_product_id: form.blinkit_product_id || null,
    };
    const query = editingId
      ? supabase.from("skus").update(payload).eq("id", editingId)
      : supabase.from("skus").insert(payload);
    const { error: writeError } = await query;
    setBusy(false);
    if (writeError) {
      setError(writeError.message);
      return;
    }
    setEditingId(null);
    setForm({ ...form, display_name: "", search_query: "", pack_raw: "", pack_ml: "", blinkit_product_id: "" });
    await load(page * PAGE);
  }

  async function toggleActive(sku: Sku) {
    const supabase = createClient();
    await supabase.from("skus").update({ active: !sku.active }).eq("id", sku.id);
    await load(page * PAGE);
  }

  function startEdit(sku: Sku) {
    setEditingId(sku.id);
    setForm({
      sku_role: sku.sku_role,
      display_name: sku.display_name,
      search_query: sku.search_query,
      brand_name: sku.brand_name,
      pack_raw: sku.pack_raw ?? "",
      pack_ml: sku.pack_ml != null ? String(sku.pack_ml) : "",
      kvi_flag: sku.kvi_flag,
      blinkit_product_id: sku.blinkit_product_id ?? "",
    });
  }

  const showPager = page > 0 || rows.length === PAGE;

  return (
    <section>
      <form onSubmit={onSubmit} className="grid gap-3 rounded-2xl border border-ink/10 bg-white/60 p-4 md:grid-cols-3">
        <select
          className="rounded-lg border border-ink/15 px-3 py-2"
          value={form.sku_role}
          onChange={(e) => setForm({ ...form, sku_role: e.target.value as SkuRole })}
        >
          <option value="self">Self</option>
          <option value="brand_competitor">Brand competitor</option>
        </select>
        <input
          className="rounded-lg border border-ink/15 px-3 py-2"
          placeholder="Display name"
          value={form.display_name}
          onChange={(e) => setForm({ ...form, display_name: e.target.value })}
          required
        />
        <input
          className="rounded-lg border border-ink/15 px-3 py-2"
          placeholder="Search query (what you type on Blinkit)"
          value={form.search_query}
          onChange={(e) => setForm({ ...form, search_query: e.target.value })}
          required
        />
        <input
          className="rounded-lg border border-ink/15 px-3 py-2"
          placeholder="Brand name on pack"
          value={form.brand_name}
          onChange={(e) => setForm({ ...form, brand_name: e.target.value })}
          required
        />
        <input
          className="rounded-lg border border-ink/15 px-3 py-2"
          placeholder="Pack (5 kg / 500 ml)"
          value={form.pack_raw}
          onChange={(e) => setForm({ ...form, pack_raw: e.target.value })}
        />
        <input
          className="rounded-lg border border-ink/15 px-3 py-2"
          placeholder="pack_ml (liquids only)"
          value={form.pack_ml}
          onChange={(e) => setForm({ ...form, pack_ml: e.target.value })}
        />
        <input
          className="rounded-lg border border-ink/15 px-3 py-2"
          placeholder="Blinkit product id (optional)"
          value={form.blinkit_product_id}
          onChange={(e) => setForm({ ...form, blinkit_product_id: e.target.value })}
        />
        <label className="flex items-center gap-2 text-sm">
          <input
            type="checkbox"
            checked={form.kvi_flag}
            onChange={(e) => setForm({ ...form, kvi_flag: e.target.checked })}
          />
          KVI
        </label>
        <button type="submit" disabled={busy} className="rounded-full bg-ink px-4 py-2 text-lime disabled:opacity-50">
          {busy ? "Saving…" : editingId ? "Save SKU" : "Add SKU"}
        </button>
      </form>
      {error ? <p className="mt-3 text-sm text-oos">{error}</p> : null}

      <div className="mt-4 overflow-x-auto rounded-2xl border border-ink/10 bg-white/70">
        <table className="w-full text-left text-sm">
          <thead className="bg-ink/5 text-ink/60">
            <tr>
              <th className="px-3 py-2">Name</th>
              <th className="px-3 py-2">Role</th>
              <th className="px-3 py-2">Query</th>
              <th className="px-3 py-2">Pack</th>
              <th className="px-3 py-2">Active</th>
              <th className="px-3 py-2"></th>
            </tr>
          </thead>
          <tbody>
            {rows.length === 0 ? (
              <tr>
                <td className="px-3 py-4 text-ink/50" colSpan={6}>
                  No SKUs yet. Add your product, then a competitor if you want rival prices.
                </td>
              </tr>
            ) : (
              rows.map((sku) => (
                <tr key={sku.id} className="border-t border-ink/5">
                  <td className="px-3 py-2">{sku.display_name}</td>
                  <td className="px-3 py-2">{sku.sku_role}</td>
                  <td className="px-3 py-2">{sku.search_query}</td>
                  <td className="px-3 py-2">{sku.pack_raw ?? sku.pack_ml ?? "—"}</td>
                  <td className="px-3 py-2">
                    <button type="button" className="underline" onClick={() => void toggleActive(sku)}>
                      {sku.active ? "on" : "off"}
                    </button>
                  </td>
                  <td className="px-3 py-2">
                    <button type="button" className="underline" onClick={() => startEdit(sku)}>
                      Edit
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
