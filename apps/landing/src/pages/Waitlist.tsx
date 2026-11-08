import { motion } from "framer-motion";
import { CheckCircle2 } from "lucide-react";
import type { FormEvent } from "react";
import { useState } from "react";
import { ApiError, joinWaitlist } from "../api/client";

const fadeUp = {
  hidden: { opacity: 0, y: 20 },
  visible: { opacity: 1, y: 0 },
};

export function Waitlist() {
  const [name, setName] = useState("");
  const [email, setEmail] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [joined, setJoined] = useState(false);

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    setError(null);
    setSubmitting(true);
    try {
      await joinWaitlist(email.trim(), name.trim());
      setJoined(true);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Something went wrong — try again.");
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <section className="glow-backdrop flex min-h-[70vh] items-center px-5 py-20">
      <motion.div
        initial="hidden"
        animate="visible"
        variants={fadeUp}
        transition={{ duration: 0.5 }}
        className="mx-auto w-full max-w-md rounded-3xl border border-white/10 bg-panel p-8"
      >
        {joined ? (
          <div className="flex flex-col items-center gap-3 py-6 text-center">
            <CheckCircle2 size={40} className="text-accent-400" />
            <h2 className="font-heading text-xl font-bold text-white">You're on the list</h2>
            <p className="text-sm text-white/55">
              No account, nothing to do now — we'll email {email.trim() || "you"} the moment
              NOBS AI opens up.
            </p>
          </div>
        ) : (
          <>
            <h1 className="font-heading text-2xl font-bold text-white">Join the waitlist</h1>
            <p className="mt-2 text-sm text-white/55">
              NOBS AI isn't open to the public yet. Leave your email and we'll let you know
              the moment it is — no account, no sign-up now.
            </p>

            <form onSubmit={handleSubmit} className="mt-6 flex flex-col gap-4">
              <label className="flex flex-col gap-1.5">
                <span className="text-sm text-white/70">Name (optional)</span>
                <input
                  value={name}
                  onChange={(e) => setName(e.target.value)}
                  placeholder="Your name"
                  className="rounded-md border border-white/10 bg-black/20 px-3 py-2.5 text-white placeholder:text-white/30"
                />
              </label>
              <label className="flex flex-col gap-1.5">
                <span className="text-sm text-white/70">Email</span>
                <input
                  type="email"
                  required
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  placeholder="you@email.com"
                  className="rounded-md border border-white/10 bg-black/20 px-3 py-2.5 text-white placeholder:text-white/30"
                />
              </label>

              {error && <p className="text-sm text-red-400">{error}</p>}

              <button
                type="submit"
                disabled={submitting || !email.trim()}
                className="mt-1 rounded-full bg-gradient-to-r from-accent-600 to-accent-400 px-6 py-3 text-sm font-semibold text-white transition-opacity disabled:opacity-40"
              >
                {submitting ? "Joining…" : "Join the Waitlist"}
              </button>
            </form>
          </>
        )}
      </motion.div>
    </section>
  );
}
