import type { Scene } from "../api/types";

export function StoryboardTimeline({
  scenes,
  targetDurationSeconds,
}: {
  scenes: Scene[];
  targetDurationSeconds: number;
}) {
  const planned = scenes.reduce((sum, s) => sum + s.duration_seconds, 0);
  const barTotal = Math.max(planned, targetDurationSeconds, 1);

  return (
    <div>
      <div className="flex items-baseline justify-between">
        <span className="text-sm text-white/70">
          {scenes.length} scene{scenes.length === 1 ? "" : "s"}
        </span>
        <span className="text-xs text-white/40">
          {planned}s planned / {targetDurationSeconds}s target
        </span>
      </div>

      <div className="mt-2 flex h-3 w-full gap-0.5 overflow-hidden rounded-full bg-white/5">
        {scenes.map((scene, i) => (
          <div
            key={scene.id}
            title={`Scene ${scene.order} — ${scene.duration_seconds}s`}
            className={i % 2 === 0 ? "bg-accent-500" : "bg-accent-400"}
            style={{ width: `${(scene.duration_seconds / barTotal) * 100}%` }}
          />
        ))}
        {planned < targetDurationSeconds && (
          <div
            title="Not yet planned"
            className="bg-white/5"
            style={{ width: `${((targetDurationSeconds - planned) / barTotal) * 100}%` }}
          />
        )}
      </div>
    </div>
  );
}
