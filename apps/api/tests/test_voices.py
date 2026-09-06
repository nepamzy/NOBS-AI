def test_list_voices_returns_catalog(client):
    response = client.get("/voices")
    assert response.status_code == 200
    voices = response.json()
    assert len(voices) > 0
    assert {"id", "name", "description"} <= voices[0].keys()
    ids = [v["id"] for v in voices]
    assert len(ids) == len(set(ids))  # every preset id is unique
