export function authUserMessage(message: string): string {
  const lower = message.toLowerCase();
  if (lower.includes("rate limit") || lower.includes("over_email")) {
    return "Supabase hit its confirmation-email limit (a few per hour on the free plan). If you already created this account, use Sign in. For local testing: Authentication → Providers → Email → turn Confirm email off, then sign in.";
  }
  if (lower.includes("already registered") || lower.includes("user already")) {
    return "That email already has an account. Sign in instead.";
  }
  if (lower.includes("email not confirmed")) {
    return "This account exists but the email is not confirmed. Confirm it under Authentication → Users, or turn Confirm email off, then sign in.";
  }
  return message;
}

export function isSignupRetryError(message: string): boolean {
  const lower = message.toLowerCase();
  return (
    lower.includes("rate limit") ||
    lower.includes("over_email") ||
    lower.includes("already registered") ||
    lower.includes("user already")
  );
}
