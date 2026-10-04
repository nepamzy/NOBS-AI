import { useEffect, useState } from "react";
import { api, errorMessage } from "../api/client";
import type { UploadSchedule } from "../api/types";
import { DurationPicker } from "./DurationPicker";

const DAYS = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"];

function emptyForm() {
  return { dayOfWeek: 0, time: "16:00", topic: "", minutes: 5 };
}

export function UploadSchedules({ projectId }: { projectId: string }) {
  const [schedules, setSchedules] = useState<UploadSchedule[]>([]);
  const [loading, setLoading] = useState(true);
  const [showForm, setShowForm] = useState(false);
  const [form, setForm] = useState(emptyForm());
  const [creating, setCreating] = useState(false);
  const [error, setError] = useState<string | null>(null);

  function refresh() {
    api
      .listSchedules()
      .then((all) => setSchedules(all.filter((s) => s.project_id === projectId)))
      .catch((err) => setError(errorMessage(err)))
      .finally(() => setLoading(false));
  }

  // Wraps the row actions so a failed request shows inline instead of
  // becoming an uncaught promise rejection with no feedback.
  async function runAction(action: () => Promise<unknown>) {
    setError(null);
    try {
      await action();
      refresh();
    } catch (err) {
      setError(errorMessage(err));
    }
  }

  useEffect(refresh, [projectId]);

  async function handleCreate(e: React.FormEvent) {
    e.preventDefault();
    if (!form.topic.trim()) return;
    setCreating(true);
    setError(null);
    try {
      await api.createSchedule({
        project_id: projectId,
        day_of_week: form.dayOfWeek,
        trigger_time: form.time,
        topic: form.topic.trim(),
        target_duration_seconds: form.minutes * 60,
      });
      setForm(emptyForm());
      setShowForm(false);
      refresh();
    } catch (err) {
      setError(errorMessage(err));
    } finally {
      setCreating(false);
    }
  }

  function toggleEnabled(schedule: UploadSchedule) {
    return runAction(() => api.updateSchedule(schedule.id, { enabled: !schedule.enabled }));
  }

  async function toggleAutomation(schedule: UploadSchedule) {
    if (!schedule.auto_publish) {
      const confirmed = window.confirm(
        "Turn automation ON for this schedule?\n\n" +
          "Videos it creates will skip your storyboard review AND get uploaded " +
          "and published to YouTube automatically — no review step, no chance " +
          "to catch a mistake before it's public.\n\n" +
          "Only do this once you've watched this schedule produce several " +
          "good videos manually.",
      );
      if (!confirmed) return;
    }
    await runAction(() =>
      api.updateSchedule(schedule.id, { auto_publish: !schedule.auto_publish }),
    );
  }

  function handleDelete(id: string) {
    return runAction(() => api.deleteSchedule(id));
  }

  if (loading) return null;

  return (
    <div className="mt-8">
      <div className="flex items-center justify-between">
        <h2 className="text-sm font-medium uppercase tracking-wide text-white/50">
          Recurring schedule
        </h2>
        <button
          onClick={() => setShowForm((v) => !v)}
          className="text-xs font-medium text-accent-400 hover:text-accent-300"
        >
          {showForm ? "Cancel" : "+ Add schedule"}
        </button>
      </div>
      <p className="mt-1 text-xs text-white/40">
        Starts generating automatically at the chosen time. Still stops for your storyboard
        review unless you activate automation below.
      </p>

      {error && <p className="mt-3 text-sm text-red-400">{error}</p>}

      {showForm && (
        <form
          onSubmit={handleCreate}
          className="mt-3 flex flex-col gap-3 rounded-md border border-white/10 bg-white/5 p-4"
        >
          <div className="flex flex-wrap gap-3">
            <select
              value={form.dayOfWeek}
              onChange={(e) => setForm({ ...form, dayOfWeek: Number(e.target.value) })}
              className="rounded-md border border-white/10 bg-black/20 px-3 py-1.5 text-sm text-white"
            >
              {DAYS.map((day, i) => (
                <option key={day} value={i}>
                  {day}
                </option>
              ))}
            </select>
            <input
              type="time"
              value={form.time}
              onChange={(e) => setForm({ ...form, time: e.target.value })}
              className="rounded-md border border-white/10 bg-black/20 px-3 py-1.5 text-sm text-white"
            />
            <span className="self-center text-xs text-white/40">UTC — when it starts</span>
          </div>

          <input
            type="text"
            placeholder="Topic (e.g. Storytelling: Hero's Journey)"
            value={form.topic}
            onChange={(e) => setForm({ ...form, topic: e.target.value })}
            className="rounded-md border border-white/10 bg-black/20 px-3 py-1.5 text-sm text-white placeholder:text-white/40"
          />

          <DurationPicker
            minutes={form.minutes}
            onChange={(minutes) => setForm({ ...form, minutes })}
          />

          <button
            type="submit"
            disabled={creating || !form.topic.trim()}
            className="w-fit rounded-md bg-accent-500 px-4 py-2 text-sm font-medium text-white disabled:opacity-50"
          >
            {creating ? "Creating…" : "Create schedule"}
          </button>
        </form>
      )}

      {schedules.length === 0 ? (
        <p className="mt-3 text-sm text-white/40">No recurring schedule for this project yet.</p>
      ) : (
        <ul className="mt-3 flex flex-col gap-2">
          {schedules.map((schedule) => (
            <li
              key={schedule.id}
              className="rounded-md border border-white/10 bg-white/5 p-3 text-sm"
            >
              <div className="flex items-center justify-between gap-3">
                <div className="min-w-0">
                  <p className="text-white">
                    {DAYS[schedule.day_of_week]} at {schedule.trigger_time} UTC
                  </p>
                  <p className="truncate text-xs text-white/50">{schedule.topic}</p>
                </div>
                <div className="flex shrink-0 items-center gap-2">
                  <button
                    onClick={() => toggleEnabled(schedule)}
                    title={schedule.enabled ? "Pause this schedule" : "Resume this schedule"}
                    className={`rounded-full px-2.5 py-1 text-xs font-medium transition-colors ${
                      schedule.enabled
                        ? "bg-emerald-500/15 text-emerald-400"
                        : "bg-white/10 text-white/50"
                    }`}
                  >
                    {schedule.enabled ? "Enabled" : "Paused"}
                  </button>
                  <button
                    onClick={() => handleDelete(schedule.id)}
                    className="text-xs text-white/40 hover:text-red-400"
                  >
                    Delete
                  </button>
                </div>
              </div>

              <div className="mt-2 flex items-center justify-between gap-3 border-t border-white/10 pt-2">
                <p className="text-xs text-white/40">
                  {schedule.auto_publish
                    ? "Automatic — uploads and publishes to YouTube with no review"
                    : "Manual — you review and approve/publish each video"}
                </p>
                <button
                  onClick={() => toggleAutomation(schedule)}
                  className={`shrink-0 rounded-md border px-2.5 py-1 text-xs font-semibold transition-colors ${
                    schedule.auto_publish
                      ? "border-amber-500/40 bg-amber-500/10 text-amber-300 hover:bg-amber-500/20"
                      : "border-accent-500/30 bg-accent-500/10 text-accent-300 hover:bg-accent-500/20"
                  }`}
                >
                  {schedule.auto_publish ? "Deactivate automation" : "Activate automation"}
                </button>
              </div>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
