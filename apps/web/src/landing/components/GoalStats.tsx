import { Globe2, PlaySquare, Users } from "lucide-react";

// The mockups show "1M+ Videos Created / 100K+ Happy Creators / 50+
// Countries" as current, hard stats. None of that is true yet — NOBS AI
// hasn't opened to the public and has zero outside users. Framed as goals
// instead, same way the About mockup itself already (correctly) labels its
// own stats "(Coming Soon)" / "(Goal)" / "(Target)" — see the "Fake stats"
// decision in chat.
const STATS = [
  { icon: PlaySquare, value: "1M+", label: "Videos", tag: "Goal" },
  { icon: Users, value: "100K+", label: "Creators", tag: "Coming Soon" },
  { icon: Globe2, value: "50+", label: "Countries", tag: "Target" },
] as const;

export function GoalStats({ className = "" }: { className?: string }) {
  return (
    <div className={`flex flex-wrap items-center gap-8 ${className}`}>
      {STATS.map((stat) => (
        <div key={stat.label} className="flex items-center gap-3">
          <span className="flex h-11 w-11 items-center justify-center rounded-xl bg-accent-500/15 text-accent-300">
            <stat.icon size={20} />
          </span>
          <div>
            <p className="font-heading text-xl font-bold text-white">
              {stat.value}{" "}
              <span className="align-middle text-[10px] font-semibold uppercase tracking-wide text-gold-400">
                {stat.tag}
              </span>
            </p>
            <p className="text-xs text-white/50">{stat.label}</p>
          </div>
        </div>
      ))}
    </div>
  );
}
