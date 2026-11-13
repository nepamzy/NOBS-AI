import { motion } from "framer-motion";
import { Mail } from "lucide-react";

// PLACEHOLDER — swap for the real contact details. Nothing else on this
// page needs to change once this is updated.
const CONTACT_EMAIL = "hello@nobsai.example";

const fadeUp = {
  hidden: { opacity: 0, y: 20 },
  visible: { opacity: 1, y: 0 },
};

export function Contact() {
  return (
    <section className="glow-backdrop px-5 py-20">
      <motion.div
        initial="hidden"
        animate="visible"
        variants={fadeUp}
        transition={{ duration: 0.5 }}
        className="mx-auto max-w-2xl text-center"
      >
        <h1 className="font-heading text-3xl font-bold text-white sm:text-4xl">Get in touch</h1>
        <p className="mx-auto mt-3 max-w-md text-white/55">
          Questions, feedback, or press — reach out directly.
        </p>

        <a
          href={`mailto:${CONTACT_EMAIL}`}
          className="mt-8 inline-flex items-center gap-2.5 rounded-full border border-white/15 bg-panel px-6 py-3.5 text-sm font-semibold text-white transition-colors hover:border-accent-400/50 hover:text-accent-300"
        >
          <Mail size={16} />
          {CONTACT_EMAIL}
        </a>
      </motion.div>
    </section>
  );
}
