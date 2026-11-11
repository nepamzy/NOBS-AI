import { motion } from "framer-motion";
import {
  Bot,
  Clapperboard,
  FolderKanban,
  ImagePlus,
  LayoutDashboard,
  Plus,
  Scissors,
  Settings,
  Shield,
  Sparkles,
  UploadCloud,
  Video,
} from "lucide-react";
import { Link } from "react-router-dom";
import { CommunityCta } from "../components/CommunityCta";
import { HERO_PHOTOS } from "../heroPhotos";

const fadeUp = {
  hidden: { opacity: 0, y: 20 },
  visible: { opacity: 1, y: 0 },
};

// Mirrors the real app's actual sidebar (apps/web) — not the "Analytics"
// item some marketing mockups show, since that page doesn't exist yet
// (CLAUDE.md: Analytics is V3).
const SIDEBAR = [
  { icon: LayoutDashboard, label: "Dashboard", active: true },
  { icon: Plus, label: "Create Video", active: false },
  { icon: FolderKanban, label: "My Projects", active: false },
  { icon: Video, label: "Video Library", active: false },
  { icon: Bot, label: "Assistant", active: false },
  { icon: Settings, label: "Settings", active: false },
] as const;

const PLATFORM_FEATURES = [
  { icon: Clapperboard, title: "AI Video Creation", body: "Turn your ideas into stunning videos with AI." },
  { icon: Scissors, title: "Smart Clipping", body: "Find the best moments automatically." },
  { icon: Bot, iconSrc: "/icons/ai-robot.png", title: "AI Assistant", body: "Get help, ideas and suggestions." },
  { icon: ImagePlus, title: "Custom Thumbnails", body: "Create eye-catching thumbnails easily." },
  { icon: UploadCloud, title: "Direct Publishing", body: "Upload to YouTube — more platforms on the way." },
] as const;

const STEPS = [
  { step: 1, title: "Share Your Idea", body: "Tell us what you want to create." },
  { step: 2, title: "Let AI Work", body: "We research, script and plan for you." },
  { step: 3, title: "Review & Approve", body: "Check your content before production." },
  { step: 4, title: "Download & Share", body: "Get your video and grow your audience." },
] as const;

