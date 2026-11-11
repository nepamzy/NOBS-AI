import { motion } from "framer-motion";
import { Rocket } from "lucide-react";
import { Link } from "react-router-dom";

const fadeUp = {
  hidden: { opacity: 0, y: 20 },
  visible: { opacity: 1, y: 0 },
};

// The purple-and-gold "Be Part of the NOBS AI Community" banner that
// closes out every mockup page — same copy/position everywhere, so it's
// one shared component instead of four near-duplicates.
export function CommunityCta() {
  return (
    <section className="px-5 pb-20">
      <motion.div
        initial="hidden"
        whileInView="visible"
        viewport={{ once: true, margin: "-80px" }}
        variants={fadeUp}
        transition={{ duration: 0.5 }}
        className="glow-backdrop mx-auto flex max-w-5xl flex-col items-center gap-5 rounded-3xl border border-white/10 bg-panel px-8 py-10 text-center sm:flex-row sm:justify-between sm:text-left"
      >
        <div className="flex items-center gap-4">
          <span className="flex h-12 w-12 shrink-0 items-center justify-center rounded-2xl bg-gradient-to-br from-accent-600 to-accent-400">
            <Rocket size={22} className="text-white" />
          </span>
          <div>
            <h3 className="font-heading text-lg font-bold text-white sm:text-xl">
              Be Part of the NOBS AI Community
            </h3>
            <p className="mt-1 max-w-sm text-sm text-white/55">
              Join the waitlist today and be first to experience the future of AI video
              creation.
            </p>
          </div>
        </div>
        <Link
          to="/waitlist"
          className="inline-flex shrink-0 items-center gap-2 rounded-full bg-gradient-to-r from-gold-400 to-gold-500 px-7 py-3.5 text-sm font-semibold text-black shadow-lg shadow-gold-500/20 transition-transform hover:scale-[1.03]"
        >
          Join Waitlist →
        </Link>
      </motion.div>
    </section>
  );
}
