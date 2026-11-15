"""What a Claude session needs to produce a video NOBS AI has approved: the
script as scenes, the chosen voice and style, and a suggested YouTube
title/description. Read-only; the finished video comes back through
nobs_complete_claude_job (app/connector/mcp.py)."""

from sqlalchemy.orm import Session

from app.models.script import Script
from app.models.video import Video
from services.video.style_catalog import STYLE_PRESETS_BY_ID
from services.voice.catalog import VOICE_PRESETS_BY_ID


def build_brief(db: Session, video: Video) -> dict:
    script = db.query(Script).filter(Script.video_id == video.id).one_or_none()
    if script is None:
        return {"error": "This video has no script yet."}

    voice = VOICE_PRESETS_BY_ID.get(video.voice_preset)
    style = STYLE_PRESETS_BY_ID.get(video.style_preset)
    return {
        "video_id": str(video.id),
        "title": script.title,
        "topic": video.topic,
        "hook": script.hook,
        "target_duration_seconds": video.target_duration_seconds,
        "voice": (
            {"id": voice.id, "name": voice.name, "description": voice.description}
            if voice
            else {"id": video.voice_preset or None}
        ),
        "style": (
            {"id": style.id, "name": style.name, "description": style.description}
            if style
            else {"id": video.style_preset or None}
        ),
        "scenes": [
            {
                "order": s.order,
                "narration": s.narration,
                "visual_prompt": s.visual_prompt,
                "duration_seconds": s.duration_seconds,
                "transition": s.transition.value,
            }
            for s in script.scenes
        ],
        "youtube": {"suggested_title": script.title, "suggested_description": script.hook},
        "deliver": (
            "When the video is made, call nobs_complete_claude_job with this video_id and a "
            "public https link to the MP4 (or send the file with the command from "
            "nobs_upload_instructions, adding the form field video_id). Optional: "
            "voiceover_url, captions_url, thumbnail_url."
        ),
    }
