import { motion } from "framer-motion";
import { CheckCircle2, Star } from "lucide-react";

const fadeUp = {
  hidden: { opacity: 0, y: 20 },
  visible: { opacity: 1, y: 0 },
};

// Only true, checkable claims — "Secure & Reliable" / "Dedicated Support"
// style puffery from the mockups is dropped rather than asserted with
// nothing behind it (CLAUDE.md: no invented information).
const POINTS = [
  "Super Easy to Use",
  "Built for Africa & Beyond",
  "Free While in Private Testing",
  "You Approve Every Script Before It Costs Anything",
] as const;

export function WhyChoose({ title = "Why Choose NOBS AI?" }: { title?: string }) {
  return (
    <motion.div
      initial="hidden"
      whileInView="visible"
      viewport={{ once: true, margin: "-60px" }}
      variants={fadeUp}
      transition={{ duration: 0.5 }}
      className="rounded-2xl border border-white/10 bg-panel p-6 sm:p-8"
    >
      <span className="inline-flex items-center gap-1.5 rounded-full border border-gold-500/30 bg-gold-500/10 px-3 py-1 text-xs font-semibold text-gold-400">
        <Star size={12} />
        {title}
      </span>
      <div className="mt-5 grid grid-cols-1 gap-3 sm:grid-cols-2">
        {POINTS.map((point) => (
          <div key={point} className="flex items-center gap-2.5 text-sm text-white/75">
            <CheckCircle2 size={18} className="shrink-0 text-gold-400" />
            {point}
          </div>
        ))}
      </div>
    </motion.div>
  );
}
