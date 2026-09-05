import { NavLink } from "react-router-dom";

const links = [
  { to: "/", label: "Dashboard", end: true },
  { to: "/create", label: "Create" },
  { to: "/projects", label: "Projects" },
  { to: "/settings", label: "Settings" },
];

export function Sidebar() {
  return (
    <nav className="flex w-56 shrink-0 flex-col gap-1 border-r border-white/10 bg-black/20 p-4">
      <div className="mb-6 px-2 text-lg font-semibold tracking-tight text-white">NOBS AI</div>
      {links.map((link) => (
        <NavLink
          key={link.to}
          to={link.to}
          end={link.end}
          className={({ isActive }) =>
            `rounded-md px-3 py-2 text-sm transition-colors ${
              isActive
                ? "bg-white/10 text-white"
                : "text-white/60 hover:bg-white/5 hover:text-white/90"
            }`
          }
        >
          {link.label}
        </NavLink>
      ))}
    </nav>
  );
}
