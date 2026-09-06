import enum


class PipelineStage(str, enum.Enum):
    """Where a video currently sits in Topic → ... → Final MP4 (CLAUDE.md Part 3)."""

    TOPIC = "topic"
    RESEARCH = "research"
    SCRIPT = "script"
    STORYBOARD_REVIEW = "storyboard_review"
    COMPLIANCE_CHECK = "compliance_check"
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


class UserRole(str, enum.Enum):
    """ADMIN is Nobert (the only role that can generate signup PINs, and see
    every user's account for moderation). USER is anyone who signed up with
    a PIN Nobert issued them — fully separate, private data from ADMIN's own
    projects/videos; ADMIN's oversight is account-level (suspend/delete),
    not access to their creative content."""

    ADMIN = "admin"
    USER = "user"


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
