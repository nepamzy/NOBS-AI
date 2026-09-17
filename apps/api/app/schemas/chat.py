from pydantic import BaseModel


class ChatMessage(BaseModel):
    role: str  # "user" or "assistant" — echoes the Anthropic Messages API shape
    content: object  # str for plain turns, or a list of content blocks (tool use/result)


class ChatAttachment(BaseModel):
    media_type: str  # e.g. "image/png", "image/jpeg", "application/pdf"
    data: str  # base64-encoded file bytes, no data: URL prefix
    filename: str = ""


class ChatRequest(BaseModel):
    message: str
    history: list[ChatMessage] = []
    attachment: ChatAttachment | None = None


class ChatResponse(BaseModel):
    reply: str
    history: list[ChatMessage]
