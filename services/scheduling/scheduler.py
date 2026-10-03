"""Fires due UploadSchedule rows by creating a real Video and handing it to
the EXACT SAME pipeline a manually created video goes through (CLAUDE.md's
Topic -> Research -> Script -> Storyboard -> [approval] -> ... pipeline).

By default this stops at the same STORYBOARD_REVIEW checkpoint a manual
video does — nothing extra was built to enforce that, reusing the real
pipeline means the safety comes for free. The one opt-in exception is
`schedule.auto_publish` (off by default, per Nobert's own instruction:
watch it produce a few good videos manually first, then flip it on once
he trusts it) — set on the Video it creates, read by
apps/api/app/jobs/tasks.py to skip the storyboard wait AND upload +
publish to YouTube automatically once finished. Off, this schedule is
exactly as safe as a manual video; on, Nobert made that call deliberately
and can switch it back off at any time.

Runs inside apps/worker/worker.py via SchedulerRunner, in a background
thread (APScheduler), alongside the RQ worker loop in the same process.
"""

from datetime import datetime, timezone

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from sqlalchemy import or_
from sqlalchemy.orm import Session

_CHECK_INTERVAL_SECONDS = 60


def check_and_trigger_due_schedules(db: Session) -> list[str]:
    """Runs one due-check pass. Returns a list of human-readable results
    (one per schedule that fired or failed) — plain return value, not
    exceptions, so one bad schedule can't stop the others from firing."""
    # Local imports: avoid an apps/api <-> services import cycle (same
    # reasoning as services/ai/orchestration/pipeline.py).
    from app.models.upload_schedule import UploadSchedule
    from app.routers.videos import create_video
    from app.schemas.video import VideoCreate

    now = datetime.now(timezone.utc)
    today = now.strftime("%Y-%m-%d")
    current_time = now.strftime("%H:%M")
    current_weekday = now.weekday()  # 0=Monday, matches UploadSchedule.day_of_week

    due = (
        db.query(UploadSchedule)
        .filter(
            UploadSchedule.enabled.is_(True),
            UploadSchedule.day_of_week == current_weekday,
            UploadSchedule.trigger_time == current_time,
            # Plain `!= today` would silently exclude every schedule that
            # has never fired (last_triggered_on IS NULL) — SQL's
            # three-valued logic makes `NULL != 'x'` neither true nor false.
            or_(
                UploadSchedule.last_triggered_on.is_(None),
                UploadSchedule.last_triggered_on != today,
            ),
        )
        .all()
    )

    results = []
    for schedule in due:
        owner = schedule.project.owner
        try:
            video = create_video(
                VideoCreate(
                    project_id=schedule.project_id,
                    topic=schedule.topic,
                    target_duration_seconds=schedule.target_duration_seconds,
                    voice_preset=schedule.voice_preset,
                    style_preset=schedule.style_preset,
                    run_research=schedule.run_research,
                ),
                db=db,
                user=owner,
            )
            video.auto_publish = schedule.auto_publish
            schedule.last_triggered_on = today
            db.commit()
            results.append(f"schedule {schedule.id}: created video {video.id}")
        except Exception as exc:  # noqa: BLE001 - one bad schedule must not break the rest
            db.rollback()
            results.append(f"schedule {schedule.id}: failed to trigger ({exc})")

    return results


class SchedulerRunner:
    """Thin wrapper so apps/worker/worker.py can start/stop this with two
    lines, without the worker needing to know APScheduler exists."""

    def __init__(self, session_factory):
        self._session_factory = session_factory
        self._scheduler = BackgroundScheduler()

    def _tick(self) -> None:
        db = self._session_factory()
        try:
            check_and_trigger_due_schedules(db)
        finally:
            db.close()

    def start(self) -> None:
        self._scheduler.add_job(
            self._tick,
            CronTrigger(second=0),  # check once per minute, on the minute
            id="upload_schedule_check",
            replace_existing=True,
        )
        self._scheduler.start()

    def stop(self) -> None:
        self._scheduler.shutdown(wait=False)
