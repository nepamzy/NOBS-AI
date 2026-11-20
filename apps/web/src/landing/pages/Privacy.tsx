import { motion } from "framer-motion";

const fadeUp = {
  hidden: { opacity: 0, y: 20 },
  visible: { opacity: 1, y: 0 },
};

export function Privacy() {
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
          Privacy <span className="text-gradient">Policy</span>
        </h1>
        <p className="mt-2 text-sm text-white/40">Last updated: November 2026</p>

        <div className="mt-8 flex flex-col gap-6 text-white/65 leading-relaxed">
          <p>
            NOBS AI is currently a private, pre-launch project. This page explains what we
            collect from people who join our waitlist and what we do with it.
          </p>

          <div>
            <h2 className="font-heading text-xl font-semibold text-white">What we collect</h2>
            <p className="mt-2">
              When you join the waitlist, we collect your email address and, if you sign in
              with Google, the name and email address Google shares with us under the basic
              "openid", "email" and "profile" scopes. We do not request access to your
              YouTube account, Google Drive, or any other Google data, and we never see your
              Google password.
            </p>
          </div>

          <div>
            <h2 className="font-heading text-xl font-semibold text-white">How we use it</h2>
            <p className="mt-2">
              We use your email address only to let you know when NOBS AI opens up, and for
              occasional updates about the project. We don't sell, rent, or share your
              information with third parties, and we don't use it for advertising.
            </p>
          </div>

          <div>
            <h2 className="font-heading text-xl font-semibold text-white">
              Data retention and removal
            </h2>
            <p className="mt-2">
              We keep waitlist information until the product launches or you ask us to
              delete it, whichever comes first. To request deletion of your data, reach us
              through our{" "}
              <a href="/contact" className="text-white underline">
                Contact
              </a>{" "}
              page.
            </p>
          </div>

          <div>
            <h2 className="font-heading text-xl font-semibold text-white">
              Changes to this policy
            </h2>
            <p className="mt-2">
              As NOBS AI moves from a private waitlist to a real product, this policy will be
              updated to reflect what the product actually does. We'll post the new version
              here when that happens.
            </p>
          </div>
        </div>
      </motion.div>
    </section>
  );
}
