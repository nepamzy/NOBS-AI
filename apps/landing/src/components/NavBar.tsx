import { ChevronDown, Menu, X } from "lucide-react";
import { useRef, useState } from "react";
import { NavLink } from "react-router-dom";

// Where the real product lives — tapping the logo 3x in a row is the
// hidden door back to it for Nobert, never advertised anywhere on the
// page itself. Override via VITE_APP_LOGIN_URL if the app ever moves.
const APP_LOGIN_URL = import.meta.env.VITE_APP_LOGIN_URL ?? "https://nobs-ai.vercel.app/login";
const TRIPLE_TAP_WINDOW_MS = 600;

const TABS = [
  { to: "/", label: "Home" },
  { to: "/platform", label: "Our Platform" },
  { to: "/features", label: "Features" },
  { to: "/how-it-works", label: "How It Works" },
] as const;

// "For You" in the mockups has a dropdown chevron but no revealed content —
// these two sub-items are a reasonable placeholder (the product's two real
// audiences per CLAUDE.md: a solo creator automating their own channel, and
// the same pipeline pointed at a business's content). Easy to retitle/trim
// once the real intent for this menu is known.
const FOR_YOU_ITEMS = [
  { to: "/features#creators", label: "For Creators" },
  { to: "/features#businesses", label: "For Businesses" },
] as const;

const TRAILING_TABS = [
  { to: "/about", label: "About" },
  { to: "/faq", label: "FAQ" },
  { to: "/contact", label: "Contact" },
] as const;

const ALL_MOBILE_TABS = [...TABS, ...FOR_YOU_ITEMS, ...TRAILING_TABS];

export function NavBar() {
  const [menuOpen, setMenuOpen] = useState(false);
  const [forYouOpen, setForYouOpen] = useState(false);
  const tapCount = useRef(0);
  const tapTimer = useRef<ReturnType<typeof setTimeout> | null>(null);
  const closeTimer = useRef<ReturnType<typeof setTimeout> | null>(null);

  function handleLogoTap() {
    tapCount.current += 1;
    if (tapTimer.current) clearTimeout(tapTimer.current);

    if (tapCount.current >= 3) {
      tapCount.current = 0;
      window.location.href = APP_LOGIN_URL;
      return;
    }
    tapTimer.current = setTimeout(() => {
      tapCount.current = 0;
    }, TRIPLE_TAP_WINDOW_MS);
  }

  function openForYou() {
    if (closeTimer.current) clearTimeout(closeTimer.current);
    setForYouOpen(true);
  }

  function scheduleCloseForYou() {
    closeTimer.current = setTimeout(() => setForYouOpen(false), 150);
  }

  const linkClass = ({ isActive }: { isActive: boolean }) =>
    `rounded-md px-3.5 py-2 text-sm font-medium transition-colors ${
      isActive ? "bg-white/10 text-white" : "text-white/60 hover:bg-white/5 hover:text-white"
    }`;

  return (
    <header className="sticky top-0 z-50 border-b border-white/10 bg-canvas/80 backdrop-blur-md">
      <div className="mx-auto flex max-w-6xl items-center justify-between px-5 py-3">
        <button
          onClick={handleLogoTap}
          className="flex items-center gap-2 rounded-md transition-opacity hover:opacity-80 active:opacity-60"
          aria-label="NOBS AI"
        >
          <img src="/logo-mark.png" alt="" width={28} height={28} />
          <span className="font-heading text-lg font-bold text-white">
            NOBS <span className="text-gold-400">AI</span>
          </span>
        </button>

        <nav className="hidden items-center gap-1 lg:flex">
          {TABS.map((tab) => (
            <NavLink key={tab.to} to={tab.to} end={tab.to === "/"} className={linkClass}>
              {tab.label}
            </NavLink>
          ))}

          <div
            className="relative"
            onMouseEnter={openForYou}
            onMouseLeave={scheduleCloseForYou}
          >
            <button
              onClick={() => setForYouOpen((v) => !v)}
              className="flex items-center gap-1 rounded-md px-3.5 py-2 text-sm font-medium text-white/60 transition-colors hover:bg-white/5 hover:text-white"
              aria-expanded={forYouOpen}
              aria-haspopup="menu"
            >
              For You
              <ChevronDown size={14} className={`transition-transform ${forYouOpen ? "rotate-180" : ""}`} />
            </button>
            {forYouOpen && (
              <div
                role="menu"
                className="absolute left-0 top-full mt-1 w-44 rounded-xl border border-white/10 bg-panel p-1.5 shadow-xl"
              >
                {FOR_YOU_ITEMS.map((item) => (
                  <NavLink
                    key={item.to}
                    to={item.to}
                    onClick={() => setForYouOpen(false)}
                    className="block rounded-lg px-3 py-2 text-sm text-white/70 transition-colors hover:bg-white/5 hover:text-white"
                  >
                    {item.label}
                  </NavLink>
                ))}
              </div>
            )}
          </div>

          {TRAILING_TABS.map((tab) => (
            <NavLink key={tab.to} to={tab.to} className={linkClass}>
              {tab.label}
            </NavLink>
          ))}
        </nav>

        <NavLink
          to="/waitlist"
          className="hidden items-center gap-2 rounded-full bg-gradient-to-r from-gold-400 to-gold-500 px-5 py-2.5 text-sm font-semibold text-black shadow-lg shadow-gold-500/20 transition-transform hover:scale-[1.03] lg:inline-flex"
        >
          Join Waitlist →
        </NavLink>

        <button
          onClick={() => setMenuOpen((v) => !v)}
          className="rounded-md p-2 text-white/70 hover:bg-white/10 lg:hidden"
          aria-label="Toggle menu"
          aria-expanded={menuOpen}
        >
          {menuOpen ? <X size={20} /> : <Menu size={20} />}
        </button>
      </div>

      {menuOpen && (
        <nav className="flex flex-col gap-1 border-t border-white/10 px-5 py-3 lg:hidden">
          {ALL_MOBILE_TABS.map((tab) => (
            <NavLink
              key={tab.to}
              to={tab.to}
              end={tab.to === "/"}
              onClick={() => setMenuOpen(false)}
              className={({ isActive }) =>
                `rounded-md px-3.5 py-2.5 text-sm font-medium transition-colors ${
                  isActive ? "bg-white/10 text-white" : "text-white/60 hover:bg-white/5 hover:text-white"
                }`
              }
            >
              {tab.label}
            </NavLink>
          ))}
          <NavLink
            to="/waitlist"
            onClick={() => setMenuOpen(false)}
            className="mt-2 inline-flex items-center justify-center gap-2 rounded-full bg-gradient-to-r from-gold-400 to-gold-500 px-5 py-2.5 text-sm font-semibold text-black"
          >
            Join Waitlist →
          </NavLink>
        </nav>
      )}
    </header>
  );
}
