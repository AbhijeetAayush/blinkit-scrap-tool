"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";

import { SignOutButton } from "@/components/sign-out-button";

const LINKS = [
  { href: "/setup", label: "Setup" },
  { href: "/dashboard", label: "Shelf" },
  { href: "/alerts", label: "Alerts" },
  { href: "/runs", label: "Runs" },
];

export function Nav() {
  const pathname = usePathname();
  if (pathname === "/login") return null;

  return (
    <header className="nav-bar">
      <div className="mx-auto flex max-w-6xl items-center justify-between gap-4 px-4 py-3">
        <Link href="/setup" prefetch className="font-display text-lg tracking-tight">
          Brand shelf
        </Link>
        <nav className="flex flex-wrap items-center gap-4 text-sm">
          {LINKS.map((link) => {
            const on = pathname.startsWith(link.href);
            return (
              <Link
                key={link.href}
                href={link.href}
                prefetch
                className={on ? "font-semibold text-moss" : "text-ink/60 hover:text-ink"}
              >
                {link.label}
              </Link>
            );
          })}
          <SignOutButton />
        </nav>
      </div>
    </header>
  );
}
