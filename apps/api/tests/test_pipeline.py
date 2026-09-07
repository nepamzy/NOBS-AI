from pathlib import Path

import pytest
from app.models.asset import Asset
from app.models.compliance import ComplianceReport
from app.models.enums import AssetType, JobStatus, PipelineStage
from app.models.project import Project
from app.models.research import Research
from app.models.script import Script
from app.models.thumbnail import Thumbnail
from app.models.user import User
from app.models.video import Video
from app.models.video_clip import VideoClip
from app.models.voiceover import Voiceover

from services.ai.orchestration.pipeline import PipelineBlocked, PipelineContext, advance_one_stage
from services.ai.research.engine import ResearchEngine, ResearchResult
from services.ai.script.engine import SceneDraft, ScriptDraft, ScriptEngine
from services.common.errors import ApprovalRequiredError, CostWarning
from services.video.engine import SceneClipRequest, SceneClipResult, VideoEngine
from services.video.wan.adapter import WanEngine
from services.voice.chatterbox.adapter import ChatterboxEngine
from services.voice.engine import VoiceEngine, VoiceoverResult


def _make_video(db_session, topic="topic", duration=60) -> Video:
    user = User(email="nobert@local", display_name="Nobert", password_hash="test-hash")
    db_session.add(user)
    db_session.flush()
    project = Project(owner_id=user.id, name="p")
    db_session.add(project)
    db_session.flush()
    video = Video(project_id=project.id, topic=topic, target_duration_seconds=duration)
    db_session.add(video)
    db_session.flush()
    return video


def _unconfigured_context() -> PipelineContext:
    return PipelineContext(
        research_engine=ResearchEngine(llm_provider="", llm_api_key=""),
        script_engine=ScriptEngine(llm_provider="", llm_api_key=""),
        voice_engine=ChatterboxEngine(api_url=""),
        video_engine=WanEngine(runpod_api_key="", wan_endpoint_id=""),
        storage_root="./storage/local",
    )


def test_topic_stage_skips_research_when_disabled(db_session):
    video = _make_video(db_session)
    ctx = _unconfigured_context()

    advance_one_stage(video, db_session, ctx, run_research=False)

    assert video.stage.value == "script"


def test_research_stage_blocks_without_llm_config(db_session):
    video = _make_video(db_session)
    video.stage = PipelineStage.RESEARCH
    db_session.flush()
    ctx = _unconfigured_context()

    with pytest.raises(PipelineBlocked) as exc_info:
        advance_one_stage(video, db_session, ctx, run_research=True)

    assert exc_info.value.stage == "research"
    assert "PAYMENT / COST WARNING" in video.stage_detail
    assert video.stage.value == "research"  # never advanced past the gate


class _FakeResearchEngine(ResearchEngine):
    def __init__(self):
        pass

    def run(self, topic):
        return ResearchResult(topic=topic, key_facts=["fact one"])


class _FakeScriptEngine(ScriptEngine):
    def __init__(self):
        pass

    def generate(self, topic, target_duration_seconds, research=None):
        return ScriptDraft(
            title="Title",
            hook="Hook",
            estimated_duration_seconds=target_duration_seconds,
            word_count=50,
            scenes=[
                SceneDraft(order=1, narration="n1", visual_prompt="v1", duration_seconds=8),
                SceneDraft(order=2, narration="n2", visual_prompt="v2", duration_seconds=8),
            ],
        )


