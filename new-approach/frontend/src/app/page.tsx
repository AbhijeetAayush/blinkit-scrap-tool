"use client";

import { useEffect } from "react";
import { useRouter } from "next/navigation";

import { getToken } from "@/lib/auth";

export default function HomePage() {
  const router = useRouter();

  useEffect(() => {
    router.replace(getToken() ? "/runs" : "/login");
  }, [router]);

  return (
    <main className="flex min-h-screen items-center justify-center text-sm text-zinc-500">
      Redirecting…
    </main>
  );
}
