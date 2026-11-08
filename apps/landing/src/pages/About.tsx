import { motion } from "framer-motion";

const fadeUp = {
  hidden: { opacity: 0, y: 20 },
  visible: { opacity: 1, y: 0 },
};

export function About() {
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
          About <span className="text-gradient">NOBS AI</span>
        </h1>

        <div className="mt-8 flex flex-col gap-6 text-white/65 leading-relaxed">
          <p>
            NOBS AI started as a personal tool to automate YouTube video production end to
            end — topic in, finished video out, without touching editing software. Instead
            of generating one long, un-reviewable video, it works the way a real production
            does: research the topic, write a scene-by-scene script, get it approved, then
            generate narration and footage scene by scene before assembling the final cut.
          </p>
          <p>
            That "approve before anything expensive runs" step isn't an afterthought — it's
            the whole design. The plan is always visible before a single clip is generated,
            so nothing gets made that wasn't wanted.
          </p>
          <p>
            It's being built and tested in private right now. Opening it up to more people
            is next — the waitlist is how we'll let you know when that happens.
          </p>
        </div>
      </motion.div>
    </section>
  );
}
