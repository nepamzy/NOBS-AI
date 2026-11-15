import { CalendarClock } from "lucide-react";
import { useState } from "react";
import { api, errorMessage } from "../api/client";
import type { Video } from "../api/types";
import { Button } from "./ui";

const TIME_ZONE = Intl.DateTimeFormat().resolvedOptions().timeZone;

/** `<input type="datetime-local">` wants "YYYY-MM-DDTHH:mm" in LOCAL time. */
function toLocalInputValue(date: Date): string {
  const pad = (n: number) => String(n).padStart(2, "0");
  return `${date.getFullYear()}-${pad(date.getMonth() + 1)}-${pad(date.getDate())}T${pad(date.getHours())}:${pad(date.getMinutes())}`;
}

export function formatLocal(iso: string): string {
  return new Date(iso).toLocaleString(undefined, {
    weekday: "short",
    day: "numeric",
    month: "short",
    year: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  });
}

/** Pick the date and time a finished video goes public. The picker is in YOUR
 * local time; the exact moment is sent to the server with its UTC offset, so
 * there is no time-zone guessing. The NOBS AI worker does the publishing. */
export function SchedulePublish({
  video,
  title,
  description,
  onUpdate,
}: {
  video: Video;
  title: string;
  description: string;
  onUpdate: (video: Video) => void;
}) {
  const [when, setWhen] = useState(() => {
    const d = new Date(Date.now() + 24 * 60 * 60 * 1000);
    d.setMinutes(0, 0, 0);
    return toLocalInputValue(d);
  });
  const [earliest] = useState(() => toLocalInputValue(new Date(Date.now() + 5 * 60 * 1000)));
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function handleSchedule() {
    setBusy(true);
    setError(null);
    try {
      onUpdate(
        await api.schedulePublish(video.id, {
          publish_at: new Date(when).toISOString(),
          title: title.trim() || undefined,
          description,
        }),
      );
    } catch (err) {
      setError(errorMessage(err));
    } finally {
      setBusy(false);
    }
  }

  async function handleCancel() {
    setBusy(true);
    setError(null);
    try {
      onUpdate(await api.cancelScheduledPublish(video.id));
    } catch (err) {
      setError(errorMessage(err));
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="mt-4 border-t border-white/10 pt-4">
      <h4 className="flex items-center gap-2 text-sm font-medium text-white">
        <CalendarClock size={15} /> Publish on a date
      </h4>

      {video.scheduled_publish_at ? (
        <div className="mt-2 flex flex-wrap items-center gap-3">
          <p className="text-sm text-emerald-300">
            Scheduled for {formatLocal(video.scheduled_publish_at)}{" "}
            <span className="text-white/40">({TIME_ZONE})</span>
          </p>
          <Button variant="secondary" size="sm" onClick={handleCancel} disabled={busy}>
            Cancel schedule
          </Button>
        </div>
      ) : (
        <>
          <p className="mt-1 text-xs text-white/50">
            It uploads privately and goes public at that moment. Times are in your time zone (
            {TIME_ZONE}).
          </p>
          <div className="mt-2 flex flex-wrap items-center gap-2">
            <input
              type="datetime-local"
              value={when}
              min={earliest}
              onChange={(e) => setWhen(e.target.value)}
              className="rounded-md border border-white/10 bg-black/20 px-3 py-1.5 text-sm text-white [color-scheme:dark]"
            />
            <Button onClick={handleSchedule} disabled={busy || !when}>
              {busy ? "Scheduling…" : "Schedule"}
            </Button>
          </div>
        </>
      )}

      {video.publish_error && (
        <p className="mt-2 text-sm text-amber-300">{video.publish_error}</p>
      )}
      {error && <p className="mt-2 text-sm text-red-400">{error}</p>}
    </div>
  );
}
