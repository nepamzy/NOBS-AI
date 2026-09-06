def test_get_settings_returns_defaults(client):
    response = client.get("/settings")
    assert response.status_code == 200
    assert response.json() == {
        "default_duration_minutes": 3,
        "default_voice_preset": "",
        "default_style_preset": "",
        "weekly_goal": 3,
    }


def test_update_settings_persists_partial_change(client):
    response = client.put("/settings", json={"weekly_goal": 5, "default_voice_preset": "calm"})
    assert response.status_code == 200
    body = response.json()
    assert body["weekly_goal"] == 5
    assert body["default_voice_preset"] == "calm"
    assert body["default_duration_minutes"] == 3  # untouched field keeps its default

    # A second GET reflects the same persisted values, not a fresh default.
    response = client.get("/settings")
    assert response.json()["weekly_goal"] == 5
    assert response.json()["default_voice_preset"] == "calm"
