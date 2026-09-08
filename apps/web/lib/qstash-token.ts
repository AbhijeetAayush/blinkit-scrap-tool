export function qstashTokenProblem(token: string): string | null {
  const trimmed = token.trim();
  if (!trimmed) return "QSTASH_TOKEN is empty in apps/web/.env.local";
  try {
    const json = JSON.parse(Buffer.from(trimmed, "base64").toString("utf8")) as {
      UserID?: string;
      Password?: string;
    };
    if (json?.UserID && json?.Password) {
      return "QSTASH_TOKEN is the Upstash Redis REST token. Open Upstash → QStash (not Redis) → copy the QStash token into apps/web/.env.local → restart npm run dev.";
    }
  } catch {
    /* JWT-shaped QStash tokens are valid */
  }
  return null;
}
