from pydantic import BaseModel


class YouTubeUploadRequest(BaseModel):
    title: str
    description: str
    tags: list[str] = []
