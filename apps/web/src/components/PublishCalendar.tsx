import { ChevronLeft, ChevronRight } from "lucide-react";
import { useMemo, useState } from "react";
import { Link } from "react-router-dom";
import type { Video } from "../api/types";

const WEEKDAYS = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"];

function dayKey(d: Date): string {
  return `${d.getFullYear()}-${d.getMonth() + 1}-${d.getDate()}`;
}

/** A month view of every video scheduled to go public, in the viewer's own
 * time zone. Click a chip to open that video (reschedule or cancel there). */
export function PublishCalendar({ videos }: { videos: Video[] }) {
  const [cursor, setCursor] = useState(() => {
    const now = new Date();
    return new Date(now.getFullYear(), now.getMonth(), 1);
  });

  const scheduled = useMemo(() => {
    const byDay = new Map<string, { video: Video; at: Date }[]>();
    for (const video of videos) {
      if (!video.scheduled_publish_at) continue;
      const at = new Date(video.scheduled_publish_at);
      const key = dayKey(at);
      byDay.set(key, [...(byDay.get(key) ?? []), { video, at }].sort((a, b) => +a.at - +b.at));
    }
    return byDay;
  }, [videos]);

  const cells = useMemo(() => {
    const first = new Date(cursor);
    const offset = (first.getDay() + 6) % 7; // Monday-first
    const start = new Date(first.getFullYear(), first.getMonth(), 1 - offset);
    const daysInMonth = new Date(first.getFullYear(), first.getMonth() + 1, 0).getDate();
    const total = Math.ceil((offset + daysInMonth) / 7) * 7;
    return Array.from({ length: total }, (_, i) => {
      const d = new Date(start.getFullYear(), start.getMonth(), start.getDate() + i);
      return { date: d, inMonth: d.getMonth() === first.getMonth() };
    });
  }, [cursor]);

  const todayKey = dayKey(new Date());
  const title = cursor.toLocaleString(undefined, { month: "long", year: "numeric" });
  const monthCount = cells.reduce(
    (n, c) => (c.inMonth ? n + (scheduled.get(dayKey(c.date))?.length ?? 0) : n),
    0,
  );

  return (
    <div className="rounded-lg border border-panel-border bg-panel p-4">
      <div className="mb-3 flex items-center justify-between">
        <div>
          <h3 className="font-heading text-base font-semibold text-white">{title}</h3>
          <p className="text-xs text-white/40">
            {monthCount === 0
              ? "Nothing scheduled this month"
              : `${monthCount} video${monthCount === 1 ? "" : "s"} scheduled`}
          </p>
        </div>
        <div className="flex items-center gap-1">
          <button
            aria-label="Previous month"
            onClick={() => setCursor(new Date(cursor.getFullYear(), cursor.getMonth() - 1, 1))}
            className="rounded-md p-1.5 text-white/60 hover:bg-white/10 hover:text-white"
          >
            <ChevronLeft size={18} />
          </button>
          <button
            onClick={() => {
              const now = new Date();
              setCursor(new Date(now.getFullYear(), now.getMonth(), 1));
            }}
            className="rounded-md px-2 py-1 text-xs text-white/60 hover:bg-white/10 hover:text-white"
          >
            Today
          </button>
          <button
            aria-label="Next month"
            onClick={() => setCursor(new Date(cursor.getFullYear(), cursor.getMonth() + 1, 1))}
            className="rounded-md p-1.5 text-white/60 hover:bg-white/10 hover:text-white"
          >
            <ChevronRight size={18} />
          </button>
        </div>
      </div>

      <div className="grid grid-cols-7 gap-px overflow-hidden rounded-md border border-white/10 bg-white/10">
        {WEEKDAYS.map((d) => (
          <div key={d} className="bg-panel px-2 py-1 text-center text-[11px] text-white/40">
            {d}
          </div>
        ))}
        {cells.map(({ date, inMonth }) => {
          const key = dayKey(date);
          const items = scheduled.get(key) ?? [];
          return (
            <div
              key={key}
              className={`min-h-[84px] bg-panel p-1.5 ${inMonth ? "" : "opacity-40"}`}
            >
              <span
                className={`inline-flex h-5 min-w-5 items-center justify-center rounded-full px-1 text-[11px] ${
                  key === todayKey ? "bg-accent-500 font-semibold text-white" : "text-white/60"
                }`}
              >
                {date.getDate()}
              </span>
              <div className="mt-1 flex flex-col gap-1">
                {items.slice(0, 2).map(({ video, at }) => (
                  <Link
                    key={video.id}
                    to={`/videos/${video.id}`}
                    title={`${video.topic} — ${at.toLocaleTimeString(undefined, { hour: "2-digit", minute: "2-digit" })}`}
                    className="truncate rounded bg-accent-500/20 px-1.5 py-0.5 text-[11px] text-accent-300 hover:bg-accent-500/30"
                  >
                    {at.toLocaleTimeString(undefined, { hour: "2-digit", minute: "2-digit" })}{" "}
                    {video.topic}
                  </Link>
                ))}
                {items.length > 2 && (
                  <span className="px-1 text-[11px] text-white/40">+{items.length - 2} more</span>
                )}
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
