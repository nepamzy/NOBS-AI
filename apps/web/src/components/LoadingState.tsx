export function LoadingState() {
  return (
    <div className="flex items-center gap-2 text-sm text-white/40">
      <span className="h-3 w-3 animate-spin rounded-full border-2 border-white/20 border-t-accent-500" />
      Loading…
    </div>
  );
}
