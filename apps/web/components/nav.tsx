"use client";

import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";

import { createClient } from "@/lib/supabase/client";

const LINKS = [
  { href: "/setup", label: "Setup" },
  { href: "/dashboard", label: "Shelf" },
  { href: "/alerts", label: "Alerts" },
  { href: "/runs", label: "Runs" },
];

export function Nav() {
  const pathname = usePathname();
  const router = useRouter();
  if (pathname === "/login") return null;

  async function signOut() {
    const supabase = createClient();
    await supabase.auth.signOut();
    router.push("/login");
    router.refresh();
  }

  return (
    <header className="border-b border-ink/10 bg-paper/80 backdrop-blur">
      <div className="mx-auto flex max-w-6xl items-center justify-between gap-4 px-4 py-3">
        <Link href="/setup" className="font-display text-lg tracking-tight">
          Brand shelf
        </Link>
        <nav className="flex flex-wrap items-center gap-4 text-sm">
          {LINKS.map((link) => (
            <Link
              key={link.href}
              href={link.href}
              prefetch
              className={pathname.startsWith(link.href) ? "font-semibold text-moss" : "text-ink/70"}
            >
              {link.label}
            </Link>
          ))}
          <button type="button" onClick={() => void signOut()} className="text-ink/50 hover:text-ink">
            Sign out
          </button>
        </nav>
      </div>
    </header>
  );
}
