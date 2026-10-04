import { useState } from "react";
import { NavLink, useNavigate } from "react-router-dom";
import { useAuth } from "../auth/AuthContext";
import { Logo } from "./Logo";

const links = [
  { to: "/", label: "Dashboard", end: true },
  { to: "/create", label: "Create" },
  { to: "/clips", label: "Clips" },
  { to: "/assistant", label: "Assistant" },
  { to: "/projects", label: "Projects" },
  { to: "/settings", label: "Settings" },
];

export function Sidebar() {
  const { user, logout } = useAuth();
  const navigate = useNavigate();
  // Below md the sidebar collapses into a top bar with a Menu toggle — a
  // fixed 224px column left phones ~160px for content and scrolled sideways.
  const [menuOpen, setMenuOpen] = useState(false);

  async function handleLogout() {
    await logout();
    navigate("/login", { replace: true });
  }

  return (
    <nav className="flex shrink-0 flex-col border-b border-white/10 bg-black/20 p-4 md:w-56 md:border-r md:border-b-0">
      <div className="flex items-center justify-between gap-2 px-2 md:mb-6">
        <div className="flex items-center gap-2">
          <Logo size={22} />
          <span className="font-heading text-lg font-semibold tracking-tight text-white">
            NOBS AI
          </span>
        </div>
        <button
          onClick={() => setMenuOpen((v) => !v)}
          aria-expanded={menuOpen}
          className="rounded-md border border-white/10 px-3 py-1.5 text-sm font-medium text-white/70 md:hidden"
        >
          {menuOpen ? "Close" : "Menu"}
        </button>
      </div>

      <div className={`${menuOpen ? "flex" : "hidden"} mt-3 flex-1 flex-col gap-1 md:mt-0 md:flex`}>
        {links.map((link) => (
          <NavLink
            key={link.to}
            to={link.to}
            end={link.end}
            onClick={() => setMenuOpen(false)}
            className={({ isActive }) =>
              `rounded-md px-3 py-2 text-sm font-medium transition-colors ${
                isActive
                  ? "bg-accent-500/15 text-accent-400"
                  : "text-white/60 hover:bg-white/5 hover:text-white/90"
              }`
            }
          >
            {link.label}
          </NavLink>
        ))}
        {user?.role === "admin" && (
          <NavLink
            to="/admin"
            onClick={() => setMenuOpen(false)}
            className={({ isActive }) =>
              `rounded-md px-3 py-2 text-sm font-medium transition-colors ${
                isActive
                  ? "bg-accent-500/15 text-accent-400"
                  : "text-white/60 hover:bg-white/5 hover:text-white/90"
              }`
            }
          >
            Admin
          </NavLink>
        )}

        <div className="mt-4 flex flex-col gap-2 border-t border-white/10 pt-4 md:mt-auto">
          {user && (
            <div className="px-3 text-xs text-white/40">
              <div className="truncate text-white/70">{user.display_name}</div>
              {user.role !== "admin" && <div>{user.token_balance} tokens left</div>}
            </div>
          )}
          <button
            onClick={handleLogout}
            className="rounded-md px-3 py-2 text-left text-sm font-medium text-white/60 transition-colors hover:bg-white/5 hover:text-white/90"
          >
            Log out
          </button>
        </div>
      </div>
    </nav>
  );
}
