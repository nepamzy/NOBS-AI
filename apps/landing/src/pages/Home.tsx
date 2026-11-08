import { motion } from "framer-motion";
import { Clapperboard, Mic, Sparkles, Wand2 } from "lucide-react";
import { Suspense, lazy } from "react";
import { Link } from "react-router-dom";

// Lazy: three.js + fiber + drei are the bulk of this app's JS weight, and
// only this page needs them — About/Contact/Waitlist shouldn't have to
// download it at all.
const Scene3D = lazy(() => import("../components/Scene3D").then((m) => ({ default: m.Scene3D })));

const STEPS = [
  {
    icon: Sparkles,
    title: "Give it a topic",
    body: "One line is enough — \"5 habits that will change your life.\" NOBS AI researches it, finds the angle, and writes a scene-by-scene script.",
  },
  {
    icon: Mic,
    title: "Real narration",
    body: "Every scene gets real voiceover, timed to the words — not a robotic text-to-speech guess.",
  },
  {
    icon: Clapperboard,
    title: "Real footage, scene by scene",
    body: "Each line of the script becomes its own short video clip, generated and assembled in order — never one long, un-editable render.",
  },
  {
    icon: Wand2,
    title: "You approve before anything renders",
    body: "The full storyboard — every scene, every line — is yours to review and approve first. Nothing expensive happens behind your back.",
  },
];

const fadeUp = {
  hidden: { opacity: 0, y: 24 },
  visible: { opacity: 1, y: 0 },
};

export function Home() {
  return (
    <>
      <section className="glow-backdrop relative overflow-hidden px-5 pb-24 pt-16 sm:pt-24">
        <div className="mx-auto grid max-w-6xl grid-cols-1 items-center gap-10 lg:grid-cols-[1.1fr_1fr]">
          <motion.div
            initial="hidden"
            animate="visible"
            variants={fadeUp}
            transition={{ duration: 0.6, ease: "easeOut" }}
          >
            <span className="inline-flex items-center rounded-full border border-accent-500/30 bg-accent-500/10 px-3 py-1 text-xs font-medium text-accent-300">
              Not yet open to the public
            </span>
            <h1 className="mt-5 font-heading text-4xl font-bold leading-tight text-white sm:text-5xl lg:text-6xl">
              Turn a topic into a <span className="text-gradient">finished video</span>
            </h1>
            <p className="mt-5 max-w-xl text-lg text-white/60">
              Research, script, voice, and footage — handled end to end. You give the idea
              and approve the plan; NOBS AI does the rest.
            </p>
            <div className="mt-8 flex flex-wrap items-center gap-4">
              <Link
                to="/waitlist"
                className="rounded-full bg-gradient-to-r from-accent-600 to-accent-400 px-7 py-3.5 text-sm font-semibold text-white shadow-lg shadow-accent-600/30 transition-transform hover:scale-[1.03]"
              >
                Join the Waitlist
              </Link>
              <Link
                to="/about"
                className="rounded-full border border-white/15 px-7 py-3.5 text-sm font-semibold text-white/80 transition-colors hover:border-white/30 hover:text-white"
              >
                How it works
              </Link>
            </div>
          </motion.div>

          <motion.div
            initial={{ opacity: 0, scale: 0.9 }}
            animate={{ opacity: 1, scale: 1 }}
            transition={{ duration: 0.8, ease: "easeOut", delay: 0.1 }}
            className="relative h-[320px] sm:h-[420px] lg:h-[480px]"
          >
            <Suspense fallback={<div className="glow-backdrop h-full w-full" />}>
              <Scene3D className="h-full w-full" />
            </Suspense>
          </motion.div>
        </div>
      </section>

      <section className="px-5 py-20">
        <div className="mx-auto max-w-6xl">
          <motion.h2
            initial="hidden"
            whileInView="visible"
            viewport={{ once: true, margin: "-80px" }}
            variants={fadeUp}
            transition={{ duration: 0.5 }}
            className="text-center font-heading text-2xl font-bold text-white sm:text-3xl"
          >
            From idea to finished video, in four steps
          </motion.h2>

          <div className="mt-12 grid grid-cols-1 gap-6 sm:grid-cols-2 lg:grid-cols-4">
            {STEPS.map((step, i) => (
              <motion.div
                key={step.title}
                initial="hidden"
                whileInView="visible"
                viewport={{ once: true, margin: "-60px" }}
                variants={fadeUp}
                transition={{ duration: 0.5, delay: i * 0.08 }}
                className="rounded-2xl border border-white/10 bg-panel p-6"
              >
                <span className="flex h-11 w-11 items-center justify-center rounded-xl bg-gradient-to-br from-accent-600 to-accent-400">
                  <step.icon size={20} className="text-white" />
                </span>
                <h3 className="mt-4 font-heading text-base font-semibold text-white">
                  {step.title}
                </h3>
                <p className="mt-2 text-sm leading-relaxed text-white/55">{step.body}</p>
              </motion.div>
            ))}
          </div>
        </div>
      </section>

      <section className="px-5 py-20">
        <motion.div
          initial="hidden"
          whileInView="visible"
          viewport={{ once: true, margin: "-80px" }}
          variants={fadeUp}
          transition={{ duration: 0.5 }}
          className="glow-backdrop mx-auto max-w-3xl rounded-3xl border border-white/10 bg-panel px-8 py-14 text-center"
        >
          <h2 className="font-heading text-2xl font-bold text-white sm:text-3xl">
            Be first in when it opens
          </h2>
          <p className="mx-auto mt-3 max-w-md text-white/55">
            NOBS AI is still in private testing. Join the waitlist and you'll get an email
            the moment it's ready for you.
          </p>
          <Link
            to="/waitlist"
            className="mt-7 inline-flex rounded-full bg-gradient-to-r from-accent-600 to-accent-400 px-8 py-3.5 text-sm font-semibold text-white shadow-lg shadow-accent-600/30 transition-transform hover:scale-[1.03]"
          >
            Join the Waitlist
          </Link>
        </motion.div>
      </section>
    </>
  );
}
