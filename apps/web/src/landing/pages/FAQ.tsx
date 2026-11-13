import { motion } from "framer-motion";
import { HelpCircle, Minus, Plus } from "lucide-react";
import { useState } from "react";
import { CommunityCta } from "../components/CommunityCta";

const fadeUp = {
  hidden: { opacity: 0, y: 20 },
  visible: { opacity: 1, y: 0 },
};

// Not in the mockups (no FAQ content was shown) — drafted from what's
// actually true about the product today rather than invented, per
// CLAUDE.md. Easy to edit once real questions come in.
const FAQS = [
  {
    q: "What is NOBS AI?",
    a: "An AI tool that turns a topic into a finished video — research, script, voiceover, and footage, assembled end to end. You review and approve the plan before anything is generated.",
  },
  {
    q: "Can I use it right now?",
    a: "Not yet — it's in private testing. Join the waitlist and you'll get an email the moment it opens up.",
  },
  {
    q: "Will it be free?",
    a: "Pricing isn't decided yet. Waitlist members will hear about it first, before anyone else.",
  },
  {
    q: "What platforms does it publish to?",
    a: "YouTube upload is built today. More platforms are planned but not available yet.",
  },
  {
    q: "Is my content private?",
    a: "Yes — every project is private to the account that created it.",
  },
] as const;

export function FAQ() {
  const [open, setOpen] = useState<number | null>(0);

  return (
    <>
      <section className="glow-backdrop px-5 pb-10 pt-14 text-center sm:pt-20">
        <motion.div initial="hidden" animate="visible" variants={fadeUp} transition={{ duration: 0.5 }}>
          <span className="inline-flex items-center gap-1.5 rounded-full border border-accent-500/30 bg-accent-500/10 px-3 py-1 text-xs font-semibold text-accent-300">
            <HelpCircle size={12} />
            FAQ
          </span>
          <h1 className="mt-4 font-heading text-3xl font-bold text-white sm:text-4xl">
            Frequently Asked <span className="text-gradient">Questions</span>
          </h1>
        </motion.div>
      </section>

      <section className="px-5 pb-16">
        <div className="mx-auto max-w-2xl divide-y divide-white/10 rounded-2xl border border-white/10 bg-panel">
          {FAQS.map((item, i) => (
            <div key={item.q}>
              <button
                onClick={() => setOpen(open === i ? null : i)}
                className="flex w-full items-center justify-between gap-4 px-6 py-5 text-left"
                aria-expanded={open === i}
              >
                <span className="font-heading text-sm font-semibold text-white sm:text-base">
                  {item.q}
                </span>
                {open === i ? (
                  <Minus size={16} className="shrink-0 text-gold-400" />
                ) : (
                  <Plus size={16} className="shrink-0 text-white/40" />
                )}
              </button>
              {open === i && (
                <p className="px-6 pb-5 text-sm leading-relaxed text-white/60">{item.a}</p>
              )}
            </div>
          ))}
        </div>
      </section>

      <CommunityCta />
    </>
  );
}
