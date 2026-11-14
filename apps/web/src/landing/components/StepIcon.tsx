// Icon tile with the step number badge pinned to its corner — the same
// treatment on Home, Our Platform and How It Works.
export function StepIcon({ src, step, size = 56 }: { src: string; step: number; size?: number }) {
  return (
    <div className="relative inline-block">
      <img
        src={src}
        alt=""
        width={size}
        height={size}
        loading="lazy"
        decoding="async"
        className="rounded-2xl"
        style={{ width: size, height: size }}
      />
      <span className="absolute -bottom-2 -left-2 flex h-6 w-6 items-center justify-center rounded-full border-2 border-panel bg-gradient-to-br from-accent-600 to-accent-400 text-[11px] font-bold text-white">
        {step}
      </span>
    </div>
  );
}
