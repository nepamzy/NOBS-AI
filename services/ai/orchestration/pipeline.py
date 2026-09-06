"""Drives a Video through CLAUDE.md's pipeline:

    TOPIC -> RESEARCH -> SCRIPT -> STORYBOARD_REVIEW -> [approval] ->
    VOICE -> VIDEO_GENERATION -> ASSEMBLY -> CAPTIONS -> THUMBNAIL -> COMPLETED

One call advances the video by exactly one stage (or stops it at
STORYBOARD_REVIEW until approved, per "Storyboard" in CLAUDE.md Part 3 —
never generate first and discover a bad script after the fact).

If a stage's engine raises ApprovalRequiredError, that message is stored on
the video (stage_detail) and the stage does NOT advance — the pipeline
parks itself rather than retrying a paid call on its own.
"""

from dataclasses import dataclass

from sqlalchemy.orm import Session

from services.ai.research.engine import ResearchEngine
from services.ai.script.engine import ScriptEngine
from services.common.errors import ApprovalRequiredError
from services.video.engine import VideoEngine
from services.voice.engine import VoiceEngine


@dataclass
class PipelineContext:
    research_engine: ResearchEngine
    script_engine: ScriptEngine
    voice_engine: VoiceEngine
    video_engine: VideoEngine
    storage_root: str


class PipelineBlocked(RuntimeError):
    """Raised (and caught by the worker task) when a stage can't proceed
    without approval or configuration. Carries the human-readable reason."""

    def __init__(self, stage: str, reason: str):
        self.stage = stage
        self.reason = reason
        super().__init__(f"Pipeline blocked at stage '{stage}': {reason}")


def _block(video, db: Session, stage: str, reason: str) -> None:
    """Every blocked stage goes through here so stage_detail always reflects
    *why the current stage* is stuck — never a stale reason left over from
    a stage the video has since moved past."""
    video.stage_detail = reason
    db.commit()
    raise PipelineBlocked(stage, reason)


def advance_one_stage(video, db: Session, ctx: PipelineContext, run_research: bool) -> None:
    from app.models.enums import PipelineStage  # local import: avoids apps/api <-> services cycle
    from app.models.research import Research
    from app.models.script import Scene, Script

    stage = video.stage

    if stage == PipelineStage.TOPIC:
        video.stage = PipelineStage.RESEARCH if run_research else PipelineStage.SCRIPT
        db.commit()
        return

    if stage == PipelineStage.RESEARCH:
        try:
            result = ctx.research_engine.run(video.topic)
        except ApprovalRequiredError as exc:
            _block(video, db, "research", exc.cost_warning.render())

        research = Research(
            video_id=video.id,
            topic=result.topic,
            key_facts=result.key_facts,
            statistics=result.statistics,
            interesting_findings=result.interesting_findings,
            counterarguments=result.counterarguments,
            story_opportunities=result.story_opportunities,
        )
        db.add(research)
        video.stage = PipelineStage.SCRIPT
        video.stage_detail = ""
        db.commit()
        return

    if stage == PipelineStage.SCRIPT:
        research = db.query(Research).filter(Research.video_id == video.id).one_or_none()
        research_result = None
        if research is not None:
            from services.ai.research.engine import ResearchResult

            research_result = ResearchResult(
                topic=research.topic,
                key_facts=research.key_facts,
                statistics=research.statistics,
                interesting_findings=research.interesting_findings,
                counterarguments=research.counterarguments,
                story_opportunities=research.story_opportunities,
            )

        try:
            draft = ctx.script_engine.generate(
                video.topic, video.target_duration_seconds, research_result
            )
        except ApprovalRequiredError as exc:
            _block(video, db, "script", exc.cost_warning.render())

        script = Script(
            video_id=video.id,
            title=draft.title,
            hook=draft.hook,
            estimated_duration_seconds=draft.estimated_duration_seconds,
            word_count=draft.word_count,
        )
        script.scenes = [
            Scene(
                order=s.order,
                narration=s.narration,
                visual_prompt=s.visual_prompt,
                duration_seconds=s.duration_seconds,
                transition=s.transition,
            )
            for s in draft.scenes
        ]
        db.add(script)
        video.stage = PipelineStage.STORYBOARD_REVIEW
        video.stage_detail = "Awaiting storyboard approval"
        video.stage_progress_percent = 0
        db.commit()
        return

    if stage == PipelineStage.STORYBOARD_REVIEW:
        if not video.storyboard_approved:
            _block(video, db, "storyboard_review", "Awaiting storyboard approval")
        video.stage = PipelineStage.VOICE
        video.stage_detail = ""
        db.commit()
        return

    if stage == PipelineStage.VOICE:
        _block(
            video,
            db,
            "voice",
            "Voice synthesis not yet wired into the pipeline runner "
            "(engine adapter exists; per-scene orchestration is a later step)",
        )

    if stage == PipelineStage.VIDEO_GENERATION:
        scene_count = (
            db.query(Scene)
            .join(Script)
            .filter(Script.video_id == video.id)
            .count()
        )
        _block(
            video,
            db,
            "video_generation",
            f"0 of {scene_count} scene clips generated — video generation not "
            "yet wired into the pipeline runner (engine adapter exists; "
            "per-scene orchestration is a later step)",
        )

    if stage == PipelineStage.ASSEMBLY:
        _block(video, db, "assembly", "FFmpeg assembly step not yet wired into the pipeline runner")

    if stage == PipelineStage.CAPTIONS:
        _block(video, db, "captions", "Captions pipeline not yet implemented")

    if stage == PipelineStage.THUMBNAIL:
        _block(video, db, "thumbnail", "Thumbnail generation not yet implemented")

    _block(video, db, stage.value, "No handler for this stage")
