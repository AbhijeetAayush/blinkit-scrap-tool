import { qstashTokenProblem } from "@/lib/qstash-token";
import { createClient } from "@/lib/supabase/server";
import { NextResponse } from "next/server";

export const maxDuration = 120;

export async function POST() {
  const supabase = await createClient();
  const {
    data: { user },
  } = await supabase.auth.getUser();
  if (!user) {
    return NextResponse.json({ error: "unauthorized" }, { status: 401 });
  }

  const dispatchUrl = process.env.DISPATCH_URL;
  const token = process.env.QSTASH_TOKEN;
  const qstashUrl = (process.env.QSTASH_URL || "https://qstash.upstash.io").replace(/\/$/, "");
  const runSecret = process.env.MANUAL_RUN_SECRET;
  if (!dispatchUrl) {
    return NextResponse.json({ error: "DISPATCH_URL missing in apps/web/.env.local" }, { status: 500 });
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
      body: JSON.stringify({ slot_kind: "manual" }),
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

  if (!runSecret) {
    return NextResponse.json(
      { error: tokenProblem || "Set MANUAL_RUN_SECRET or a real QSTASH_TOKEN in apps/web/.env.local" },
      { status: 500 },
    );
  }

  const res = await fetch(dispatchUrl.replace(/\/$/, ""), {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      "x-run-secret": runSecret,
    },
    body: JSON.stringify({ slot_kind: "manual" }),
  });
  const text = await res.text();
  if (!res.ok) {
    return NextResponse.json(
      { error: `Dispatch ${res.status}: ${text.slice(0, 280)}`, upstream: res.status },
      { status: 502 },
    );
  }
  return NextResponse.json({ ok: true, via: "dispatch", body: text.slice(0, 500) });
}
