from pydantic import BaseModel


class ChatMessage(BaseModel):
    role: str  # "user" or "assistant" — echoes the Anthropic Messages API shape
    content: object  # str for plain turns, or a list of content blocks (tool use/result)


class ChatRequest(BaseModel):
    message: str
    history: list[ChatMessage] = []


class ChatResponse(BaseModel):
    reply: str
    history: list[ChatMessage]
