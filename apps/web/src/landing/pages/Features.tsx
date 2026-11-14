import { motion } from "framer-motion";
import {
  Heart,
  Star,
  TrendingUp,
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
    iconSrc: "/icons/video-creation.png",
    title: "AI Video Creation",
    body: "Turn your ideas into stunning videos with AI.",
    id: "creators",
  },
  {
    iconSrc: "/icons/smart-clipping.png",
    title: "Smart Clipping",
    body: "Find the best moments in a long video automatically.",
  },
  {
    iconSrc: "/icons/ai-robot.png",
    title: "AI Assistant",
    body: "Get help, ideas and suggestions while you create.",
  },
  {
    iconSrc: "/icons/custom-thumbnails.png",
    title: "Custom Thumbnails",
    body: "Create eye-catching thumbnails easily.",
  },
  {
    iconSrc: "/icons/direct-publishing.png",
    title: "Direct Publishing",
    body: "Upload straight to YouTube — more platforms on the way.",
    id: "businesses",
  },
  {
    iconSrc: "/icons/analytics.png",
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
                <img
                  src={f.iconSrc}
                  alt=""
                  width={64}
                  height={64}
                  loading="lazy"
                  decoding="async"
                  className="h-16 w-16 rounded-2xl"
                />
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
