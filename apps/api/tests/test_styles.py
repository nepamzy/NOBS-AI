def test_list_styles_returns_catalog(client):
    response = client.get("/styles")
    assert response.status_code == 200
    styles = response.json()
    assert len(styles) > 0
    assert {"id", "name", "description", "accent_hex"} <= styles[0].keys()
    ids = [s["id"] for s in styles]
    assert len(ids) == len(set(ids))  # every preset id is unique