def test_full_free_path_reaches_storyboard_review_and_waits_for_approval(db_session):
    video = _make_video(db_session)
    ctx = PipelineContext(
        research_engine=_FakeResearchEngine(),
        script_engine=_FakeScriptEngine(),
        voice_engine=ChatterboxEngine(api_url=""),
        video_engine=WanEngine(runpod_api_key="", wan_endpoint_id=""),
        storage_root="./storage/local",
    )

    advance_one_stage(video, db_session, ctx, run_research=True)  # TOPIC -> RESEARCH
    advance_one_stage(video, db_session, ctx, run_research=True)  # RESEARCH -> SCRIPT
    advance_one_stage(video, db_session, ctx, run_research=True)  # SCRIPT -> STORYBOARD_REVIEW

    assert video.stage.value == "storyboard_review"
    research = db_session.query(Research).filter(Research.video_id == video.id).one()
    assert research.key_facts == ["fact one"]
    script = db_session.query(Script).filter(Script.video_id == video.id).one()
    assert [s.order for s in script.scenes] == [1, 2]

    with pytest.raises(PipelineBlocked) as exc_info:
        advance_one_stage(video, db_session, ctx, run_research=True)
    assert exc_info.value.stage == "storyboard_review"
    assert video.stage_detail == "Awaiting storyboard approval"

    video.storyboard_approved = True
    db_session.flush()
    advance_one_stage(video, db_session, ctx, run_research=True)  # -> COMPLIANCE_CHECK
    assert video.stage.value == "compliance_check"
    advance_one_stage(video, db_session, ctx, run_research=True)  # COMPLIANCE_CHECK -> VOICE
    assert video.stage.value == "voice"
    assert video.stage_detail == ""  # cleared, not left over from storyboard_review

    # advance_one_stage moves one stage per call, so the next call attempts
    # "voice" and blocks — stage_detail must reflect *that* block, not the
    # stale "Awaiting storyboard approval" message from the previous stage.
    with pytest.raises(PipelineBlocked) as exc_info:
        advance_one_stage(video, db_session, ctx, run_research=True)
    assert exc_info.value.stage == "voice"
    assert video.stage_detail != "Awaiting storyboard approval"
    assert "0 of 2 scene voiceovers generated" in video.stage_detail
    assert "PAYMENT / COST WARNING" in video.stage_detail


class _FakeVoiceEngine(VoiceEngine):
    """Duration is derived from the narration text and deliberately
    different from the script engine's guessed scene duration, so tests can
    prove the pipeline re-targets video generation at the *measured*
    length rather than the original estimate."""

    def __init__(self):
        self.calls: list[tuple[str, str, str]] = []

    def synthesize(self, text: str, voice_preset: str, output_path: str) -> VoiceoverResult:
        self.calls.append((text, voice_preset, output_path))
        duration = len(text) * 0.5
        return VoiceoverResult(
            audio_path=output_path,
            duration_seconds=duration,
            word_timestamps=[{"word": text, "start": 0.0, "end": duration}],
        )


class _BlockingVoiceEngine(VoiceEngine):
    def synthesize(self, text: str, voice_preset: str, output_path: str) -> VoiceoverResult:
        raise ApprovalRequiredError(
            CostWarning(
                action="synthesize",
                service="test",
                expected_cost="unknown",
                billing_type="unknown",
                max_expected_cost="unknown",
                risk="Unknown",
                why_needed="test",
            )
        )


class _FakeVideoEngine(VideoEngine):
    def __init__(self):
        self.calls: list[SceneClipRequest] = []

    def generate_clip(self, request: SceneClipRequest, output_path: str) -> SceneClipResult:
        self.calls.append(request)
        return SceneClipResult(clip_path=output_path, duration_seconds=request.duration_seconds)


def _advance_to_voice(db_session):
    video = _make_video(db_session)
    fake_voice = _FakeVoiceEngine()
    fake_video = _FakeVideoEngine()
    ctx = PipelineContext(
        research_engine=_FakeResearchEngine(),
        script_engine=_FakeScriptEngine(),
        voice_engine=fake_voice,
        video_engine=fake_video,
        storage_root="./storage/local",
    )
    advance_one_stage(video, db_session, ctx, run_research=True)  # TOPIC -> RESEARCH
    advance_one_stage(video, db_session, ctx, run_research=True)  # RESEARCH -> SCRIPT
    advance_one_stage(video, db_session, ctx, run_research=True)  # SCRIPT -> STORYBOARD_REVIEW
    video.storyboard_approved = True
    db_session.flush()
    advance_one_stage(video, db_session, ctx, run_research=True)  # -> COMPLIANCE_CHECK
    advance_one_stage(video, db_session, ctx, run_research=True)  # COMPLIANCE_CHECK -> VOICE
    return video, ctx, fake_voice, fake_video


