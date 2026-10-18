import {
  BarChart3,
  FolderKanban,
  Home,
  Link2,
  PlaySquare,
  PlusCircle,
  Scissors,
  Send,
  Settings as SettingsIcon,
  ShieldCheck,
  Sparkles,
  Wallet,
  type LucideIcon,
} from "lucide-react";
import { useEffect, useState } from "react";
import { NavLink, useNavigate } from "react-router-dom";
import { api } from "../api/client";
import type { ChannelConnectionStatus } from "../api/types";
import { useAuth } from "../auth/AuthContext";
import { Logo } from "./Logo";

const links: { to: string; label: string; end?: boolean; icon: LucideIcon }[] = [
  { to: "/", label: "Home", end: true, icon: Home },
  { to: "/create", label: "Create Video", icon: PlusCircle },
  { to: "/projects", label: "My Projects", icon: FolderKanban },
  { to: "/library", label: "Video Library", icon: PlaySquare },
  { to: "/clips", label: "Smart Clipping", icon: Scissors },
  { to: "/assistant", label: "AI Assistant", icon: Sparkles },
  { to: "/analytics", label: "Analytics", icon: BarChart3 },
  { to: "/publishing", label: "Publishing", icon: Send },
  { to: "/settings", label: "Settings", icon: SettingsIcon },
];

const adminLinks: { to: string; label: string; icon: LucideIcon }[] = [
  { to: "/admin", label: "Admin Dashboard", icon: ShieldCheck },
  { to: "/connections", label: "Channel Connections", icon: Link2 },
  { to: "/spend", label: "Spending", icon: Wallet },
];

function navLinkClass({ isActive }: { isActive: boolean }): string {
  return `flex items-center gap-2.5 rounded-lg px-3 py-2 text-sm font-medium transition-colors ${
    isActive
      ? "bg-gradient-to-r from-accent-600 to-accent-400 text-white shadow-[0_0_16px_-2px_var(--color-accent-500)]"
      : "text-white/60 hover:bg-white/5 hover:text-white/90"
  }`;
}

/** Real connection state for the sidebar's "Quick Channels" section — the
 * same /connections/status the Channel Connections page uses, not a
 * decorative "always connected" badge. Admin-only, same as that page,
 * since these are shared app-wide integrations, not per-user. */
function QuickChannels() {
  const [channels, setChannels] = useState<ChannelConnectionStatus[] | null>(null);

  useEffect(() => {
    api
      .getConnectionsStatus()
      .then((s) => setChannels(s.youtube_channels))
      .catch(() => setChannels([]));
  }, []);

  if (!channels || channels.length === 0) return null;

  return (
    <div className="mt-6 border-t border-white/10 pt-4">
      <p className="px-3 text-xs font-medium uppercase tracking-wide text-white/40">
        Quick Channels
      </p>
      <div className="mt-2 flex flex-col gap-1.5">
        {channels.map((ch) => (
          <div key={ch.id} className="flex items-center gap-2 rounded-lg px-3 py-1.5">
            <span className="flex h-6 w-6 shrink-0 items-center justify-center rounded-full bg-red-500/90 text-[10px] font-bold text-white">
              YT
            </span>
            <div className="min-w-0 flex-1">
              <p className="truncate text-xs text-white/80">{ch.name}</p>
              <p
                className={`text-[11px] ${ch.connected ? "text-emerald-400" : "text-white/40"}`}
              >
                {ch.connected ? "Connected" : ch.configured ? "Not verified" : "Not connected"}
              </p>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}

export function Sidebar() {
  const { user, logout } = useAuth();
  const navigate = useNavigate();
  const [menuOpen, setMenuOpen] = useState(false);

  async function handleLogout() {
    await logout();
    navigate("/login", { replace: true });
  }

  return (
    <nav className="flex shrink-0 flex-col border-b border-white/10 bg-black/40 p-4 md:h-screen md:w-64 md:overflow-y-auto md:border-r md:border-b-0">
      <div className="flex items-center justify-between gap-2 px-1 md:mb-6">
        <div className="flex items-center gap-2.5">
          <Logo size={30} />
          <div className="leading-tight">
            <span className="block font-heading text-base font-bold tracking-tight text-white">
              NOBS AI
            </span>
            <span className="block text-[11px] text-white/40">Ideas &rarr; Videos &rarr; Growth</span>
          </div>
        </div>
        <button
          onClick={() => setMenuOpen((v) => !v)}
          aria-expanded={menuOpen}
          aria-controls="sidebar-nav-links"
          aria-label={menuOpen ? "Close navigation menu" : "Open navigation menu"}
          className="rounded-md border border-white/10 px-3 py-1.5 text-sm font-medium text-white/70 md:hidden"
        >
          {menuOpen ? "Close" : "Menu"}
        </button>
      </div>

      <div
        id="sidebar-nav-links"
        className={`${menuOpen ? "flex" : "hidden"} mt-3 flex-1 flex-col gap-1 md:mt-0 md:flex`}
      >
        {links.map((link) => (
          <NavLink
            key={link.to}
            to={link.to}
            end={link.end}
            onClick={() => setMenuOpen(false)}
            className={navLinkClass}
          >
            <link.icon size={17} strokeWidth={2} className="shrink-0" />
            {link.label}
          </NavLink>
        ))}
        {user?.role === "admin" &&
          adminLinks.map((link) => (
            <NavLink key={link.to} to={link.to} onClick={() => setMenuOpen(false)} className={navLinkClass}>
              <link.icon size={17} strokeWidth={2} className="shrink-0" />
              {link.label}
            </NavLink>
          ))}

        {user?.role === "admin" && <QuickChannels />}

        <div className="mt-4 flex flex-col gap-2 border-t border-white/10 pt-4 md:mt-auto">
          {user && (
            <div className="flex items-center gap-2.5 px-2">
              <span className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-gradient-to-br from-accent-400 to-accent-600 text-xs font-bold text-white">
                {user.display_name.slice(0, 1).toUpperCase()}
              </span>
              <div className="min-w-0">
                <div className="truncate text-sm text-white/80">{user.display_name}</div>
                <div className="truncate text-xs text-white/40">
                  {user.role === "admin" ? "Admin" : `${user.token_balance} tokens left`}
                </div>
              </div>
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
