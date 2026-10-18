import type { ReactNode } from "react";
import { Link } from "react-router-dom";

/** Flat panel surface (NOBS AI Frontend Blueprint: canvas #090D1B behind
 * everything, panels #11172B on top) — the shared card/section container
 * used across every screen instead of each page inventing its own. */
export function Panel({
  className = "",
  children,
}: {
  className?: string;
  children: ReactNode;
}) {
  return (
    <div className={`rounded-lg border border-panel-border bg-panel p-5 ${className}`}>
      {children}
    </div>
  );
}

type ButtonVariant = "primary" | "secondary" | "ghost" | "danger" | "success";

const BUTTON_VARIANTS: Record<ButtonVariant, string> = {
  primary: "bg-accent-500 text-white hover:bg-accent-600",
  secondary: "border border-white/15 text-white/80 hover:border-white/30 hover:text-white",
  ghost: "text-white/60 hover:bg-white/5 hover:text-white",
  danger: "border border-red-500/30 bg-red-500/10 text-red-300 hover:bg-red-500/20",
  // Reserved for the one class of action that's genuinely irreversible/costly
  // (approve storyboard, publish) — a deliberate "money gate" signal, kept
  // distinct from the brand accent used for ordinary primary actions.
  success: "bg-emerald-500 text-black hover:bg-emerald-400",
};

type ButtonSize = "sm" | "md";

const BUTTON_SIZES: Record<ButtonSize, string> = {
  sm: "px-2.5 py-1 text-xs",
  md: "px-4 py-2 text-sm",
};

export function Button({
  variant = "primary",
  size = "md",
  className = "",
  type = "button",
  ...props
}: React.ButtonHTMLAttributes<HTMLButtonElement> & {
  variant?: ButtonVariant;
  size?: ButtonSize;
}) {
  return (
    <button
      type={type}
      className={`rounded-md font-medium transition-colors disabled:cursor-not-allowed disabled:opacity-40 ${BUTTON_SIZES[size]} ${BUTTON_VARIANTS[variant]} ${className}`}
      {...props}
    />
  );
}

export type Tone = "success" | "warning" | "error" | "info" | "neutral";

const TONE_CLASSES: Record<Tone, string> = {
  success: "border-emerald-500/40 bg-emerald-500/10 text-emerald-300",
  warning: "border-amber-500/40 bg-amber-500/10 text-amber-300",
  error: "border-red-500/40 bg-red-500/10 text-red-300",
  info: "border-sky-500/40 bg-sky-500/10 text-sky-300",
  neutral: "border-white/10 bg-white/5 text-white/50",
};

/** Status indicator for anything with a real, known state (video/project
 * stage, schedule enabled/paused, publish status). Never render one for a
 * state that hasn't actually been confirmed — use `neutral` ("Unknown" /
 * "No videos yet") instead of guessing. */
export function StatusPill({ tone, label }: { tone: Tone; label: string }) {
  return (
    <span
      className={`inline-flex items-center rounded-full border px-2.5 py-0.5 text-xs font-medium ${TONE_CLASSES[tone]}`}
    >
      {label}
    </span>
  );
}

export function ErrorState({ message }: { message: string }) {
  return (
    <div className="rounded-md border border-red-500/30 bg-red-500/10 px-4 py-3 text-sm text-red-300">
      {message}
    </div>
  );
}

export function EmptyState({
  title,
  description,
  actionLabel,
  actionTo,
}: {
  title: string;
  description?: string;
  actionLabel?: string;
  actionTo?: string;
}) {
  return (
    <div className="rounded-lg border border-dashed border-white/15 px-6 py-10 text-center">
      <p className="text-white/70">{title}</p>
      {description && <p className="mt-1 text-sm text-white/40">{description}</p>}
      {actionLabel && actionTo && (
        <Link
          to={actionTo}
          className="mt-4 inline-block rounded-md bg-accent-500 px-4 py-2 text-sm font-medium text-white transition-colors hover:bg-accent-600"
        >
          {actionLabel}
        </Link>
      )}
    </div>
  );
}

export function PermissionDeniedState({ message }: { message?: string }) {
  return (
    <div className="rounded-lg border border-white/10 bg-white/5 px-6 py-10 text-center">
      <p className="text-white/70">You don't have access to this.</p>
      {message && <p className="mt-1 text-sm text-white/40">{message}</p>}
    </div>
  );
}
