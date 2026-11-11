import { motion } from "framer-motion";
import {
  ArrowRight,
  CheckCircle2,
  Clapperboard,
  Lightbulb,
  Rocket,
  Wand2,
  Zap,
} from "lucide-react";
import { Link } from "react-router-dom";
import { CommunityCta } from "../components/CommunityCta";
import { GoalStats } from "../components/GoalStats";
import { HeroVisual } from "../components/HeroVisual";
import { WhyChoose } from "../components/WhyChoose";
import { HERO_PHOTOS } from "../heroPhotos";

const fadeUp = {
  hidden: { opacity: 0, y: 20 },
  visible: { opacity: 1, y: 0 },
};

const STEPS = [
  {
    step: 1,
    icon: Lightbulb,
    title: "Share Your Idea",
    body: "Tell us what you want to create.",
    tags: ["YouTube Video", "Faceless Channel"] as readonly string[] | undefined,
    checklist: undefined as readonly string[] | undefined,
  },
  {
    step: 2,
    icon: Wand2,
    title: "Let AI Work",
    body: "Our AI researches, writes scripts and plans your content.",
    tags: undefined as readonly string[] | undefined,
    checklist: ["Research", "Script", "Plan"] as readonly string[] | undefined,
  },
  {
    step: 3,
    icon: Clapperboard,
    title: "Create & Review",
    body: "Get high-quality videos with scenes, voice and more.",
    tags: undefined as readonly string[] | undefined,
    checklist: undefined as readonly string[] | undefined,
  },
  {
    step: 4,
    icon: Rocket,
    title: "Publish & Grow",
    body: "Download your video and share it to reach more people.",
    tags: undefined as readonly string[] | undefined,
    checklist: undefined as readonly string[] | undefined,
  },
] as const;

export function HowItWorks() {
  return (
    <>
      <section className="glow-backdrop relative overflow-hidden px-5 pb-16 pt-14 sm:pt-20">
        <div className="mx-auto grid max-w-6xl grid-cols-1 items-center gap-10 lg:grid-cols-[1.1fr_1fr]">
          <motion.div initial="hidden" animate="visible" variants={fadeUp} transition={{ duration: 0.5 }}>
            <span className="inline-flex items-center gap-1.5 rounded-full border border-accent-500/30 bg-accent-500/10 px-3 py-1 text-xs font-semibold text-accent-300">
              <Zap size={12} />
              Simple Process
            </span>
            <h1 className="mt-5 font-heading text-4xl font-bold leading-tight text-white sm:text-5xl">
              How It <span className="text-gradient">Works</span>
            </h1>
            <p className="mt-2 font-heading text-xl font-semibold text-white/90 sm:text-2xl">
              Go from an idea to a finished video in just <span className="text-gold-400">4 easy steps</span>!
            </p>
            <p className="mt-4 max-w-xl text-white/60">
              NOBS AI handles the hard work. You just bring the idea, and we turn it into a
              video.
            </p>
            <Link
              to="/waitlist"
              className="mt-7 inline-flex rounded-full bg-gradient-to-r from-gold-400 to-gold-500 px-7 py-3.5 text-sm font-semibold text-black shadow-lg shadow-gold-500/20 transition-transform hover:scale-[1.03]"
            >
              Join the Waitlist →
            </Link>
          </motion.div>

          <motion.div
            initial={{ opacity: 0, scale: 0.9 }}
            animate={{ opacity: 1, scale: 1 }}
            transition={{ duration: 0.8, delay: 0.1 }}
          >
            <HeroVisual
              photoSrc={HERO_PHOTOS.phoneMan.src}
              photoAlt={HERO_PHOTOS.phoneMan.alt}
              className="h-[280px] sm:h-[340px]"
            />
          </motion.div>
        </div>
      </section>

      <section className="px-5 pb-16">
        <div className="mx-auto grid max-w-6xl grid-cols-1 gap-6 sm:grid-cols-2 lg:grid-cols-4">
          {STEPS.map((s, i) => (
            <motion.div
              key={s.title}
              initial="hidden"
              whileInView="visible"
              viewport={{ once: true, margin: "-60px" }}
              variants={fadeUp}
              transition={{ duration: 0.4, delay: i * 0.08 }}
              className="relative rounded-2xl border border-white/10 bg-panel p-6"
            >
              <span className="flex h-9 w-9 items-center justify-center rounded-full bg-gradient-to-br from-accent-600 to-accent-400 text-xs font-bold text-white">
                {s.step}
              </span>
              <h3 className="mt-4 font-heading text-base font-semibold text-white">{s.title}</h3>
              <p className="mt-2 text-sm leading-relaxed text-white/55">{s.body}</p>

              {s.tags && (
                <div className="mt-4 flex flex-wrap gap-1.5">
                  {s.tags.map((tag) => (
                    <span
                      key={tag}
                      className="rounded-full border border-white/10 bg-black/20 px-2.5 py-1 text-[10px] text-white/50"
                    >
                      {tag}
                    </span>
                  ))}
                </div>
              )}
              {s.checklist && (
                <div className="mt-4 flex flex-col gap-1.5">
                  {s.checklist.map((item) => (
                    <span key={item} className="flex items-center gap-1.5 text-xs text-white/60">
                      <CheckCircle2 size={13} className="text-gold-400" />
                      {item}
                    </span>
                  ))}
                </div>
              )}

              {i < STEPS.length - 1 && (
                <ArrowRight
                  size={18}
                  className="absolute -right-3 top-1/2 hidden -translate-y-1/2 text-accent-400/50 lg:block"
                />
              )}
            </motion.div>
          ))}
        </div>
      </section>

      <section className="px-5 pb-16">
        <div className="mx-auto grid max-w-6xl grid-cols-1 gap-6 lg:grid-cols-[1.3fr_1fr]">
          <WhyChoose />
          <motion.div
            initial="hidden"
            whileInView="visible"
            viewport={{ once: true, margin: "-60px" }}
            variants={fadeUp}
            transition={{ duration: 0.5 }}
            className="flex items-center justify-center rounded-2xl border border-white/10 bg-panel p-6"
          >
            <GoalStats />
          </motion.div>
        </div>
      </section>

      <CommunityCta />
    </>
  );
}
