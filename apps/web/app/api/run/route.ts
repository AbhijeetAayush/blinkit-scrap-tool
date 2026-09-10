import { qstashTokenProblem } from "@/lib/qstash-token";
import { currentBrandId } from "@/lib/brand";
import { createClient } from "@/lib/supabase/server";
import { NextResponse } from "next/server";

export const maxDuration = 120;

async function chunkIn(table: string, ids: string[], brandId: string): Promise<string[]> {
  const supabase = await createClient();
  const found: string[] = [];
  for (let i = 0; i < ids.length; i += 100) {
    const slice = ids.slice(i, i + 100);
    const { data, error } = await supabase.from(table).select("id").eq("brand_id", brandId).in("id", slice);
    if (error) throw new Error(error.message);
    found.push(...((data ?? []) as { id: string }[]).map((r) => r.id));
  }
  return found;
}

function dispatchClientError(text: string): string | null {
  try {
    const parsed = JSON.parse(text) as {
      status?: string;
      error?: string;
      remaining?: number;
      needed?: number;
      pages?: number;
    };
    if (parsed.status === "budget") {
      return `Not enough daily search budget for ${parsed.pages} searches (need ${parsed.needed}, remaining ${parsed.remaining}). Select fewer rows.`;
    }
    if (parsed.status === "error") {
      return parsed.error || "Dispatch rejected the run";
    }
  } catch {
    return null;
  }
  return null;
}

export async function POST(request: Request) {
  const brandId = await currentBrandId();
  if (!brandId) {
    return NextResponse.json({ error: "unauthorized" }, { status: 401 });
  }

  let body: { keyword_ids?: unknown; pincode_ids?: unknown } = {};
  try {
    body = (await request.json()) as { keyword_ids?: unknown; pincode_ids?: unknown };
  } catch {
    return NextResponse.json({ error: "JSON body required" }, { status: 400 });
  }
  const keywordIds = Array.isArray(body.keyword_ids) ? body.keyword_ids.map(String) : [];
  const pincodeIds = Array.isArray(body.pincode_ids) ? body.pincode_ids.map(String) : [];
  if (!keywordIds.length || !pincodeIds.length) {
    return NextResponse.json({ error: "Select at least one keyword and one location" }, { status: 400 });
  }

  let ownedKeywords: string[];
  let ownedPins: string[];
  try {
    ownedKeywords = await chunkIn("keywords", keywordIds, brandId);
    ownedPins = await chunkIn("pincodes", pincodeIds, brandId);
  } catch (err) {
    return NextResponse.json(
      { error: err instanceof Error ? err.message : "Could not verify selection. Apply migration 0003 if keywords table is missing." },
      { status: 500 },
    );
  }
  if (ownedKeywords.length !== keywordIds.length || ownedPins.length !== pincodeIds.length) {
    return NextResponse.json({ error: "Selection includes ids that are not in your brand" }, { status: 400 });
  }

  const dispatchUrl = process.env.DISPATCH_URL;
  const token = process.env.QSTASH_TOKEN;
  const qstashUrl = (process.env.QSTASH_URL || "https://qstash.upstash.io").replace(/\/$/, "");
  const runSecret = process.env.MANUAL_RUN_SECRET;
  if (!dispatchUrl) {
    return NextResponse.json({ error: "DISPATCH_URL missing in apps/web/.env.local" }, { status: 500 });
  }

  const payload = {
    slot_kind: "manual",
    brand_id: brandId,
    keyword_ids: ownedKeywords,
    pincode_ids: ownedPins,
  };

  if (runSecret) {
    const res = await fetch(dispatchUrl.replace(/\/$/, ""), {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "x-run-secret": runSecret,
      },
      body: JSON.stringify(payload),
    });
    const text = await res.text();
    if (!res.ok) {
      return NextResponse.json(
        { error: `Dispatch ${res.status}: ${text.slice(0, 280)}`, upstream: res.status },
        { status: 502 },
      );
    }
    const dispatchError = dispatchClientError(text);
    if (dispatchError) {
      return NextResponse.json({ error: dispatchError }, { status: 400 });
    }
    let runId: string | undefined;
    try {
      const parsed = JSON.parse(text) as { run_id?: string };
      runId = parsed.run_id;
    } catch {
      runId = undefined;
    }
    return NextResponse.json({ ok: true, via: "dispatch", run_id: runId, body: text.slice(0, 500) });
  }

  const tokenProblem = token ? qstashTokenProblem(token) : "QSTASH_TOKEN missing";
  const canQstash = Boolean(token) && !tokenProblem;

  if (canQstash) {
    const destination = dispatchUrl.replace(/\/$/, "");
    const res = await fetch(`${qstashUrl}/v2/publish/${destination}`, {
      method: "POST",
      headers: {
        Authorization: `Bearer ${token}`,
        "Content-Type": "application/json",
      },
      body: JSON.stringify(payload),
    });
    const text = await res.text();
    if (!res.ok) {
      return NextResponse.json(
        { error: `QStash ${res.status}: ${text.slice(0, 280)}`, upstream: res.status },
        { status: 502 },
      );
    }
    return NextResponse.json({ ok: true, via: "qstash", body: text.slice(0, 500) });
  }

  return NextResponse.json(
    { error: tokenProblem || "Set MANUAL_RUN_SECRET or a real QSTASH_TOKEN in apps/web/.env.local" },
    { status: 500 },
  );
}
