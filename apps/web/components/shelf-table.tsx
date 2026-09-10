import Link from "next/link";

import { packLabel, shelfRowKey, unitPrice } from "@/lib/shelf";
import type { LatestObservation } from "@/lib/types";

export function ShelfTable({
  rows,
  showPin = false,
}: {
  rows: LatestObservation[];
  showPin?: boolean;
}) {
  return (
    <div className="table-wrap">
      <table className="shelf-table">
        <thead>
          <tr>
            <th>Name</th>
            <th>Brand</th>
            <th>Pack</th>
            <th>MRP</th>
            <th>Selling</th>
            <th>Off %</th>
            <th>Ad</th>
            <th>Rating</th>
            <th>Reviews</th>
            <th>Store</th>
            {showPin ? <th>Pin</th> : null}
            <th>Keyword</th>
            <th>Stock</th>
            <th>Rank</th>
            <th>₹/kg</th>
          </tr>
        </thead>
        <tbody>
          {rows.length === 0 ? (
            <tr>
              <td className="empty-cell" colSpan={showPin ? 15 : 14}>
                No rows.
              </td>
            </tr>
          ) : (
            rows.map((row) => (
              <tr key={shelfRowKey(row)}>
                <td className="name-cell">{row.sku_name}</td>
                <td>{row.brand_name ?? "—"}</td>
                <td>{packLabel(row)}</td>
                <td className="tabular">{row.mrp ?? "—"}</td>
                <td className="tabular">{row.selling_price ?? "—"}</td>
                <td className="tabular">{row.discount_percent ?? "—"}</td>
                <td>{row.is_sponsored ? <span className="badge badge-ad">ad</span> : "—"}</td>
                <td className="tabular">{row.rating ?? "—"}</td>
                <td className="tabular">{row.rating_count ?? "—"}</td>
                <td className="store-cell">{row.merchant_id ?? "—"}</td>
                {showPin ? (
                  <td>
                    <Link className="link" href={`/pins/${row.pincode}`}>
                      {row.pincode}
                    </Link>
                  </td>
                ) : null}
                <td>{row.search_query || "—"}</td>
                <td>
                  <span className={row.availability === "in_stock" ? "badge badge-stock" : "badge badge-oos"}>
                    {row.availability === "in_stock" ? "in" : row.availability}
                  </span>
                </td>
                <td className="tabular">{row.shelf_position ?? row.organic_rank ?? "—"}</td>
                <td className="tabular">{unitPrice(row)}</td>
              </tr>
            ))
          )}
        </tbody>
      </table>
    </div>
  );
}
