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
