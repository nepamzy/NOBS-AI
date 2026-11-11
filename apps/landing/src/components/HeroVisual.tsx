import { Clapperboard, Sparkles } from "lucide-react";
import { BrandIcon } from "./BrandIcon";

// Hero photo + the mockups' orbiting app-icon badges. Photos are real
// (AI-generated with Nobert's explicit go-ahead on the cost — see chat —
// then persisted permanently via his own Cloudinary account, since the
// generator's own URLs expire). The icon badges are real brand marks
// (BrandIcon) for YouTube/TikTok — the one thing with no official mark
// available is CapCut, so that badge stays a generic clapperboard/editing
// icon rather than a fabricated logo.
export function HeroVisual({
  photoSrc,
  photoAlt,
  className = "",
}: {
  photoSrc: string;
  photoAlt: string;
  className?: string;
}) {
  return (
    <div className={`relative flex items-center justify-center ${className}`}>
      <div className="glow-backdrop absolute inset-0 rounded-[2.5rem]" />

      <div className="relative h-full w-full max-w-sm overflow-hidden rounded-[2.5rem] border border-white/10 bg-panel">
        <img src={photoSrc} alt={photoAlt} className="h-full w-full object-cover" />
      </div>

      <span className="absolute -left-4 top-6 flex h-12 w-12 items-center justify-center rounded-2xl border border-white/10 bg-panel shadow-lg sm:-left-6">
        <BrandIcon name="youtube" size={22} />
      </span>
      <span className="absolute -right-3 top-2 flex h-11 w-11 items-center justify-center rounded-2xl border border-white/10 bg-black shadow-lg sm:-right-5">
        <BrandIcon name="tiktok" size={18} />
      </span>
      <span className="absolute -bottom-3 left-1/4 flex h-11 w-11 items-center justify-center rounded-2xl border border-white/10 bg-panel shadow-lg">
        <Clapperboard size={20} className="text-accent-300" />
      </span>
      <span className="absolute -bottom-4 -right-2 flex h-12 w-12 items-center justify-center rounded-2xl border border-white/10 bg-panel shadow-lg">
        <Sparkles size={20} className="text-gold-400" />
      </span>
    </div>
  );
}
