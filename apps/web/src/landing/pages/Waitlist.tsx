import { motion } from "framer-motion";
import { CheckCircle2, Users } from "lucide-react";
import { useSearchParams } from "react-router-dom";
import { WaitlistInlineForm } from "../components/WaitlistInlineForm";

const fadeUp = {
  hidden: { opacity: 0, y: 20 },
  visible: { opacity: 1, y: 0 },
};

const OAUTH_ERROR_MESSAGES: Record<string, string> = {
  not_configured:
    "Google sign-in isn't set up yet — use your email below instead, or try again once it's live.",
  denied: "Sign-in was cancelled — use your email below instead.",
  failed: "Something went wrong signing you in — use your email below instead.",
};

export function Waitlist() {
  const [params] = useSearchParams();
  const joinedViaOAuth = params.get("joined") === "1";
  const oauthError = params.get("oauth_error");

  return (
    <section className="glow-backdrop flex min-h-[70vh] items-center px-5 py-20">
      <motion.div
        initial="hidden"
        animate="visible"
        variants={fadeUp}
        transition={{ duration: 0.5 }}
        className="mx-auto w-full max-w-md rounded-3xl border border-white/10 bg-panel p-8"
      >
        {joinedViaOAuth ? (
          <div className="flex flex-col items-center gap-3 py-6 text-center">
            <CheckCircle2 size={40} className="text-gold-400" />
            <h2 className="font-heading text-xl font-bold text-white">You're on the list</h2>
            <p className="text-sm text-white/55">
              No account, nothing to do now — we'll email you the moment NOBS AI opens up.
            </p>
          </div>
        ) : (
          <>
            <span className="inline-flex items-center gap-1.5 rounded-full border border-accent-500/30 bg-accent-500/10 px-3 py-1 text-xs font-semibold text-accent-300">
              <Users size={12} />
              Join Our Exclusive Waitlist
            </span>
            <h1 className="mt-4 font-heading text-2xl font-bold text-white">
              Join the waitlist
            </h1>
            <p className="mt-2 text-sm text-white/55">
              NOBS AI isn't open to the public yet. Leave your email and we'll let you know
              the moment it is — no account, no sign-up now.
            </p>

            {oauthError && (
              <p className="mt-4 rounded-lg border border-gold-500/20 bg-gold-500/10 px-3 py-2 text-xs text-gold-300">
                {OAUTH_ERROR_MESSAGES[oauthError] ?? OAUTH_ERROR_MESSAGES.failed}
              </p>
            )}

            <WaitlistInlineForm />
          </>
        )}
      </motion.div>
    </section>
  );
}
