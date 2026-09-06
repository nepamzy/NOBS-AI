def test_spend_empty_by_default(client):
    response = client.get("/spend")
    assert response.status_code == 200
    body = response.json()
    assert body["entries"] == []
    assert body["total_estimated_usd"] == 0
    assert body["total_actual_usd"] == 0


def test_create_spend_entry_and_totals(client):
    response = client.post(
        "/spend",
        json={
            "category": "gpu",
            "service": "Runpod",
            "purpose": "Manual test render",
            "estimated_cost_usd": 2.5,
            "actual_cost_usd": 2.1,
        },
    )
    assert response.status_code == 201
    assert response.json()["category"] == "gpu"

    response = client.get("/spend")
    body = response.json()
    assert len(body["entries"]) == 1
    assert body["total_estimated_usd"] == 2.5
    assert body["total_actual_usd"] == 2.1


def test_create_spend_entry_without_costs_defaults_to_zero_totals(client):
    response = client.post(
        "/spend",
        json={"category": "other", "service": "Domain registrar", "purpose": "renewal check"},
    )
    assert response.status_code == 201
    assert response.json()["estimated_cost_usd"] is None

    response = client.get("/spend")
    assert response.json()["total_estimated_usd"] == 0
