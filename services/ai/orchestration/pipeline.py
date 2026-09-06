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
    from app.models.asset import Asset
    from app.models.enums import AssetType, JobStatus, PipelineStage
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
        video.stage = PipelineStage.COMPLIANCE_CHECK
        video.stage_detail = ""
        db.commit()
        return

    if stage == PipelineStage.COMPLIANCE_CHECK:
        from app.models.compliance import ComplianceReport
        from app.models.project import Project
        from app.models.video import Video as VideoModel

        from services.compliance.checker import check_script

        script = db.query(Script).filter(Script.video_id == video.id).one()
        scenes = script.scenes

        owner_id = db.query(Project.owner_id).filter(Project.id == video.project_id).scalar()
        previous_titles = [
            title
            for (title,) in db.query(Script.title)
            .join(VideoModel, VideoModel.id == Script.video_id)
            .join(Project, Project.id == VideoModel.project_id)
            .filter(Project.owner_id == owner_id, VideoModel.id != video.id)
            .all()
        ]

        result = check_script(
            title=script.title,
            hook=script.hook,
            scene_narrations=[s.narration for s in scenes],
            previous_titles=previous_titles,
        )

        db.add(
            ComplianceReport(
                video_id=video.id,
                passed=result.passed,
                blockers=result.blockers,
                warnings=result.warnings,
            )
        )
        db.commit()

        if not result.passed:
            _block(
                video,
                db,
                "compliance_check",
                "Compliance check failed:\n" + "\n".join(f"- {b}" for b in result.blockers),
            )

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
        from pathlib import Path

        from services.rendering.ffmpeg.assembler import AssemblyError, burn_in_captions
        from services.rendering.ffmpeg.captions import build_cues, render_srt

        script = db.query(Script).filter(Script.video_id == video.id).one()
        scenes = script.scenes
        voiceovers = {
            v.scene_id: v for v in db.query(Voiceover).filter(Voiceover.video_id == video.id)
        }

        missing = [s.order for s in scenes if s.id not in voiceovers]
        if missing:
            _block(
                video,
                db,
                "captions",
                f"Scene(s) {missing} missing a voiceover — captions need every "
                "scene's word timestamps",
            )

        # Each scene's offset on the final timeline is the sum of prior
        # scenes' real (measured) voiceover durations — exactly what
        # assembly conformed each scene's clip to, so this lines up without
        # needing to re-measure anything from the assembled video.
        scene_word_timestamps = []
        offset = 0.0
        for scene in scenes:
            vo = voiceovers[scene.id]
            scene_word_timestamps.append((offset, vo.word_timestamps))
            offset += vo.duration_seconds

        cues = build_cues(scene_word_timestamps)
        srt_content = render_srt(cues)

        output_dir = Path(ctx.storage_root) / str(video.id) / "assembly"
        output_dir.mkdir(parents=True, exist_ok=True)
        subtitles_path = output_dir / "captions.srt"
        subtitles_path.write_text(srt_content)

        captioned_path = str(output_dir / "final_captioned.mp4")
        try:
            burn_in_captions(video.final_video_path, str(subtitles_path), captioned_path)
        except AssemblyError as exc:
            _block(video, db, "captions", f"ffmpeg caption burn-in failed: {exc}")

        video.final_video_path = captioned_path
        db.add(
            Asset(
                video_id=video.id,
                asset_type=AssetType.CAPTIONS,
                path=str(subtitles_path),
                label="Captions",
            )
        )
        video.stage = PipelineStage.THUMBNAIL
        video.stage_detail = ""
        db.commit()
        return

    if stage == PipelineStage.THUMBNAIL:
        from pathlib import Path

        from app.models.thumbnail import Thumbnail

        from services.rendering.ffmpeg.assembler import AssemblyError, extract_frame

        total_duration = sum(
            v.duration_seconds
            for v in db.query(Voiceover).filter(Voiceover.video_id == video.id)
        )

        output_dir = Path(ctx.storage_root) / str(video.id) / "assembly"
        output_dir.mkdir(parents=True, exist_ok=True)

        try:
            # Three candidate frames pulled straight from the finished video
            # as thumbnail options (A/B/C) — no separate paid image-generation
            # step needed for a V1 thumbnail picker.
            for label, fraction in (("A", 0.15), ("B", 0.5), ("C", 0.85)):
                image_path = str(output_dir / f"thumbnail_{label}.jpg")
                extract_frame(
                    video.final_video_path, round(total_duration * fraction, 2), image_path
                )
                db.add(Thumbnail(video_id=video.id, image_path=image_path, variant_label=label))
                db.add(
                    Asset(
                        video_id=video.id,
                        asset_type=AssetType.THUMBNAIL,
                        path=image_path,
                        label=f"Thumbnail {label}",
                    )
                )
        except AssemblyError as exc:
            _block(video, db, "thumbnail", f"ffmpeg thumbnail extraction failed: {exc}")

        video.stage = PipelineStage.COMPLETED
        video.stage_detail = ""
        db.commit()
        return

    if stage == PipelineStage.COMPLETED:
        # Terminal state — nothing left to advance.
        return

    _block(video, db, stage.value, "No handler for this stage")
