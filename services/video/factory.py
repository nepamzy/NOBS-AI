from services.video.engine import VideoEngine
from services.video.local_wan.adapter import LocalWanEngine
from services.video.wan.adapter import WanEngine


def get_video_engine(
    video_provider: str,
    runpod_api_key: str,
    wan_endpoint_id: str,
    local_wan_api_url: str,
) -> VideoEngine:
    if video_provider == "wan_local":
        return LocalWanEngine(local_wan_api_url)
    return WanEngine(runpod_api_key, wan_endpoint_id)
