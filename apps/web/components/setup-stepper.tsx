"use client";

import Link from "next/link";

const STEPS = [
  { href: "/onboarding", label: "1. Brand" },
  { href: "/setup", label: "2. SKUs + pin" },
  { href: "/dashboard", label: "3. Shelf" },
] as const;

export function SetupStepper({ current }: { current: "onboarding" | "setup" | "dashboard" }) {
  return (
    <ol className="mb-8 flex flex-wrap gap-2 text-sm">
      {STEPS.map((step) => {
        const active =
          (current === "onboarding" && step.href === "/onboarding") ||
          (current === "setup" && step.href === "/setup") ||
          (current === "dashboard" && step.href === "/dashboard");
        return (
          <li key={step.href}>
            <Link
              href={step.href}
              className={`rounded-full px-3 py-1 ${active ? "bg-ink text-lime" : "border border-ink/15 text-ink/60"}`}
            >
              {step.label}
            </Link>
          </li>
        );
      })}
    </ol>
  );
}
