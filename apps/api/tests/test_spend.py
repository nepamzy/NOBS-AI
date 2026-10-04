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


def test_new_entry_defaults_to_active_status(client):
    response = client.post(
        "/spend",
        json={"category": "hosting", "service": "Vercel", "purpose": "frontend"},
    )
    assert response.json()["status"] == "active"


def test_update_spend_entry_status(client):
    created = client.post(
        "/spend",
        json={
            "category": "gpu",
            "service": "Runpod",
            "purpose": "pod rental",
            "status": "pending",
            "billing_type": "hourly",
        },
    ).json()

    response = client.patch(f"/spend/{created['id']}", json={"status": "active"})
    assert response.status_code == 200
    assert response.json()["status"] == "active"
    assert response.json()["billing_type"] == "hourly"


def test_update_missing_spend_entry_is_404(client):
    response = client.patch(
        "/spend/00000000-0000-0000-0000-000000000000", json={"status": "stopped"}
    )
    assert response.status_code == 404


def test_delete_spend_entry(client):
    created = client.post(
        "/spend",
        json={"category": "other", "service": "Temp thing", "purpose": "test"},
    ).json()

    response = client.delete(f"/spend/{created['id']}")
    assert response.status_code == 204

    assert client.get("/spend").json()["entries"] == []


def test_summary_computes_active_monthly_recurring_and_counts(client):
    client.post(
        "/spend",
        json={
            "category": "hosting",
            "service": "Render Worker",
            "purpose": "job runner",
            "status": "active",
            "billing_type": "monthly",
            "actual_cost_usd": 7.0,
        },
    )
    client.post(
        "/spend",
        json={
            "category": "gpu",
            "service": "Runpod",
            "purpose": "pod rental",
            "status": "pending",
            "billing_type": "hourly",
        },
    )

    body = client.get("/spend").json()
    assert body["active_monthly_recurring_usd"] == 7.0
    assert body["active_count"] == 1
    assert body["pending_count"] == 1
    categories = {b["category"]: b for b in body["by_category"]}
    assert categories["hosting"]["actual_usd"] == 7.0
