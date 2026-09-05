import pytest
from app.models.enums import PipelineStage
from app.models.project import Project
from app.models.research import Research
from app.models.script import Script
from app.models.user import User
from app.models.video import Video

from services.ai.orchestration.pipeline import PipelineBlocked, PipelineContext, advance_one_stage
from services.ai.research.engine import ResearchEngine, ResearchResult
from services.ai.script.engine import SceneDraft, ScriptDraft, ScriptEngine
from services.video.wan.adapter import WanEngine
from services.voice.chatterbox.adapter import ChatterboxEngine


def _make_video(db_session, topic="topic", duration=60) -> Video:
    user = User(email="nobert@local", display_name="Nobert")
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
    advance_one_stage(video, db_session, ctx, run_research=True)  # STORYBOARD_REVIEW -> VOICE
    assert video.stage.value == "voice"
    assert video.stage_detail == ""  # cleared, not left over from storyboard_review

    # advance_one_stage moves one stage per call, so the next call attempts
    # "voice" and blocks — stage_detail must reflect *that* block, not the
    # stale "Awaiting storyboard approval" message from the previous stage.
    with pytest.raises(PipelineBlocked) as exc_info:
        advance_one_stage(video, db_session, ctx, run_research=True)
    assert exc_info.value.stage == "voice"
    assert video.stage_detail != "Awaiting storyboard approval"
    assert "voice synthesis" in video.stage_detail.lower()
