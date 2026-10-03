from services.video.factory import get_video_engine
from services.video.local_wan.adapter import LocalWanEngine
from services.video.wan.adapter import WanEngine


def test_defaults_to_runpod_wan():
    engine = get_video_engine("wan_runpod", "key", "endpoint", "")
    assert isinstance(engine, WanEngine)


def test_wan_local_returns_local_engine():
    engine = get_video_engine("wan_local", "key", "endpoint", "http://localhost:8765")
    assert isinstance(engine, LocalWanEngine)


def test_unknown_provider_falls_back_to_runpod_wan():
    engine = get_video_engine("something_else", "key", "endpoint", "")
    assert isinstance(engine, WanEngine)
