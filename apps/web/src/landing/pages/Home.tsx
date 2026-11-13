import { motion } from "framer-motion";
import { Bot, CheckCircle2, Lightbulb, Rocket, Wand2 } from "lucide-react";
import { Link } from "react-router-dom";
import { CommunityCta } from "../components/CommunityCta";
import { GoalStats } from "../components/GoalStats";
import { HeroVisual } from "../components/HeroVisual";
import { WaitlistInlineForm } from "../components/WaitlistInlineForm";
import { HERO_PHOTOS } from "../heroPhotos";

const fadeUp = {
  hidden: { opacity: 0, y: 24 },
  visible: { opacity: 1, y: 0 },
};

const STEPS = [
  { icon: Lightbulb, step: 1, title: "Share Your Idea", body: "Tell us what you want to create." },
  { icon: Bot, step: 2, title: "Let AI Work", body: "We research, script and plan for you." },
  { icon: CheckCircle2, step: 3, title: "Review & Approve", body: "Check your content before production." },
  { icon: Rocket, step: 4, title: "Download & Share", body: "Get your amazing video and grow your audience." },
] as const;

export function Home() {
  return (
    <>
      <section className="glow-backdrop relative overflow-hidden px-5 pb-20 pt-14 sm:pt-20">
        <div className="mx-auto grid max-w-6xl grid-cols-1 items-center gap-10 lg:grid-cols-[1.15fr_1fr]">
          <motion.div
            initial="hidden"
            animate="visible"
            variants={fadeUp}
            transition={{ duration: 0.6, ease: "easeOut" }}
          >
            <span className="inline-flex items-center rounded-full border border-accent-500/30 bg-accent-500/10 px-3 py-1 text-xs font-medium text-accent-300">
              The Next-Gen AI Video Partner
            </span>
            <h1 className="mt-5 font-heading text-4xl font-bold leading-tight text-white sm:text-5xl lg:text-6xl">
              NOBS <span className="text-gold-400">AI</span>
              <br />
              Create. Automate. <span className="text-gradient">Grow.</span>
            </h1>
            <p className="mt-5 max-w-xl text-lg text-white/60">
              The AI agent for creating stunning videos, automating your content, and
              growing your audience on YouTube — with more platforms on the way.
            </p>
            <div className="mt-8 flex flex-wrap items-center gap-4">
              <Link
                to="/waitlist"
                className="rounded-full bg-gradient-to-r from-gold-400 to-gold-500 px-7 py-3.5 text-sm font-semibold text-black shadow-lg shadow-gold-500/20 transition-transform hover:scale-[1.03]"
              >
                Join the Waitlist →
              </Link>
              <Link
                to="/how-it-works"
                className="rounded-full border border-white/15 px-7 py-3.5 text-sm font-semibold text-white/80 transition-colors hover:border-white/30 hover:text-white"
              >
                See how it works
              </Link>
            </div>
            <p className="mt-5 text-xs text-white/40">
              Not open to the public yet — join the waitlist and we'll email you the moment
              it is.
            </p>
          </motion.div>

          <motion.div
            initial={{ opacity: 0, scale: 0.9 }}
            animate={{ opacity: 1, scale: 1 }}
            transition={{ duration: 0.8, ease: "easeOut", delay: 0.1 }}
          >
            <HeroVisual
              photoSrc={HERO_PHOTOS.phoneMan.src}
              photoAlt={HERO_PHOTOS.phoneMan.alt}
              className="h-[300px] sm:h-[380px]"
            />
          </motion.div>
        </div>
      </section>

      <section className="px-5 pb-20">
        <motion.div
          initial="hidden"
          whileInView="visible"
          viewport={{ once: true, margin: "-80px" }}
          variants={fadeUp}
          transition={{ duration: 0.5 }}
          className="mx-auto max-w-3xl rounded-3xl border border-white/10 bg-panel p-6 sm:p-8"
        >
          <h2 className="font-heading text-xl font-bold text-white">Join Our Exclusive Waitlist</h2>
          <p className="mt-2 text-sm text-white/55">
            Be the first to know when NOBS AI launches. Get early access and special
            benefits.
          </p>
          <WaitlistInlineForm />
        </motion.div>
      </section>

      <section className="px-5 pb-20">
        <div className="mx-auto max-w-6xl">
          <motion.div
            initial="hidden"
            whileInView="visible"
            viewport={{ once: true, margin: "-80px" }}
            variants={fadeUp}
            transition={{ duration: 0.5 }}
            className="text-center"
          >
            <span className="inline-flex items-center gap-1.5 rounded-full border border-accent-500/30 bg-accent-500/10 px-3 py-1 text-xs font-semibold text-accent-300">
              <Wand2 size={12} />
              How It Works
            </span>
            <h2 className="mt-4 font-heading text-2xl font-bold text-white sm:text-3xl">
              4 Simple Steps to Amazing Results
            </h2>
            <p className="mx-auto mt-2 max-w-md text-sm text-white/55">
              Get started in minutes and let NOBS AI do the heavy lifting.
            </p>
          </motion.div>

          <div className="mt-10 grid grid-cols-1 gap-6 sm:grid-cols-2 lg:grid-cols-4">
            {STEPS.map((s, i) => (
              <motion.div
                key={s.title}
                initial="hidden"
                whileInView="visible"
                viewport={{ once: true, margin: "-60px" }}
                variants={fadeUp}
                transition={{ duration: 0.5, delay: i * 0.08 }}
                className="rounded-2xl border border-white/10 bg-panel p-6"
              >
                <span className="flex h-11 w-11 items-center justify-center rounded-xl bg-gradient-to-br from-accent-600 to-accent-400 text-sm font-bold text-white">
                  {s.step}
                </span>
                <h3 className="mt-4 flex items-center gap-2 font-heading text-base font-semibold text-white">
                  <s.icon size={16} className="text-gold-400" />
                  {s.title}
                </h3>
                <p className="mt-2 text-sm leading-relaxed text-white/55">{s.body}</p>
              </motion.div>
            ))}
          </div>

          <div className="mt-8 text-center">
            <Link
              to="/how-it-works"
              className="text-sm font-semibold text-accent-300 hover:text-accent-200"
            >
              See the full guide →
            </Link>
          </div>
        </div>
      </section>

      <section className="px-5 pb-20">
        <motion.div
          initial="hidden"
          whileInView="visible"
          viewport={{ once: true, margin: "-80px" }}
          variants={fadeUp}
          transition={{ duration: 0.5 }}
          className="mx-auto max-w-5xl"
        >
          <GoalStats className="justify-center" />
        </motion.div>
      </section>

      <CommunityCta />
    </>
  );
}
