export const TERMINAL_RUN_STATUSES = new Set(["derived", "error", "budget", "halted"]);

export function isRunTerminal(status: string | null | undefined): boolean {
  return Boolean(status && TERMINAL_RUN_STATUSES.has(status));
}