def test_voice_stage_syncs_scene_duration_to_measured_voiceover_length(db_session):
    video, ctx, fake_voice, _fake_video = _advance_to_voice(db_session)
    script = db_session.query(Script).filter(Script.video_id == video.id).one()
    original_durations = {s.id: s.duration_seconds for s in script.scenes}

    advance_one_stage(video, db_session, ctx, run_research=True)  # VOICE -> VIDEO_GENERATION

    assert video.stage.value == "video_generation"
    assert len(fake_voice.calls) == 2  # one synthesize call per scene

    voiceovers = db_session.query(Voiceover).filter(Voiceover.video_id == video.id).all()
    assert len(voiceovers) == 2
    assert {v.scene_id for v in voiceovers} == {s.id for s in script.scenes}

    db_session.refresh(script)
    for scene in script.scenes:
        vo = next(v for v in voiceovers if v.scene_id == scene.id)
        # scene.duration_seconds was overwritten with the *measured*
        # voiceover length, not left at the script engine's 8s estimate —
        # this is the anchor that keeps video generation and narration in
        # sync instead of drifting apart.
        assert scene.duration_seconds == round(vo.duration_seconds)
        assert scene.duration_seconds != original_durations[scene.id]


def test_voice_stage_blocks_without_losing_scenes_already_synthesized(db_session):
    video = _make_video(db_session)
    ctx = PipelineContext(
        research_engine=_FakeResearchEngine(),
        script_engine=_FakeScriptEngine(),
        voice_engine=_BlockingVoiceEngine(),
        video_engine=_FakeVideoEngine(),
        storage_root="./storage/local",
    )
    advance_one_stage(video, db_session, ctx, run_research=True)  # TOPIC -> RESEARCH
    advance_one_stage(video, db_session, ctx, run_research=True)  # RESEARCH -> SCRIPT
    advance_one_stage(video, db_session, ctx, run_research=True)  # SCRIPT -> STORYBOARD_REVIEW
    video.storyboard_approved = True
    db_session.flush()
    advance_one_stage(video, db_session, ctx, run_research=True)  # -> COMPLIANCE_CHECK
    advance_one_stage(video, db_session, ctx, run_research=True)  # COMPLIANCE_CHECK -> VOICE

    with pytest.raises(PipelineBlocked) as exc_info:
        advance_one_stage(video, db_session, ctx, run_research=True)
    assert exc_info.value.stage == "voice"
    assert "0 of 2 scene voiceovers generated" in video.stage_detail
    assert "blocked on scene 1" in video.stage_detail


def test_video_generation_stage_requests_measured_duration_not_original_estimate(db_session):
    video, ctx, _fake_voice, fake_video = _advance_to_voice(db_session)
    advance_one_stage(video, db_session, ctx, run_research=True)  # VOICE -> VIDEO_GENERATION
    advance_one_stage(video, db_session, ctx, run_research=True)  # VIDEO_GENERATION -> ASSEMBLY

    assert video.stage.value == "assembly"
    assert len(fake_video.calls) == 2
    for request in fake_video.calls:
        # 8s was the script engine's estimate for both scenes; the real
        # voiceover for "n1"/"n2" measures 1.0s (len(text) * 0.5) — the clip
        # request must target that measured value, not the estimate, or the
        # generated clip won't match its narration's real length.
        assert request.duration_seconds == 1
        assert request.duration_seconds != 8

    clips = db_session.query(VideoClip).filter(VideoClip.video_id == video.id).all()
    assert len(clips) == 2
    assert all(c.status == JobStatus.SUCCEEDED for c in clips)


def test_assembly_stage_conforms_and_muxes_each_scene_before_concatenating(db_session, monkeypatch):
    video, ctx, _fake_voice, _fake_video = _advance_to_voice(db_session)
    advance_one_stage(video, db_session, ctx, run_research=True)  # VOICE -> VIDEO_GENERATION
    advance_one_stage(video, db_session, ctx, run_research=True)  # VIDEO_GENERATION -> ASSEMBLY

    from services.rendering.ffmpeg import assembler

    conform_calls: list[tuple[str, float, str]] = []
    mux_calls: list[tuple[str, str, str]] = []
    concat_calls: list[tuple[list[str], str]] = []

    monkeypatch.setattr(
        assembler,
        "conform_clip_to_duration",
        lambda clip_path, target_seconds, output_path: conform_calls.append(
            (clip_path, target_seconds, output_path)
        ),
    )
    monkeypatch.setattr(
        assembler,
        "mux_voiceover",
        lambda video_path, audio_path, output_path: mux_calls.append(
            (video_path, audio_path, output_path)
        ),
    )
    monkeypatch.setattr(
        assembler,
        "concat_clips",
        lambda clip_paths, output_path: concat_calls.append((clip_paths, output_path)),
    )

    advance_one_stage(video, db_session, ctx, run_research=True)  # ASSEMBLY -> CAPTIONS

    assert video.stage.value == "captions"
    assert video.final_video_path is not None

    voiceovers = db_session.query(Voiceover).filter(Voiceover.video_id == video.id).all()
    measured_durations = {vo.duration_seconds for vo in voiceovers}

    # Every scene's clip was conformed to ITS OWN voiceover's measured
    # duration (never a whole-video average or a speed change) before any
    # concatenation happened.
    assert len(conform_calls) == 2
    for _clip_path, target_seconds, _output_path in conform_calls:
        assert target_seconds in measured_durations

    assert len(mux_calls) == 2
    # each mux call's video input is the corresponding conform call's output
    conformed_outputs = {c[2] for c in conform_calls}
    assert {m[0] for m in mux_calls} == conformed_outputs

    assert len(concat_calls) == 1
    assert len(concat_calls[0][0]) == 2  # both scenes' muxed clips concatenated


