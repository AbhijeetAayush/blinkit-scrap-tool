"use client";

import { useState } from "react";

import { CoverageManager } from "@/components/coverage-manager";
import { KeywordManager } from "@/components/keyword-manager";
import { RunNowButton } from "@/components/run-now-button";
import { SetupStepper } from "@/components/setup-stepper";
import { useBrandId } from "@/lib/use-brand";

export default function SetupPage() {
  const { brandId, ready, error } = useBrandId();
  const [keywordIds, setKeywordIds] = useState<Set<string>>(new Set());
  const [pinIds, setPinIds] = useState<Set<string>>(new Set());

  if (!ready) {
    return <p className="text-ink/60">Loading your brand…</p>;
  }
  if (error) {
    return <p className="text-oos">{error}</p>;
  }
  if (!brandId) return null;

  const pages = keywordIds.size * pinIds.size;
  const canRun = keywordIds.size > 0 && pinIds.size > 0;

  return (
    <div className="space-y-10">
      <SetupStepper current="setup" />
      <header>
        <h1 className="font-display text-3xl">Keywords and locations</h1>
        <p className="mt-1 text-ink/70">
          Upload CSVs or add rows by hand. Check the keywords and stores you want, then run. Every product on those
          Blinkit search pages is saved.
        </p>
      </header>

      <div>
        <h2 className="font-display text-xl">Keywords</h2>
        <p className="mb-3 text-sm text-ink/60">Upload keywords.csv (header Keyword) or type one. Then check rows to scrape.</p>
        <KeywordManager
          brandId={brandId}
          selected={keywordIds}
          onSelectionChange={setKeywordIds}
        />
      </div>

      <div>
        <h2 className="font-display text-xl">Locations</h2>
        <p className="mb-3 text-sm text-ink/60">
          Upload blinkit_pune_stores.csv (Store Name, Area, Pincode, Latitude, Longitude) or add lat/lon.
        </p>
        <CoverageManager
          brandId={brandId}
          selected={pinIds}
          onSelectionChange={setPinIds}
        />
      </div>

      <div className="rounded-2xl border border-ink/10 bg-white/70 p-5">
        <h2 className="font-display text-xl">Run scrape</h2>
        {!canRun ? (
          <p className="mt-2 text-sm text-ink/60">Check at least one keyword and one location.</p>
        ) : (
          <p className="mt-2 text-sm text-ink/60">
            About {pages} ScrapingBee searches ({keywordIds.size} keywords × {pinIds.size} locations). Wait a minute,
            then open Shelf.
          </p>
        )}
        <div className="mt-4">
          {canRun ? (
            <RunNowButton keywordIds={[...keywordIds]} pincodeIds={[...pinIds]} pages={pages} />
          ) : null}
        </div>
      </div>
    </div>
  );
}
