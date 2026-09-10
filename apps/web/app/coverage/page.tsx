import { redirect } from "next/navigation";

import { CoverageManager } from "@/components/coverage-manager";
import { SetupStepper } from "@/components/setup-stepper";
import { currentBrandId } from "@/lib/brand";

export default async function CoveragePage() {
  const brandId = await currentBrandId();
  if (!brandId) redirect("/onboarding");
  return (
    <div>
      <SetupStepper current="setup" />
      <h1 className="font-display text-3xl tracking-tight">Coverage</h1>
      <p className="mt-1 text-ink/70">Add store locations. Check rows and run from Setup.</p>
      <div className="mt-6">
        <CoverageManager brandId={brandId} />
      </div>
    </div>
  );
}
