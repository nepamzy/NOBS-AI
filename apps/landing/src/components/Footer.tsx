import { Link } from "react-router-dom";

const LINKS = [
  { to: "/platform", label: "Our Platform" },
  { to: "/features", label: "Features" },
  { to: "/how-it-works", label: "How It Works" },
  { to: "/about", label: "About" },
  { to: "/faq", label: "FAQ" },
  { to: "/contact", label: "Contact" },
] as const;

export function Footer() {
  return (
    <footer className="border-t border-white/10 px-5 py-10">
      <div className="mx-auto flex max-w-6xl flex-col items-center gap-6 text-center sm:flex-row sm:items-start sm:justify-between sm:text-left">
        <div className="flex items-center gap-2">
          <img src="/logo-mark.png" alt="" width={20} height={20} />
          <span className="font-heading text-sm font-semibold text-white">
            NOBS <span className="text-gold-400">AI</span>
          </span>
        </div>

        <nav className="flex flex-wrap items-center justify-center gap-x-5 gap-y-2 text-xs text-white/50">
          {LINKS.map((link) => (
            <Link key={link.to} to={link.to} className="hover:text-white">
              {link.label}
            </Link>
          ))}
        </nav>

        <Link
          to="/waitlist"
          className="rounded-full bg-gradient-to-r from-gold-400 to-gold-500 px-5 py-2 text-xs font-semibold text-black"
        >
          Join Waitlist →
        </Link>
      </div>
      <p className="mx-auto mt-6 max-w-6xl text-center text-[11px] text-white/35 sm:text-left">
        © {new Date().getFullYear()} NOBS AI. Not yet open to the public.
      </p>
    </footer>
  );
}
