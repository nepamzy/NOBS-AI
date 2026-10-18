"""A dropped DB connection right after a paid call must not lose the result,
and must never make the paid call a second time.

These use a real, committed session (not the per-test rollback fixture),
because the retry does a real rollback — exactly what production does."""

import pytest
from app.db import Base
from app.models.enums import PipelineStage
from app.models.project import Project
from app.models.research import Research
from app.models.script import Script
from app.models.user import User
from app.models.video import Video
from sqlalchemy import text
from sqlalchemy.exc import OperationalError
from sqlalchemy.orm import Session
from tests.test_pipeline import _unconfigured_context

import services.ai.orchestration.pipeline as pipeline
from services.ai.orchestration.pipeline import advance_one_stage
from services.ai.research.engine import ResearchEngine, ResearchResult
from services.ai.script.engine import SceneDraft, ScriptDraft, ScriptEngine


@pytest.fixture
def committed(db_engine):
    session = Session(bind=db_engine)
    yield session
    session.rollback()
    session.close()
    with db_engine.begin() as conn:
        tables = ", ".join(f'"{t.name}"' for t in Base.metadata.sorted_tables)
        conn.execute(text(f"TRUNCATE {tables} CASCADE"))


@pytest.fixture
def no_sleep(monkeypatch):
    monkeypatch.setattr(pipeline.time, "sleep", lambda seconds: None)


def _committed_video(session, stage) -> Video:
    user = User(email="retry@local", display_name="Retry", password_hash="test-hash")
    session.add(user)
    session.flush()
    project = Project(owner_id=user.id, name="p")
    session.add(project)
    session.flush()
    video = Video(project_id=project.id, topic="topic", target_duration_seconds=60, stage=stage)
    session.add(video)
    session.commit()
    return video


def _drop_commits(monkeypatch, session, drop_on: set[int]):
    """Make the commit() calls numbered in drop_on raise a Supabase-style error."""
    real_commit = session.commit
    state = {"count": 0}

    def commit():
        state["count"] += 1
        if state["count"] in drop_on:
            raise OperationalError(
                "UPDATE videos ...", {}, Exception("SSL error: unexpected eof while reading")
            )
        return real_commit()

    monkeypatch.setattr(session, "commit", commit)


class _CountingResearch(ResearchEngine):
    def __init__(self):
        self.calls = []

    def run(self, topic):
        self.calls.append(topic)
        return ResearchResult(topic=topic, key_facts=["fact one"])


class _CountingScript(ScriptEngine):
    def __init__(self):
        self.calls = 0

    def generate(self, topic, duration, research, lessons):
        self.calls += 1
        return ScriptDraft(
            title="Title",
            hook="Hook",
            estimated_duration_seconds=5,
            word_count=1,
            scenes=[
                SceneDraft(
                    order=1,
                    narration="hello",
                    visual_prompt="a shot",
                    duration_seconds=5,
                    transition="cut",
                )
            ],
        )


def test_research_saved_after_one_dropped_connection_without_repeating_the_call(
    committed, monkeypatch, no_sleep
):
    video = _committed_video(committed, PipelineStage.RESEARCH)
    engine = _CountingResearch()
    ctx = _unconfigured_context()
    ctx.research_engine = engine
    # commit #1 is the release before the LLM call; #2 is the first save attempt.
    _drop_commits(monkeypatch, committed, drop_on={2})

    advance_one_stage(video, committed, ctx, run_research=True)

    assert len(engine.calls) == 1, "the paid research call must run exactly once"
    committed.expire_all()
    assert committed.get(Video, video.id).stage == PipelineStage.SCRIPT
    assert committed.query(Research).filter(Research.video_id == video.id).count() == 1


def test_research_gives_up_clearly_when_saving_keeps_failing(
    committed, monkeypatch, no_sleep
):
    video = _committed_video(committed, PipelineStage.RESEARCH)
    engine = _CountingResearch()
    ctx = _unconfigured_context()
    ctx.research_engine = engine
    _drop_commits(monkeypatch, committed, drop_on={2, 3, 4})

    with pytest.raises(OperationalError):
        advance_one_stage(video, committed, ctx, run_research=True)

    assert len(engine.calls) == 1, "still only one paid call, even when every save fails"
    committed.expire_all()
    assert committed.query(Research).filter(Research.video_id == video.id).count() == 0


def test_script_saved_after_one_dropped_connection(committed, monkeypatch, no_sleep):
    video = _committed_video(committed, PipelineStage.SCRIPT)
    engine = _CountingScript()
    ctx = _unconfigured_context()
    ctx.script_engine = engine
    _drop_commits(monkeypatch, committed, drop_on={2})

    advance_one_stage(video, committed, ctx, run_research=False)

    assert engine.calls == 1
    committed.expire_all()
    assert committed.get(Video, video.id).stage == PipelineStage.STORYBOARD_REVIEW
    assert committed.query(Script).filter(Script.video_id == video.id).count() == 1
