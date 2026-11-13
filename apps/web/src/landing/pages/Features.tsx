import { motion } from "framer-motion";
import {
  BarChart3,
  Bot,
  Clapperboard,
  Heart,
  ImagePlus,
  Scissors,
  Star,
  TrendingUp,
  UploadCloud,
  Zap,
} from "lucide-react";
import { CommunityCta } from "../components/CommunityCta";
import { HeroVisual } from "../components/HeroVisual";
import { WhyChoose } from "../components/WhyChoose";
import { HERO_PHOTOS } from "../heroPhotos";

const fadeUp = {
  hidden: { opacity: 0, y: 20 },
  visible: { opacity: 1, y: 0 },
};

// "Coming Soon" on Analytics (CLAUDE.md: explicitly V3, not built) and
// Direct Publishing reworded to YouTube-only (TikTok isn't built) — see
// the "Overstated features" decision in chat.
const FEATURES = [
  {
    icon: Clapperboard,
    title: "AI Video Creation",
    body: "Turn your ideas into stunning videos with AI.",
    id: "creators",
  },
  {
    icon: Scissors,
    title: "Smart Clipping",
    body: "Find the best moments in a long video automatically.",
  },
  {
    icon: Bot,
    iconSrc: "/icons/ai-robot.png",
    title: "AI Assistant",
    body: "Get help, ideas and suggestions while you create.",
  },
  {
    icon: ImagePlus,
    title: "Custom Thumbnails",
    body: "Create eye-catching thumbnails easily.",
  },
  {
    icon: UploadCloud,
    title: "Direct Publishing",
    body: "Upload straight to YouTube — more platforms on the way.",
    id: "businesses",
  },
  {
    icon: BarChart3,
    title: "Analytics",
    body: "Track performance and grow faster.",
    comingSoon: true,
  },
] as const;

export function Features() {
  return (
    <>
      <section className="glow-backdrop relative overflow-hidden px-5 pb-16 pt-14 sm:pt-20">
        <div className="mx-auto grid max-w-6xl grid-cols-1 items-center gap-10 lg:grid-cols-[1.1fr_1fr]">
          <motion.div initial="hidden" animate="visible" variants={fadeUp} transition={{ duration: 0.5 }}>
            <span className="inline-flex items-center gap-1.5 rounded-full border border-accent-500/30 bg-accent-500/10 px-3 py-1 text-xs font-semibold text-accent-300">
              <Star size={12} />
              Powerful Features
            </span>
            <h1 className="mt-5 font-heading text-4xl font-bold leading-tight text-white sm:text-5xl">
              Everything You Need to <span className="text-gradient">Create Amazing</span> Videos
            </h1>
            <p className="mt-5 max-w-xl text-lg text-white/60">
              From idea to finished video, NOBS AI gives you the tools to make it — all in
              one place.
            </p>
            <div className="mt-7 flex flex-wrap items-center gap-x-8 gap-y-3 border-t border-white/10 pt-6 text-sm">
              <span className="flex items-center gap-2 text-white/70">
                <Zap size={16} className="text-gold-400" /> Save Time
              </span>
              <span className="flex items-center gap-2 text-white/70">
                <TrendingUp size={16} className="text-gold-400" /> Grow Bigger
              </span>
              <span className="flex items-center gap-2 text-white/70">
                <Heart size={16} className="text-gold-400" /> Work Smarter
              </span>
            </div>
          </motion.div>

          <motion.div
            initial={{ opacity: 0, scale: 0.9 }}
            animate={{ opacity: 1, scale: 1 }}
            transition={{ duration: 0.8, delay: 0.1 }}
          >
            <HeroVisual
              photoSrc={HERO_PHOTOS.headphonesWoman.src}
              photoAlt={HERO_PHOTOS.headphonesWoman.alt}
              className="h-[280px] sm:h-[340px]"
            />
          </motion.div>
        </div>
      </section>

      <section className="px-5 pb-16">
        <div className="mx-auto grid max-w-6xl grid-cols-1 gap-5 sm:grid-cols-2 lg:grid-cols-3">
          {FEATURES.map((f, i) => (
            <motion.div
              key={f.title}
              id={"id" in f ? f.id : undefined}
              initial="hidden"
              whileInView="visible"
              viewport={{ once: true, margin: "-60px" }}
              variants={fadeUp}
              transition={{ duration: 0.4, delay: i * 0.05 }}
              className="scroll-mt-24 rounded-2xl border border-white/10 bg-panel p-6"
            >
              <div className="flex items-center justify-between">
                {"iconSrc" in f ? (
                  <img src={f.iconSrc} alt="" className="h-11 w-11 rounded-xl" />
                ) : (
                  <span className="flex h-11 w-11 items-center justify-center rounded-xl bg-gradient-to-br from-accent-600 to-accent-400">
                    <f.icon size={20} className="text-white" />
                  </span>
                )}
                {"comingSoon" in f && f.comingSoon && (
                  <span className="rounded-full bg-gold-500/15 px-2.5 py-1 text-[10px] font-bold uppercase tracking-wide text-gold-400">
                    Coming Soon
                  </span>
                )}
              </div>
              <h3 className="mt-4 font-heading text-base font-semibold text-white">{f.title}</h3>
              <p className="mt-2 text-sm leading-relaxed text-white/55">{f.body}</p>
            </motion.div>
          ))}
        </div>
      </section>

      <section className="px-5 pb-16">
        <div className="mx-auto max-w-6xl">
          <WhyChoose title="Built for Creators, Designed for Growth" />
        </div>
      </section>

      <CommunityCta />
    </>
  );
}
