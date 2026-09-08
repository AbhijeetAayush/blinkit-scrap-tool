"use client";

import { SkuManager } from "@/components/sku-manager";
import { SetupStepper } from "@/components/setup-stepper";
import { useBrandId } from "@/lib/use-brand";

export default function SkusPage() {
  const { brandId, ready, error } = useBrandId();
  if (!ready) return <p className="text-ink/60">Loading…</p>;
  if (error) return <p className="text-oos">{error}</p>;
  if (!brandId) return null;
  return (
    <div>
      <SetupStepper current="setup" />
      <h1 className="font-display text-3xl">SKUs</h1>
      <p className="mt-1 text-ink/70">Your products and brand competitors. Use Setup to add a pin and run in one place.</p>
      <div className="mt-6">
        <SkuManager brandId={brandId} />
      </div>
    </div>
  );
}
