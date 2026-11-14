import { useSlow } from "../hooks/useSlow";

export function LoadingState() {
  // The API runs on a plan that sleeps after 15 quiet minutes; the first
  // request after that takes up to a minute. Say so rather than just spinning.
  const slow = useSlow(true, 4000);
  return (
    <div className="flex items-center gap-2 text-sm text-white/40">
      <span className="h-3 w-3 shrink-0 animate-spin rounded-full border-2 border-white/20 border-t-accent-500" />
      {slow
        ? "Still loading — the server may be waking up after a quiet spell (it can take up to a minute)…"
        : "Loading…"}
    </div>
  );
}
