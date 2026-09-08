import { createClient } from "@/lib/supabase/server";

export async function currentBrandId(): Promise<string | null> {
  const supabase = await createClient();
  const {
    data: { user },
  } = await supabase.auth.getUser();
  if (!user) return null;
  const { data } = await supabase
    .from("brand_members")
    .select("brand_id")
    .eq("user_id", user.id)
    .limit(1)
    .maybeSingle();
  return data?.brand_id ?? null;
}
