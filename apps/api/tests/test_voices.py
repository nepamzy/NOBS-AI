def test_list_voices_returns_catalog(client):
    response = client.get("/voices")
    assert response.status_code == 200
    voices = response.json()
    assert len(voices) == 5
    assert {"id", "name", "description", "preview_path"} <= voices[0].keys()
    ids = [v["id"] for v in voices]
    assert len(ids) == len(set(ids))  # every preset id is unique
    assert all(v["preview_path"] for v in voices)  # every preset has a real preview clip
