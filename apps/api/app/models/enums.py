import enum


class PipelineStage(str, enum.Enum):
    """Where a video currently sits in Topic → ... → Final MP4 (CLAUDE.md Part 3)."""

    TOPIC = "topic"
    RESEARCH = "research"
    SCRIPT = "script"
    STORYBOARD_REVIEW = "storyboard_review"
    VOICE = "voice"
    VIDEO_GENERATION = "video_generation"
    ASSEMBLY = "assembly"
    CAPTIONS = "captions"
    THUMBNAIL = "thumbnail"
    COMPLETED = "completed"
    FAILED = "failed"


class JobStatus(str, enum.Enum):
    QUEUED = "queued"
    RUNNING = "running"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    CANCELLED = "cancelled"


class AssetType(str, enum.Enum):
    SCRIPT = "script"
    VOICEOVER = "voiceover"
    SCENE_CLIP = "scene_clip"
    THUMBNAIL = "thumbnail"
    CAPTIONS = "captions"
    FINAL_VIDEO = "final_video"


class TransitionType(str, enum.Enum):
    CUT = "cut"
    FADE = "fade"
    DISSOLVE = "dissolve"


class CostCategory(str, enum.Enum):
    """Matches CLAUDE.md Part 4's spend-tracking categories exactly."""

    GPU = "gpu"
    LLM = "llm"
    TTS = "tts"
    VIDEO_GENERATION = "video_generation"
    STORAGE = "storage"
    DATABASE = "database"
    HOSTING = "hosting"
    NETWORKING = "networking"
    DOMAIN = "domain"
    OTHER = "other"