def test_assembly_skips_music_when_library_is_empty(db_session, monkeypatch):
    video, ctx, _fake_voice, _fake_video = _advance_to_voice(db_session)
    advance_one_stage(video, db_session, ctx, run_research=True)  # VOICE -> VIDEO_GENERATION
    advance_one_stage(video, db_session, ctx, run_research=True)  # VIDEO_GENERATION -> ASSEMBLY

    from services.rendering.ffmpeg import assembler

    monkeypatch.setattr(assembler, "conform_clip_to_duration", lambda *a, **k: None)
    monkeypatch.setattr(assembler, "mux_voiceover", lambda *a, **k: None)
    monkeypatch.setattr(assembler, "concat_clips", lambda *a, **k: None)
    mix_calls = []
    monkeypatch.setattr(
        assembler,
        "mix_background_music",
        lambda *a, **k: mix_calls.append(a),
    )

    advance_one_stage(video, db_session, ctx, run_research=True)  # ASSEMBLY -> CAPTIONS

    # ctx.music_library_path defaults to a folder that doesn't exist in
    # tests — an empty/missing library must never block assembly.
    assert video.stage.value == "captions"
    assert video.music_track is None
    assert mix_calls == []


def test_assembly_mixes_music_when_library_has_tracks(db_session, monkeypatch, tmp_path):
    (tmp_path / "song.mp3").write_bytes(b"")

    video, ctx, _fake_voice, _fake_video = _advance_to_voice(db_session)
    ctx.music_library_path = str(tmp_path)
    advance_one_stage(video, db_session, ctx, run_research=True)  # VOICE -> VIDEO_GENERATION
    advance_one_stage(video, db_session, ctx, run_research=True)  # VIDEO_GENERATION -> ASSEMBLY

    from services.rendering.ffmpeg import assembler

    monkeypatch.setattr(assembler, "conform_clip_to_duration", lambda *a, **k: None)
    monkeypatch.setattr(assembler, "mux_voiceover", lambda *a, **k: None)
    monkeypatch.setattr(assembler, "concat_clips", lambda *a, **k: None)
    mix_calls = []
    monkeypatch.setattr(
        assembler,
        "mix_background_music",
        lambda video_path, music_path, output_path: mix_calls.append(
            (video_path, music_path, output_path)
        ),
    )

    advance_one_stage(video, db_session, ctx, run_research=True)  # ASSEMBLY -> CAPTIONS

    assert video.stage.value == "captions"
    assert video.music_track == "song.mp3"
    assert len(mix_calls) == 1
    _video_path, music_path, output_path = mix_calls[0]
    assert music_path == str(tmp_path / "song.mp3")
    assert video.final_video_path == output_path


def _advance_to_captions(db_session, monkeypatch):
    """Drives a video through VOICE -> VIDEO_GENERATION -> ASSEMBLY with the
    ffmpeg-backed assembler calls stubbed out (ffmpeg isn't installed in this
    sandbox), landing on CAPTIONS with a final_video_path already set."""
    video, ctx, fake_voice, fake_video = _advance_to_voice(db_session)
    advance_one_stage(video, db_session, ctx, run_research=True)  # VOICE -> VIDEO_GENERATION
    advance_one_stage(video, db_session, ctx, run_research=True)  # VIDEO_GENERATION -> ASSEMBLY

    from services.rendering.ffmpeg import assembler

    monkeypatch.setattr(assembler, "conform_clip_to_duration", lambda *a, **k: None)
    monkeypatch.setattr(assembler, "mux_voiceover", lambda *a, **k: None)
    monkeypatch.setattr(assembler, "concat_clips", lambda *a, **k: None)

    advance_one_stage(video, db_session, ctx, run_research=True)  # ASSEMBLY -> CAPTIONS
    assert video.stage.value == "captions"
    return video, ctx, fake_voice, fake_video


