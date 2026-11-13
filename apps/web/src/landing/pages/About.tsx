import { motion } from "framer-motion";
import { Gem, Rocket, Star, Target } from "lucide-react";
import { Link } from "react-router-dom";
import { CommunityCta } from "../components/CommunityCta";
import { GoalStats } from "../components/GoalStats";
import { HeroVisual } from "../components/HeroVisual";
import { HERO_PHOTOS } from "../heroPhotos";

const fadeUp = {
  hidden: { opacity: 0, y: 20 },
  visible: { opacity: 1, y: 0 },
};

const VALUES = ["Innovation", "Simplicity", "Reliability", "Customer First"] as const;

export function About() {
  return (
    <>
      <section className="glow-backdrop relative overflow-hidden px-5 pb-16 pt-14 sm:pt-20">
        <div className="mx-auto grid max-w-6xl grid-cols-1 items-center gap-10 lg:grid-cols-[1.1fr_1fr]">
          <motion.div initial="hidden" animate="visible" variants={fadeUp} transition={{ duration: 0.5 }}>
            <span className="inline-flex items-center gap-1.5 rounded-full border border-accent-500/30 bg-accent-500/10 px-3 py-1 text-xs font-semibold text-accent-300">
              <Star size={12} />
              About NOBS AI
            </span>
            <h1 className="mt-5 font-heading text-4xl font-bold leading-tight text-white sm:text-5xl">
              About <span className="text-gradient">Us</span>
            </h1>
            <p className="mt-3 font-heading text-lg font-semibold text-white/85">
              Building the Future of AI Video Creation in Africa and Beyond
            </p>
            <p className="mt-4 max-w-xl text-white/60">
              NOBS AI is more than a tool — it's an AI video creation platform designed to
              help anyone, anywhere, turn ideas into videos with ease.
            </p>
            <Link
              to="/waitlist"
              className="mt-7 inline-flex rounded-full bg-gradient-to-r from-gold-400 to-gold-500 px-7 py-3.5 text-sm font-semibold text-black shadow-lg shadow-gold-500/20 transition-transform hover:scale-[1.03]"
            >
              Join Our Waitlist →
            </Link>
          </motion.div>

          <motion.div
            initial={{ opacity: 0, scale: 0.9 }}
            animate={{ opacity: 1, scale: 1 }}
            transition={{ duration: 0.8, delay: 0.1 }}
          >
            <HeroVisual
              photoSrc={HERO_PHOTOS.pointingMan.src}
              photoAlt={HERO_PHOTOS.pointingMan.alt}
              className="h-[280px] sm:h-[340px]"
            />
          </motion.div>
        </div>
      </section>

      <section className="px-5 pb-16">
        <div className="mx-auto max-w-6xl">
          <div className="grid grid-cols-1 gap-8 lg:grid-cols-[1.2fr_1fr]">
            <motion.div
              initial="hidden"
              whileInView="visible"
              viewport={{ once: true, margin: "-60px" }}
              variants={fadeUp}
              transition={{ duration: 0.5 }}
            >
              <span className="text-xs font-semibold uppercase tracking-wide text-accent-300">
                Our Story
              </span>
              <h2 className="mt-2 font-heading text-2xl font-bold text-white">
                From a Big Idea to a Global Vision
              </h2>
              <p className="mt-4 text-white/60">
                NOBS AI was born from a simple belief: everyone should be able to create
                professional-quality videos without complex tools, expensive software, or
                technical skills.
              </p>
              <p className="mt-3 text-white/60">
                It's being built and tested in private right now, one real video at a time —
                research, script, voice, and footage, approved step by step before anything
                expensive runs.
              </p>
            </motion.div>

            <motion.div
              initial="hidden"
              whileInView="visible"
              viewport={{ once: true, margin: "-60px" }}
              variants={fadeUp}
              transition={{ duration: 0.5, delay: 0.1 }}
              className="grid grid-cols-1 gap-4 sm:grid-cols-3 lg:grid-cols-1"
            >
              {[
                {
                  icon: Rocket,
                  title: "Our Mission",
                  body: "Make AI video creation simple, affordable and accessible for everyone.",
                  list: undefined as readonly string[] | undefined,
                },
                {
                  icon: Target,
                  title: "Our Vision",
                  body: "A world where anyone can turn ideas into impact through AI.",
                  list: undefined as readonly string[] | undefined,
                },
                {
                  icon: Gem,
                  title: "Our Values",
                  body: undefined as string | undefined,
                  list: VALUES as readonly string[] | undefined,
                },
              ].map((card) => (
                <div key={card.title} className="rounded-2xl border border-white/10 bg-panel p-5">
                  <card.icon size={20} className="text-gold-400" />
                  <h3 className="mt-3 font-heading text-sm font-semibold text-white">{card.title}</h3>
                  {card.body && <p className="mt-1.5 text-xs text-white/55">{card.body}</p>}
                  {card.list && (
                    <ul className="mt-1.5 flex flex-col gap-1 text-xs text-white/55">
                      {card.list.map((v) => (
                        <li key={v}>✓ {v}</li>
                      ))}
                    </ul>
                  )}
                </div>
              ))}
            </motion.div>
          </div>
        </div>
      </section>

      <section className="px-5 pb-16">
        <div className="mx-auto max-w-6xl border-t border-white/10 pt-12">
          <span className="text-xs font-semibold uppercase tracking-wide text-accent-300">
            Our Impact
          </span>
          <h2 className="mt-2 max-w-lg font-heading text-2xl font-bold text-white">
            Building Toward a Creative and Innovative Community
          </h2>
          <GoalStats className="mt-8" />
        </div>
      </section>

      <section className="px-5 pb-16">
        <div className="mx-auto max-w-6xl border-t border-white/10 pt-12">
          <span className="text-xs font-semibold uppercase tracking-wide text-accent-300">
            Who's Building This
          </span>
          <div className="mt-4 flex flex-col items-start gap-4 rounded-2xl border border-white/10 bg-panel p-6 sm:flex-row sm:items-center">
            <span className="flex h-16 w-16 shrink-0 items-center justify-center rounded-2xl bg-gradient-to-br from-accent-600 to-accent-400 font-heading text-xl font-bold text-white">
              NA
            </span>
            <div>
              <h3 className="font-heading text-base font-semibold text-white">Nobert Agu</h3>
              <p className="mt-1 text-sm text-white/55">
                Building NOBS AI solo — right now it's one person's project, not a company
                with a team yet. That's the honest version; it may change as it grows.
              </p>
            </div>
          </div>
        </div>
      </section>

      <CommunityCta />
    </>
  );
}
