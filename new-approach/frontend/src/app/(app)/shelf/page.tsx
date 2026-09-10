"use client";

import { FormEvent, useCallback, useEffect, useState } from "react";

import { api, ApiError } from "@/lib/api-client";
import { packLabel, shelfRowKey, unitPrice } from "@/lib/shelf";
import type { ShelfListResponse, ShelfRow } from "@/lib/types";

export default function ShelfPage() {
  const [items, setItems] = useState<ShelfRow[]>([]);
  const [platform, setPlatform] = useState("blinkit");
  const [pincode, setPincode] = useState("");
  const [q, setQ] = useState("");
  const [merchantId, setMerchantId] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  const load = useCallback(async () => {
    setBusy(true);
    setError(null);
    try {
      const params = new URLSearchParams();
      if (platform) params.set("platform", platform);
      if (pincode.trim()) params.set("pincode", pincode.trim());
      if (q.trim()) params.set("q", q.trim());
      if (merchantId.trim()) params.set("merchant_id", merchantId.trim());
      params.set("limit", "200");
      const res = await api<ShelfListResponse>(`/shelf?${params.toString()}`);
      setItems(res.items);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Failed to load shelf");
    } finally {
      setBusy(false);
    }
  }, [merchantId, pincode, platform, q]);

  useEffect(() => {
    void load();
  }, [load]);

  function onFilter(e: FormEvent) {
    e.preventDefault();
    void load();
  }

  return (
    <div className="space-y-6">
      <header>
        <h1 className="text-2xl font-semibold tracking-tight">Shelf</h1>
        <p className="mt-1 text-sm text-zinc-500">
          Latest harvest observations — same fields as before (price, pack, rank, ₹/kg, stock, ads).
        </p>
      </header>

      <form onSubmit={onFilter} className="flex flex-wrap gap-2">
        <select
          className="input w-auto"
          value={platform}
          onChange={(e) => setPlatform(e.target.value)}
        >
          <option value="blinkit">blinkit</option>
        </select>
        <input
          className="input max-w-[8rem]"
          placeholder="Pincode"
          value={pincode}
          onChange={(e) => setPincode(e.target.value)}
        />
        <input
          className="input max-w-xs"
          placeholder="Search name or query"
          value={q}
          onChange={(e) => setQ(e.target.value)}
        />
        <input
          className="input max-w-xs"
          placeholder="Merchant id"
          value={merchantId}
          onChange={(e) => setMerchantId(e.target.value)}
        />
        <button className="btn btn-primary" type="submit" disabled={busy}>
          {busy ? "Loading…" : "Apply"}
        </button>
      </form>

      {error ? <p className="text-sm text-red-600">{error}</p> : null}

      <div className="table-wrap">
        <table className="data">
          <thead>
            <tr>
              <th>Name</th>
              <th>Brand</th>
              <th>Category</th>
              <th>Pack</th>
              <th>MRP</th>
              <th>Selling</th>
              <th>Off %</th>
              <th>Ad</th>
              <th>Rating</th>
              <th>Reviews</th>
              <th>ETA</th>
              <th>Store</th>
              <th>Pin</th>
              <th>Keyword</th>
              <th>Stock</th>
              <th>Rank</th>
              <th>₹/kg</th>
              <th>Image</th>
            </tr>
          </thead>
          <tbody>
            {items.length === 0 ? (
              <tr>
                <td colSpan={18} className="text-zinc-500">
                  No shelf rows.
                </td>
              </tr>
            ) : (
              items.map((row) => (
                <tr key={shelfRowKey(row)}>
                  <td className="max-w-[14rem]">
                    {row.product_url ? (
                      <a
                        className="text-sky-700 underline"
                        href={row.product_url}
                        target="_blank"
                        rel="noreferrer"
                      >
                        {row.sku_name}
                      </a>
                    ) : (
                      row.sku_name
                    )}
                  </td>
                  <td>{row.brand_name ?? "—"}</td>
                  <td className="max-w-[12rem] truncate">
                    {row.category_path?.length ? row.category_path.join(" › ") : "—"}
                  </td>
                  <td>{packLabel(row)}</td>
                  <td className="tabular-nums">{row.mrp ?? "—"}</td>
                  <td className="tabular-nums">{row.selling_price ?? "—"}</td>
                  <td className="tabular-nums">{row.discount_percent ?? "—"}</td>
                  <td>{row.is_sponsored ? "ad" : "—"}</td>
                  <td className="tabular-nums">{row.rating ?? "—"}</td>
                  <td className="tabular-nums">{row.rating_count ?? "—"}</td>
                  <td>
                    {row.delivery_time_text ??
                      (row.delivery_promise_min != null ? `${row.delivery_promise_min} mins` : "—")}
                  </td>
                  <td className="max-w-[10rem] truncate">{row.merchant_id}</td>
                  <td>{row.pincode}</td>
                  <td>{row.search_query || "—"}</td>
                  <td>
                    <span
                      className={
                        row.availability === "in_stock"
                          ? "badge badge-done"
                          : "badge badge-error"
                      }
                    >
                      {row.availability === "in_stock" ? "in" : row.availability}
                    </span>
                  </td>
                  <td className="tabular-nums">
                    {row.shelf_position ?? row.organic_rank ?? "—"}
                  </td>
                  <td className="tabular-nums">{unitPrice(row)}</td>
                  <td>
                    {row.image_url ? (
                      // eslint-disable-next-line @next/next/no-img-element
                      <img
                        src={row.image_url}
                        alt=""
                        className="h-10 w-10 rounded object-cover"
                      />
                    ) : (
                      "—"
                    )}
                  </td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}
