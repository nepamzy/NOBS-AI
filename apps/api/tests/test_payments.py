def test_list_packages_returns_catalog(client):
    response = client.get("/payments/packages")
    assert response.status_code == 200
    packages = response.json()
    assert len(packages) > 0
    assert {"id", "name", "tokens", "price_usd"} <= packages[0].keys()
    ids = [p["id"] for p in packages]
    assert len(ids) == len(set(ids))  # every package id is unique