def test_captions_stage_builds_srt_from_real_word_timestamps_and_burns_it_in(
    db_session, monkeypatch
):
    video, ctx, _fake_voice, _fake_video = _advance_to_captions(db_session, monkeypatch)

    from services.rendering.ffmpeg import assembler

    burn_calls = []
    monkeypatch.setattr(
        assembler,
        "burn_in_captions",
        lambda video_path, subtitles_path, output_path: burn_calls.append(
            (video_path, subtitles_path, output_path)
        ),
    )

    advance_one_stage(video, db_session, ctx, run_research=True)  # CAPTIONS -> THUMBNAIL

    assert video.stage.value == "thumbnail"
    assert len(burn_calls) == 1
    _video_path, subtitles_path, output_path = burn_calls[0]
    assert video.final_video_path == output_path  # captioned output replaces the prior final path

    srt_content = Path(subtitles_path).read_text()
    # both scenes' narration ("n1"/"n2" from _FakeScriptEngine) made it into
    # the subtitle file, using the *measured* voiceover timestamps
    assert "n1" in srt_content
    assert "n2" in srt_content

    assets = db_session.query(Asset).filter(Asset.video_id == video.id).all()
    caption_assets = [a for a in assets if a.asset_type.value == "captions"]
    assert len(caption_assets) == 1


def test_thumbnail_stage_extracts_three_candidate_frames(db_session, monkeypatch):
    video, ctx, _fake_voice, _fake_video = _advance_to_captions(db_session, monkeypatch)

    from services.rendering.ffmpeg import assembler

    monkeypatch.setattr(assembler, "burn_in_captions", lambda *a, **k: None)
    advance_one_stage(video, db_session, ctx, run_research=True)  # CAPTIONS -> THUMBNAIL

    extract_calls = []
    monkeypatch.setattr(
        assembler,
        "extract_frame",
        lambda video_path, timestamp_seconds, output_path: extract_calls.append(
            (video_path, timestamp_seconds, output_path)
        ),
    )

    advance_one_stage(video, db_session, ctx, run_research=True)  # THUMBNAIL -> COMPLETED

    assert video.stage.value == "completed"
    assert len(extract_calls) == 3
    labels = {Path(c[2]).stem for c in extract_calls}
    assert {"thumbnail_A", "thumbnail_B", "thumbnail_C"} == labels
    # three distinct timestamps spread across the video, not all the same frame
    assert len({c[1] for c in extract_calls}) == 3

    thumbnails = db_session.query(Thumbnail).filter(Thumbnail.video_id == video.id).all()
    assert len(thumbnails) == 3
    assert {t.variant_label for t in thumbnails} == {"A", "B", "C"}


class _FakeStorageBackend:
    def __init__(self):
        self.calls: list[tuple[str, str]] = []

    def upload(self, local_path: str, key: str) -> str:
        self.calls.append((local_path, key))
        return f"https://fake.supabase.co/storage/v1/object/public/nobs-ai/{key}"