export function Platform() {
  return (
    <>
      <section className="glow-backdrop relative overflow-hidden px-5 pb-16 pt-14 sm:pt-20">
        <div className="mx-auto grid max-w-6xl grid-cols-1 items-center gap-10 lg:grid-cols-[1fr_1.05fr]">
          <motion.div initial="hidden" animate="visible" variants={fadeUp} transition={{ duration: 0.5 }}>
            <span className="inline-flex items-center gap-1.5 rounded-full border border-accent-500/30 bg-accent-500/10 px-3 py-1 text-xs font-semibold text-accent-300">
              <Sparkles size={12} />
              Our Platform
            </span>
            <h1 className="mt-5 font-heading text-4xl font-bold leading-tight text-white sm:text-5xl">
              The Complete <span className="text-gradient">AI Video Creation</span> Platform
            </h1>
            <p className="mt-5 max-w-xl text-lg text-white/60">
              NOBS AI brings together research, scripting, voice, and video generation in
              one place. Give it the idea, approve the plan, get the video.
            </p>
            <div className="mt-7 flex flex-wrap items-center gap-x-8 gap-y-3 border-t border-white/10 pt-6 text-sm text-white/70">
              <span className="flex items-center gap-2">
                <Sparkles size={16} className="text-gold-400" /> All-in-One Solution
              </span>
              <span className="flex items-center gap-2">
                <Bot size={16} className="text-gold-400" /> Built for Creators
              </span>
              <span className="flex items-center gap-2">
                <Shield size={16} className="text-gold-400" /> Review Before It Runs
              </span>
            </div>
            <Link
              to="/waitlist"
              className="mt-8 inline-flex rounded-full bg-gradient-to-r from-gold-400 to-gold-500 px-7 py-3.5 text-sm font-semibold text-black shadow-lg shadow-gold-500/20 transition-transform hover:scale-[1.03]"
            >
              Join the Waitlist →
            </Link>
          </motion.div>

          <motion.div
            initial={{ opacity: 0, scale: 0.95 }}
            animate={{ opacity: 1, scale: 1 }}
            transition={{ duration: 0.7, delay: 0.1 }}
            className="glow-backdrop relative rounded-2xl border border-white/10 bg-panel p-3 shadow-2xl"
          >
            <img
              src={HERO_PHOTOS.pointingMan.src}
              alt={HERO_PHOTOS.pointingMan.alt}
              className="absolute -right-4 -top-6 hidden h-28 w-28 rounded-2xl border-2 border-panel object-cover shadow-xl sm:block"
            />
            <div className="flex overflow-hidden rounded-xl border border-white/10 bg-black/30">
              <aside className="hidden w-40 flex-col gap-1 border-r border-white/10 bg-black/20 p-3 sm:flex">
                {SIDEBAR.map((item) => (
                  <span
                    key={item.label}
                    className={`flex items-center gap-2 rounded-lg px-2.5 py-2 text-xs ${
                      item.active ? "bg-accent-500/20 text-white" : "text-white/50"
                    }`}
                  >
                    <item.icon size={14} />
                    {item.label}
                  </span>
                ))}
              </aside>
              <div className="flex-1 p-4">
                <p className="font-heading text-sm font-semibold text-white">
                  Welcome back, Creator! 👋
                </p>
                <p className="mt-1 text-xs text-white/50">
                  Let's turn your idea into an amazing video.
                </p>
                <div className="mt-3 grid grid-cols-3 gap-2">
                  {[
                    ["Projects", "—"],
                    ["Videos", "—"],
                    ["Processing", "—"],
                  ].map(([label, value]) => (
                    <div key={label} className="rounded-lg border border-white/10 bg-panel p-2.5 text-center">
                      <p className="font-heading text-sm font-bold text-white">{value}</p>
                      <p className="text-[10px] text-white/45">{label}</p>
                    </div>
                  ))}
                </div>
                <p className="mt-3 text-[10px] text-white/30">
                  Illustrative preview — real numbers once NOBS AI is in use.
                </p>
              </div>
            </div>
          </motion.div>
        </div>
      </section>

      <section className="px-5 pb-16">
        <div className="mx-auto max-w-6xl">
          <motion.div
            initial="hidden"
            whileInView="visible"
            viewport={{ once: true, margin: "-80px" }}
            variants={fadeUp}
            transition={{ duration: 0.5 }}
            className="text-center"
          >
            <span className="inline-flex items-center rounded-full border border-accent-500/30 bg-accent-500/10 px-3 py-1 text-xs font-semibold text-accent-300">
              Key Features
            </span>
            <h2 className="mt-4 font-heading text-2xl font-bold text-white sm:text-3xl">
              Powerful Features for Unlimited Creativity
            </h2>
          </motion.div>

          <div className="mt-10 grid grid-cols-1 gap-5 sm:grid-cols-2 lg:grid-cols-5">
            {PLATFORM_FEATURES.map((f, i) => (
              <motion.div
                key={f.title}
                initial="hidden"
                whileInView="visible"
                viewport={{ once: true, margin: "-60px" }}
                variants={fadeUp}
                transition={{ duration: 0.4, delay: i * 0.05 }}
                className="rounded-2xl border border-white/10 bg-panel p-5"
              >
                {"iconSrc" in f ? (
                  <img src={f.iconSrc} alt="" className="h-10 w-10 rounded-xl" />
                ) : (
                  <span className="flex h-10 w-10 items-center justify-center rounded-xl bg-gradient-to-br from-accent-600 to-accent-400">
                    <f.icon size={18} className="text-white" />
                  </span>
                )}
                <h3 className="mt-3 font-heading text-sm font-semibold text-white">{f.title}</h3>
                <p className="mt-1.5 text-xs leading-relaxed text-white/55">{f.body}</p>
              </motion.div>
            ))}
          </div>

          <div className="mt-14 border-t border-white/10 pt-10 text-center">
            <span className="inline-flex items-center rounded-full border border-accent-500/30 bg-accent-500/10 px-3 py-1 text-xs font-semibold text-accent-300">
              How It Works
            </span>
            <h2 className="mt-4 font-heading text-xl font-bold text-white sm:text-2xl">
              Get Started in 4 Simple Steps
            </h2>
          </div>

          <div className="mt-8 grid grid-cols-1 gap-6 sm:grid-cols-2 lg:grid-cols-4">
            {STEPS.map((s) => (
              <div key={s.title} className="flex items-start gap-3">
                <span className="flex h-9 w-9 shrink-0 items-center justify-center rounded-full bg-gradient-to-br from-accent-600 to-accent-400 text-xs font-bold text-white">
                  {s.step}
                </span>
                <div>
                  <h3 className="font-heading text-sm font-semibold text-white">{s.title}</h3>
                  <p className="mt-1 text-xs text-white/55">{s.body}</p>
                </div>
              </div>
            ))}
          </div>
        </div>
      </section>

      <CommunityCta />
    </>
  );
}
