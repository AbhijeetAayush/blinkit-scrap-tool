export function normalizeKeyword(raw: string): string | null {
  const query = raw.trim().replace(/\s+/g, " ").toLowerCase();
  if (!query) return null;
  if (query === "others") return null;
  if (query.length < 3) return null;
  return query;
}

export function uniqueKeywords(values: string[]): string[] {
  const seen = new Set<string>();
  const out: string[] = [];
  for (const raw of values) {
    const query = normalizeKeyword(raw);
    if (!query || seen.has(query)) continue;
    seen.add(query);
    out.push(query);
  }
  return out;
}
