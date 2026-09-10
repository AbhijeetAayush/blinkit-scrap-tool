import { redirect } from "next/navigation";

import { SetupClient } from "@/app/setup/setup-client";
import { currentBrandId } from "@/lib/brand";

export default async function SetupPage() {
  const brandId = await currentBrandId();
  if (!brandId) redirect("/onboarding");
  return <SetupClient brandId={brandId} />;
}
