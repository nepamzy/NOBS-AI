from tests.test_api import _signup_guest


def test_join_waitlist_creates_signup(client):
    response = client.post(
        "/waitlist", json={"email": "Visitor@Example.com", "name": "Taylor"}
    )
    assert response.status_code == 201
    body = response.json()
    assert body["email"] == "visitor@example.com"  # normalized lowercase
    assert body["name"] == "Taylor"


def test_join_waitlist_is_idempotent_for_the_same_email(client):
    first = client.post("/waitlist", json={"email": "repeat@example.com", "name": "A"})
    second = client.post("/waitlist", json={"email": "REPEAT@example.com", "name": "B"})

    assert first.status_code == 201
    assert second.status_code == 201
    assert first.json()["id"] == second.json()["id"]  # same row, not a duplicate


def test_join_waitlist_rejects_malformed_email(client):
    response = client.post("/waitlist", json={"email": "not-an-email"})
    assert response.status_code == 422


def test_join_waitlist_name_is_optional(client):
    response = client.post("/waitlist", json={"email": "noname@example.com"})
    assert response.status_code == 201
    assert response.json()["name"] == ""


def test_list_waitlist_requires_admin(client, db_session):
    _user_id, token = _signup_guest(client, db_session)
    response = client.get("/admin/waitlist", headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 403


def test_list_waitlist_returns_signups_for_admin(client):
    client.post("/waitlist", json={"email": "one@example.com"})
    client.post("/waitlist", json={"email": "two@example.com"})

    response = client.get("/admin/waitlist")
    assert response.status_code == 200
    emails = {row["email"] for row in response.json()}
    assert emails == {"one@example.com", "two@example.com"}
