import { NavLink, useNavigate } from "react-router-dom";
import { useAuth } from "../auth/AuthContext";

const links = [
  { to: "/", label: "Dashboard", end: true },
  { to: "/create", label: "Create" },
  { to: "/projects", label: "Projects" },
  { to: "/settings", label: "Settings" },
];

export function Sidebar() {
  const { user, logout } = useAuth();
  const navigate = useNavigate();

  async function handleLogout() {
    await logout();
    navigate("/login", { replace: true });
  }

  return (
    <nav className="flex w-56 shrink-0 flex-col gap-1 border-r border-white/10 bg-black/20 p-4">
      <div className="mb-6 flex items-center gap-2 px-2">
        <span className="h-2 w-2 rounded-full bg-accent-500" />
        <span className="font-heading text-lg font-semibold tracking-tight text-white">
          NOBS AI
        </span>
      </div>
      {links.map((link) => (
        <NavLink
          key={link.to}
          to={link.to}
          end={link.end}
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

      <div className="mt-auto flex flex-col gap-2 border-t border-white/10 pt-4">
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
    </nav>
  );
}
