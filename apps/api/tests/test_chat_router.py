class _FakeBlock:
    def __init__(self, type_, **fields):
        self.type = type_
        self._fields = fields
        for key, value in fields.items():
            setattr(self, key, value)

    def model_dump(self):
        return {"type": self.type, **self._fields}


class _FakeResponse:
    def __init__(self, stop_reason, content):
        self.stop_reason = stop_reason
        self.content = content


def test_returns_402_when_llm_not_configured(client):
    response = client.post("/chat/messages", json={"message": "hello", "history": []})
    assert response.status_code == 402


def test_chat_can_list_projects_via_tool_use(client, monkeypatch):
    from app.config import settings

    monkeypatch.setattr(settings, "llm_provider", "anthropic")
    monkeypatch.setattr(settings, "llm_api_key", "key123")

    project_response = client.post("/projects", json={"name": "My Project"})
    assert project_response.status_code == 201

    responses = [
        _FakeResponse(
            "tool_use", [_FakeBlock("tool_use", id="t1", name="list_projects", input={})]
        ),
        _FakeResponse("end_turn", [_FakeBlock("text", text="You have 1 project: My Project.")]),
    ]

    class _FakeMessages:
        def create(self, **kwargs):
            return responses.pop(0)

    class _FakeClient:
        def __init__(self, api_key):
            self.messages = _FakeMessages()

    import anthropic

    monkeypatch.setattr(anthropic, "Anthropic", _FakeClient)

    response = client.post(
        "/chat/messages", json={"message": "what projects do I have?", "history": []}
    )
    assert response.status_code == 200
    body = response.json()
    assert body["reply"] == "You have 1 project: My Project."
    assert any("My Project" in str(m["content"]) for m in body["history"])


def test_admin_gets_web_search_tool_and_broadened_prompt(client, monkeypatch):
    from app.config import settings

    import services.ai.assistant.engine as engine_module

    monkeypatch.setattr(settings, "llm_provider", "anthropic")
    monkeypatch.setattr(settings, "llm_api_key", "key123")

    captured = {}

    def fake_run_chat_turn(*args, **kwargs):
        captured.update(kwargs)
        return engine_module.ChatTurnResult(reply="ok", messages=[])

    import app.routers.chat as chat_router

    monkeypatch.setattr(chat_router, "run_chat_turn", fake_run_chat_turn)

    response = client.post("/chat/messages", json={"message": "hi", "history": []})
    assert response.status_code == 200
    assert engine_module.WEB_SEARCH_TOOL in captured["tools"]
    assert "Nobert, the product's admin" in captured["system_prompt"]


def test_guest_does_not_get_web_search_tool_or_broadened_prompt(client, db_session, monkeypatch):
    from app.config import settings
    from app.models.enums import UserRole

    monkeypatch.setattr(settings, "llm_provider", "anthropic")
    monkeypatch.setattr(settings, "llm_api_key", "key123")

    client.admin_user.role = UserRole.USER
    db_session.flush()

    import app.routers.chat as chat_router

    import services.ai.assistant.engine as engine_module

    captured = {}

    def fake_run_chat_turn(*args, **kwargs):
        captured.update(kwargs)
        return engine_module.ChatTurnResult(reply="ok", messages=[])

    monkeypatch.setattr(chat_router, "run_chat_turn", fake_run_chat_turn)

    response = client.post("/chat/messages", json={"message": "hi", "history": []})
    assert response.status_code == 200
    assert engine_module.WEB_SEARCH_TOOL not in captured["tools"]
    assert "Nobert, the product's admin" not in captured["system_prompt"]


def test_image_attachment_is_sent_as_content_block(client, monkeypatch):
    import base64

    import app.routers.chat as chat_router
    from app.config import settings

    import services.ai.assistant.engine as engine_module

    monkeypatch.setattr(settings, "llm_provider", "anthropic")
    monkeypatch.setattr(settings, "llm_api_key", "key123")

    captured = {}

    def fake_run_chat_turn(_provider, _key, _model, conversation, *_args, **kwargs):
        captured["conversation"] = conversation
        return engine_module.ChatTurnResult(reply="ok", messages=[])

    monkeypatch.setattr(chat_router, "run_chat_turn", fake_run_chat_turn)

    image_b64 = base64.b64encode(b"fake png bytes").decode()
    response = client.post(
        "/chat/messages",
        json={
            "message": "what's in this image?",
            "history": [],
            "attachment": {"media_type": "image/png", "data": image_b64, "filename": "x.png"},
        },
    )
    assert response.status_code == 200
    last_message = captured["conversation"][-1]
    assert last_message["role"] == "user"
    blocks = last_message["content"]
    assert blocks[0]["type"] == "image"
    assert blocks[0]["source"]["media_type"] == "image/png"
    assert blocks[0]["source"]["data"] == image_b64
    assert blocks[1] == {"type": "text", "text": "what's in this image?"}


def test_video_attachment_is_rejected(client, monkeypatch):
    from app.config import settings

    monkeypatch.setattr(settings, "llm_provider", "anthropic")
    monkeypatch.setattr(settings, "llm_api_key", "key123")

    response = client.post(
        "/chat/messages",
        json={
            "message": "what's happening in this video?",
            "history": [],
            "attachment": {"media_type": "video/mp4", "data": "AAAA", "filename": "x.mp4"},
        },
    )
    assert response.status_code == 400
    assert "Video isn't supported" in response.json()["detail"]
