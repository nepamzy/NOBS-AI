import { Link } from "react-router-dom";

export function Footer() {
  return (
    <footer className="border-t border-white/10 px-5 py-10">
      <div className="mx-auto flex max-w-6xl flex-col items-center gap-4 text-center sm:flex-row sm:justify-between sm:text-left">
        <div className="flex items-center gap-2">
          <img src="/logo-mark.png" alt="" width={20} height={20} />
          <span className="font-heading text-sm font-semibold text-white">NOBS AI</span>
        </div>
        <p className="text-xs text-white/40">
          © {new Date().getFullYear()} NOBS AI. Not yet open to the public.
        </p>
        <div className="flex gap-5 text-xs text-white/50">
          <Link to="/about" className="hover:text-white">
            About
          </Link>
          <Link to="/contact" className="hover:text-white">
            Contact
          </Link>
          <Link to="/waitlist" className="hover:text-white">
            Join Waitlist
          </Link>
        </div>
      </div>
    </footer>
  );
}
