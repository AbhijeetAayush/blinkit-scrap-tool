"use client";

import { useEffect, useState } from "react";

import { createClient } from "@/lib/supabase/client";

export function useBrandId() {
  const [brandId, setBrandId] = useState<string | null>(null);
  const [ready, setReady] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const supabase = createClient();
    void (async () => {
      const {
        data: { user },
      } = await supabase.auth.getUser();
      if (!user) {
        window.location.href = "/login";
        return;
      }
      const { data: member, error: qError } = await supabase
        .from("brand_members")
        .select("brand_id")
        .eq("user_id", user.id)
        .limit(1)
        .maybeSingle();
      if (qError) {
        setError(qError.message);
        setReady(true);
        return;
      }
      if (!member) {
        window.location.href = "/onboarding";
        return;
      }
      setBrandId(member.brand_id);
      setReady(true);
    })();
  }, []);

  return { brandId, ready, error };
}