def test_thumbnail_stage_uploads_final_video_captions_and_thumbnails(db_session, monkeypatch):
    video, ctx, _fake_voice, _fake_video = _advance_to_captions(db_session, monkeypatch)
    fake_storage = _FakeStorageBackend()
    ctx.storage_backend = fake_storage

    from services.rendering.ffmpeg import assembler

    monkeypatch.setattr(assembler, "burn_in_captions", lambda *a, **k: None)
    advance_one_stage(video, db_session, ctx, run_research=True)  # CAPTIONS -> THUMBNAIL
    local_final_path = video.final_video_path  # captured before THUMBNAIL uploads it

    monkeypatch.setattr(assembler, "extract_frame", lambda *a, **k: None)
    advance_one_stage(video, db_session, ctx, run_research=True)  # THUMBNAIL -> COMPLETED

    assert video.stage.value == "completed"
    # final video, captions, and all three thumbnails were each uploaded once
    assert len(fake_storage.calls) == 5
    uploaded_local_paths = {c[0] for c in fake_storage.calls}
    assert local_final_path in uploaded_local_paths

    # the stored paths are now the uploaded URLs, not local disk paths
    assert video.final_video_path == (
        f"https://fake.supabase.co/storage/v1/object/public/nobs-ai/{video.id}/final.mp4"
    )
    captions_asset = (
        db_session.query(Asset)
        .filter(Asset.video_id == video.id, Asset.asset_type == AssetType.CAPTIONS)
        .one()
    )
    assert captions_asset.path.startswith("https://fake.supabase.co/")

    thumbnails = db_session.query(Thumbnail).filter(Thumbnail.video_id == video.id).all()
    assert len(thumbnails) == 3
    assert all(t.image_path.startswith("https://fake.supabase.co/") for t in thumbnails)
    thumbnail_assets = (
        db_session.query(Asset)
        .filter(Asset.video_id == video.id, Asset.asset_type == AssetType.THUMBNAIL)
        .all()
    )
    assert len(thumbnail_assets) == 3
    assert all(a.path.startswith("https://fake.supabase.co/") for a in thumbnail_assets)


def test_completed_stage_is_a_terminal_no_op(db_session, monkeypatch):
    video, ctx, _fake_voice, _fake_video = _advance_to_captions(db_session, monkeypatch)

    from services.rendering.ffmpeg import assembler

    monkeypatch.setattr(assembler, "burn_in_captions", lambda *a, **k: None)
    monkeypatch.setattr(assembler, "extract_frame", lambda *a, **k: None)

    advance_one_stage(video, db_session, ctx, run_research=True)  # CAPTIONS -> THUMBNAIL
    advance_one_stage(video, db_session, ctx, run_research=True)  # THUMBNAIL -> COMPLETED
    assert video.stage.value == "completed"

    detail_before = video.stage_detail
    advance_one_stage(video, db_session, ctx, run_research=True)  # COMPLETED -> COMPLETED (no-op)
    assert video.stage.value == "completed"
    assert video.stage_detail == detail_before


def test_compliance_check_blocks_near_duplicate_title_for_same_owner(db_session):
    user = User(email="dup@local", display_name="Dup", password_hash="test-hash")
    db_session.add(user)
    db_session.flush()
    project = Project(owner_id=user.id, name="p")
    db_session.add(project)
    db_session.flush()

    ctx = PipelineContext(
        research_engine=_FakeResearchEngine(),
        script_engine=_FakeScriptEngine(),
        voice_engine=_FakeVoiceEngine(),
        video_engine=_FakeVideoEngine(),
        storage_root="./storage/local",
    )

    def _advance_to_compliance(video):
        advance_one_stage(video, db_session, ctx, run_research=True)  # TOPIC -> RESEARCH
        advance_one_stage(video, db_session, ctx, run_research=True)  # RESEARCH -> SCRIPT
        advance_one_stage(video, db_session, ctx, run_research=True)  # SCRIPT -> STORYBOARD_REVIEW
        video.storyboard_approved = True
        db_session.flush()
        advance_one_stage(video, db_session, ctx, run_research=True)  # -> COMPLIANCE_CHECK

    video_one = Video(project_id=project.id, topic="topic one", target_duration_seconds=60)
    db_session.add(video_one)
    db_session.flush()
    _advance_to_compliance(video_one)
    advance_one_stage(video_one, db_session, ctx, run_research=True)  # passes: no prior videos
    assert video_one.stage.value == "voice"

    video_two = Video(project_id=project.id, topic="topic two", target_duration_seconds=60)
    db_session.add(video_two)
    db_session.flush()
    _advance_to_compliance(video_two)

    # _FakeScriptEngine always drafts the same title ("Title") — the second
    # video's script is a 100% match against the first, exactly the
    # "reused/repetitious content" pattern this check exists to catch.
    with pytest.raises(PipelineBlocked) as exc_info:
        advance_one_stage(video_two, db_session, ctx, run_research=True)
    assert exc_info.value.stage == "compliance_check"
    assert "similar to a previous video" in video_two.stage_detail

    report = (
        db_session.query(ComplianceReport)
        .filter(ComplianceReport.video_id == video_two.id)
        .one()
    )
    assert report.passed is False
    assert len(report.blockers) == 1
