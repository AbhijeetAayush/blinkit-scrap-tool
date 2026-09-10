"use client";

import { useCallback, useState } from "react";

import { CoverageManager } from "@/components/coverage-manager";
import { KeywordManager } from "@/components/keyword-manager";
import { RunNowButton } from "@/components/run-now-button";
import { SetupStepper } from "@/components/setup-stepper";

export function SetupClient({ brandId }: { brandId: string }) {
  const [keywordIds, setKeywordIds] = useState<string[]>([]);
  const [pinIds, setPinIds] = useState<string[]>([]);
  const onKeywords = useCallback((ids: string[]) => setKeywordIds(ids), []);
  const onPins = useCallback((ids: string[]) => setPinIds(ids), []);

  const pages = keywordIds.length * pinIds.length;
  const canRun = keywordIds.length > 0 && pinIds.length > 0;

  return (
    <div className="space-y-9">
      <SetupStepper current="setup" />
      <header>
        <p className="text-xs font-medium uppercase tracking-[0.18em] text-moss">Harvest</p>
        <h1 className="mt-1 font-display text-3xl tracking-tight">Keywords and locations</h1>
        <p className="mt-1 max-w-2xl text-ink/70">
          Upload CSVs or add rows by hand. Check the keywords and stores you want, then run. Every product on those
          Blinkit search pages is saved.
        </p>
      </header>

      <section>
        <h2 className="font-display text-xl">Keywords</h2>
        <p className="mb-3 text-sm text-ink/60">Upload keywords.csv (header Keyword) or type one. Then check rows to scrape.</p>
        <KeywordManager brandId={brandId} onSelectionChange={onKeywords} />
      </section>

      <section>
        <h2 className="font-display text-xl">Locations</h2>
        <p className="mb-3 text-sm text-ink/60">
          Upload blinkit_pune_stores.csv (Store Name, Area, Pincode, Latitude, Longitude) or add lat/lon.
        </p>
        <CoverageManager brandId={brandId} onSelectionChange={onPins} />
      </section>

      <section className="card p-5">
        <h2 className="font-display text-xl">Run scrape</h2>
        {!canRun ? (
          <p className="mt-2 text-sm text-ink/60">Check at least one keyword and one location.</p>
        ) : (
          <p className="mt-2 text-sm text-ink/60">
            About {pages} searches against the daily search budget ({keywordIds.length} keywords × {pinIds.length}{" "}
            locations). Wait until the button leaves Working… then open Shelf.
          </p>
        )}
        <div className="mt-4">
          {canRun ? (
            <RunNowButton brandId={brandId} keywordIds={keywordIds} pincodeIds={pinIds} pages={pages} />
          ) : null}
        </div>
      </section>
    </div>
  );
}
