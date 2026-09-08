"use client";

import { useState } from "react";

import { CoverageManager } from "@/components/coverage-manager";
import { RunNowButton } from "@/components/run-now-button";
import { SetupStepper } from "@/components/setup-stepper";
import { SkuManager } from "@/components/sku-manager";
import { useBrandId } from "@/lib/use-brand";

export default function SetupPage() {
  const { brandId, ready, error } = useBrandId();
  const [skuCount, setSkuCount] = useState(0);
  const [pinCount, setPinCount] = useState(0);

  if (!ready) {
    return <p className="text-ink/60">Loading your brand…</p>;
  }
  if (error) {
    return <p className="text-oos">{error}</p>;
  }
  if (!brandId) return null;

  const canRun = skuCount > 0 && pinCount > 0;

  return (
    <div className="space-y-10">
      <SetupStepper current="setup" />
      <header>
        <h1 className="font-display text-3xl">Add products and a pincode</h1>
        <p className="mt-1 text-ink/70">
          Stay on this page. Add at least one SKU and one real pincode, then run the scrape at the bottom.
        </p>
      </header>

      <div>
        <h2 className="font-display text-xl">SKUs</h2>
        <p className="mb-3 text-sm text-ink/60">Your listing first, then a brand competitor if you want rival prices.</p>
        <SkuManager brandId={brandId} onCount={setSkuCount} />
      </div>

      <div>
        <h2 className="font-display text-xl">Coverage</h2>
        <p className="mb-3 text-sm text-ink/60">One live pincode with lat/lon. Do not use 000001.</p>
        <CoverageManager brandId={brandId} onCount={setPinCount} />
      </div>

      <div className="rounded-2xl border border-ink/10 bg-white/70 p-5">
        <h2 className="font-display text-xl">Run scrape</h2>
        {!canRun ? (
          <p className="mt-2 text-sm text-ink/60">Add a SKU and a pincode above first. The grey Next page buttons only appear after 50 rows.</p>
        ) : (
          <p className="mt-2 text-sm text-ink/60">
            Click once, wait about a minute, then click again if the shelf is still empty (first run maps the store).
          </p>
        )}
        <div className="mt-4">
          {canRun ? <RunNowButton /> : null}
        </div>
      </div>
    </div>
  );
}
