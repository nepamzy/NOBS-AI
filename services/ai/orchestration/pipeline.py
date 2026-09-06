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
from services.video.engine import SceneClipRequest, VideoEngine
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
    # local imports: avoid an apps/api <-> services import cycle
    from app.models.enums import JobStatus, PipelineStage
    from app.models.research import Research
    from app.models.script import Scene, Script
    from app.models.video_clip import VideoClip
    from app.models.voiceover import Voiceover

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
        script = db.query(Script).filter(Script.video_id == video.id).one()
        scenes = script.scenes
        done = {v.scene_id for v in db.query(Voiceover).filter(Voiceover.video_id == video.id)}

        for scene in scenes:
            if scene.id in done:
                continue
            output_path = f"{ctx.storage_root}/{video.id}/voiceovers/{scene.id}.mp3"
            try:
                result = ctx.voice_engine.synthesize(
                    scene.narration, video.voice_preset, output_path
                )
            except ApprovalRequiredError as exc:
                _block(
                    video,
                    db,
                    "voice",
                    f"{len(done)} of {len(scenes)} scene voiceovers generated "
                    f"(blocked on scene {scene.order}):\n{exc.cost_warning.render()}",
                )

            db.add(
                Voiceover(
                    video_id=video.id,
                    scene_id=scene.id,
                    provider=type(ctx.voice_engine).__name__,
                    audio_path=result.audio_path,
                    duration_seconds=result.duration_seconds,
                    word_timestamps=result.word_timestamps,
                )
            )
            # The measured narration length is ground truth for how long this
            # scene's clip needs to be — the script engine's duration was only
            # ever an estimate. Video generation below targets this, not the
            # guess, which is what keeps the two from drifting apart.
            scene.duration_seconds = round(result.duration_seconds)
            done.add(scene.id)
            video.stage_progress_percent = int(len(done) / len(scenes) * 100)
            db.commit()

        video.stage = PipelineStage.VIDEO_GENERATION
        video.stage_detail = ""
        video.stage_progress_percent = 0
        db.commit()
        return

    if stage == PipelineStage.VIDEO_GENERATION:
        script = db.query(Script).filter(Script.video_id == video.id).one()
        scenes = script.scenes
        done = {
            c.scene_id
            for c in db.query(VideoClip).filter(
                VideoClip.video_id == video.id, VideoClip.status == JobStatus.SUCCEEDED
            )
        }

        for scene in scenes:
            if scene.id in done:
                continue
            output_path = f"{ctx.storage_root}/{video.id}/clips/{scene.id}.mp4"
            # scene.duration_seconds now holds the real, measured voiceover
            # length set in the VOICE stage above, not the original script
            # estimate — request exactly that so nothing needs stretching or
            # trimming to line up later.
            request = SceneClipRequest(
                scene_id=str(scene.id),
                visual_prompt=scene.visual_prompt,
                duration_seconds=scene.duration_seconds,
            )
            try:
                result = ctx.video_engine.generate_clip(request, output_path)
            except ApprovalRequiredError as exc:
                _block(
                    video,
                    db,
                    "video_generation",
                    f"{len(done)} of {len(scenes)} scene clips generated "
                    f"(blocked on scene {scene.order}):\n{exc.cost_warning.render()}",
                )

            db.add(
                VideoClip(
                    video_id=video.id,
                    scene_id=scene.id,
                    provider=type(ctx.video_engine).__name__,
                    status=JobStatus.SUCCEEDED,
                    clip_path=result.clip_path,
                    duration_seconds=result.duration_seconds,
                )
            )
            done.add(scene.id)
            video.stage_progress_percent = int(len(done) / len(scenes) * 100)
            db.commit()

        video.stage = PipelineStage.ASSEMBLY
        video.stage_detail = ""
        video.stage_progress_percent = 0
        db.commit()
        return

    if stage == PipelineStage.ASSEMBLY:
        from pathlib import Path

        from services.rendering.ffmpeg.assembler import (
            AssemblyError,
            concat_clips,
            conform_clip_to_duration,
            mux_voiceover,
        )

        script = db.query(Script).filter(Script.video_id == video.id).one()
        scenes = script.scenes
        clips = {
            c.scene_id: c
            for c in db.query(VideoClip).filter(
                VideoClip.video_id == video.id, VideoClip.status == JobStatus.SUCCEEDED
            )
        }
        voiceovers = {
            v.scene_id: v for v in db.query(Voiceover).filter(Voiceover.video_id == video.id)
        }

        missing = [s.order for s in scenes if s.id not in clips or s.id not in voiceovers]
        if missing:
            _block(
                video,
                db,
                "assembly",
                f"Scene(s) {missing} still missing a clip or voiceover — "
                "assembly needs every scene generated first",
            )

        output_dir = Path(ctx.storage_root) / str(video.id) / "assembly"
        output_dir.mkdir(parents=True, exist_ok=True)

        try:
            scene_paths = []
            for scene in scenes:
                clip = clips[scene.id]
                voiceover = voiceovers[scene.id]
                # Conform each clip to its OWN scene's real voiceover length
                # before concatenation (trim or hold the last frame — never a
                # speed change) so drift can't accumulate across scenes.
                conformed_path = str(output_dir / f"{scene.id}_conformed.mp4")
                conform_clip_to_duration(clip.clip_path, voiceover.duration_seconds, conformed_path)
                muxed_path = str(output_dir / f"{scene.id}_muxed.mp4")
                mux_voiceover(conformed_path, voiceover.audio_path, muxed_path)
                scene_paths.append(muxed_path)

            final_path = str(output_dir / "final.mp4")
            concat_clips(scene_paths, final_path)
        except AssemblyError as exc:
            _block(video, db, "assembly", f"ffmpeg assembly failed: {exc}")

        video.final_video_path = final_path
        video.stage = PipelineStage.CAPTIONS
        video.stage_detail = ""
        db.commit()
        return

    if stage == PipelineStage.CAPTIONS:
        _block(video, db, "captions", "Captions pipeline not yet implemented")

    if stage == PipelineStage.THUMBNAIL:
        _block(video, db, "thumbnail", "Thumbnail generation not yet implemented")

    _block(video, db, stage.value, "No handler for this stage")
