import { motion } from "framer-motion";

const fadeUp = {
  hidden: { opacity: 0, y: 20 },
  visible: { opacity: 1, y: 0 },
};

export function Terms() {
  return (
    <section className="glow-backdrop px-5 py-20">
      <motion.div
        initial="hidden"
        animate="visible"
        variants={fadeUp}
        transition={{ duration: 0.5 }}
        className="mx-auto max-w-3xl"
      >
        <h1 className="font-heading text-3xl font-bold text-white sm:text-4xl">
          Terms of <span className="text-gradient">Service</span>
        </h1>
        <p className="mt-2 text-sm text-white/40">Last updated: November 2026</p>

        <div className="mt-8 flex flex-col gap-6 text-white/65 leading-relaxed">
          <p>
            NOBS AI is a personal project, currently in private development and not yet
            generally available. These terms cover the waitlist you can join on this site.
          </p>

          <div>
            <h2 className="font-heading text-xl font-semibold text-white">The waitlist</h2>
            <p className="mt-2">
              Joining the waitlist doesn't create an account or give you access to the
              product — it just lets us contact you when access opens up. We may invite
              people off the waitlist in any order, at any time, or not at all.
            </p>
          </div>

          <div>
            <h2 className="font-heading text-xl font-semibold text-white">
              No guarantees yet
            </h2>
            <p className="mt-2">
              Because the product isn't launched, we can't make promises about features,
              availability, or timelines. Anything shown on this site describes where the
              project is headed, not a finished product.
            </p>
          </div>

          <div>
            <h2 className="font-heading text-xl font-semibold text-white">Changes</h2>
            <p className="mt-2">
              These terms will be replaced with a full Terms of Service once NOBS AI opens up
              beyond the waitlist. We'll post the updated version here when that happens.
            </p>
          </div>

          <div>
            <h2 className="font-heading text-xl font-semibold text-white">Contact</h2>
            <p className="mt-2">
              Questions about these terms? Reach us through our{" "}
              <a href="/contact" className="text-white underline">
                Contact
              </a>{" "}
              page.
            </p>
          </div>
        </div>
      </motion.div>
    </section>
  );
}
