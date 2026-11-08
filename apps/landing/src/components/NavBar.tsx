import { Menu, X } from "lucide-react";
import { useRef, useState } from "react";
import { NavLink } from "react-router-dom";

// Where the real product lives — tapping the logo 3x in a row is the
// hidden door back to it for Nobert, never advertised anywhere on the
// page itself. Override via VITE_APP_LOGIN_URL if the app ever moves.
const APP_LOGIN_URL = import.meta.env.VITE_APP_LOGIN_URL ?? "https://nobs-ai.vercel.app/login";
const TRIPLE_TAP_WINDOW_MS = 600;

const TABS = [
  { to: "/", label: "Home" },
  { to: "/about", label: "About" },
  { to: "/contact", label: "Contact" },
  { to: "/waitlist", label: "Join Waitlist" },
] as const;

export function NavBar() {
  const [menuOpen, setMenuOpen] = useState(false);
  const tapCount = useRef(0);
  const tapTimer = useRef<ReturnType<typeof setTimeout> | null>(null);

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

  return (
    <header className="sticky top-0 z-50 border-b border-white/10 bg-canvas/80 backdrop-blur-md">
      <div className="mx-auto flex max-w-6xl items-center justify-between px-5 py-3">
        <button
          onClick={handleLogoTap}
          className="flex items-center gap-2 rounded-md transition-opacity hover:opacity-80 active:opacity-60"
          aria-label="NOBS AI"
        >
          <img src="/logo-mark.png" alt="" width={28} height={28} />
          <span className="font-heading text-lg font-bold text-white">NOBS AI</span>
        </button>

        <nav className="hidden items-center gap-1 sm:flex">
          {TABS.map((tab) => (
            <NavLink
              key={tab.to}
              to={tab.to}
              end={tab.to === "/"}
              className={({ isActive }) =>
                `rounded-md px-3.5 py-2 text-sm font-medium transition-colors ${
                  isActive
                    ? "bg-white/10 text-white"
                    : "text-white/60 hover:bg-white/5 hover:text-white"
                } ${tab.to === "/waitlist" ? "ml-2 bg-gradient-to-r from-accent-600 to-accent-400 text-white hover:opacity-90" : ""}`
              }
            >
              {tab.label}
            </NavLink>
          ))}
        </nav>

        <button
          onClick={() => setMenuOpen((v) => !v)}
          className="rounded-md p-2 text-white/70 hover:bg-white/10 sm:hidden"
          aria-label="Toggle menu"
          aria-expanded={menuOpen}
        >
          {menuOpen ? <X size={20} /> : <Menu size={20} />}
        </button>
      </div>

      {menuOpen && (
        <nav className="flex flex-col gap-1 border-t border-white/10 px-5 py-3 sm:hidden">
          {TABS.map((tab) => (
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
        </nav>
      )}
    </header>
  );
}
