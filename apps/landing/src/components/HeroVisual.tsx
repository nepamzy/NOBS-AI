import { Bot, Clapperboard, Film, Sparkles, SquarePlay } from "lucide-react";
import type { ReactNode } from "react";

// Stand-in for the mockups' stock photography / mascot art (hero shots of
// people, the robot mascot, dashboard screenshots) — this session doesn't
// have the original source images. Same layout/position as the mockups
// (a central panel ringed by small floating badges) so swapping in real
// photos or AI-generated art later is a src-only change, not a rebuild.
// See the "Team & photos" cost warning in chat before any of those get
// generated.
export function HeroVisual({
  icon: Icon = Bot,
  className = "",
  children,
}: {
  icon?: typeof Bot;
  className?: string;
  children?: ReactNode;
}) {
  return (
    <div className={`relative flex items-center justify-center ${className}`}>
      <div className="glow-backdrop absolute inset-0 rounded-[2.5rem]" />

      <div className="relative flex h-full w-full max-w-sm items-center justify-center rounded-[2.5rem] border border-white/10 bg-gradient-to-br from-accent-600/20 via-panel to-panel">
        <div className="flex h-28 w-28 items-center justify-center rounded-3xl bg-gradient-to-br from-accent-600 to-accent-400 shadow-xl shadow-accent-600/30 sm:h-36 sm:w-36">
          <Icon size={56} className="text-white" />
        </div>

        <span className="absolute -left-4 top-6 flex h-12 w-12 items-center justify-center rounded-2xl border border-white/10 bg-panel shadow-lg sm:-left-6">
          <SquarePlay size={22} className="text-red-500" />
        </span>
        <span className="absolute -right-3 top-2 flex h-11 w-11 items-center justify-center rounded-2xl border border-white/10 bg-panel shadow-lg sm:-right-5">
          <Film size={20} className="text-gold-400" />
        </span>
        <span className="absolute -bottom-3 left-1/4 flex h-11 w-11 items-center justify-center rounded-2xl border border-white/10 bg-panel shadow-lg">
          <Clapperboard size={20} className="text-accent-300" />
        </span>
        <span className="absolute -bottom-4 -right-2 flex h-12 w-12 items-center justify-center rounded-2xl border border-white/10 bg-panel shadow-lg">
          <Sparkles size={20} className="text-gold-400" />
        </span>

        {children}
      </div>
    </div>
  );
}
