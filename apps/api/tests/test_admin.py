from datetime import UTC, datetime, timedelta

from app.auth.security import hash_lookup_value
from app.models.auth import SignupPin
from app.models.user import User


def _signup_guest(client, db_session, code="123456", email="guest@example.com"):
    pin = SignupPin(
        code_hash=hash_lookup_value(code),
        expires_at=datetime.now(UTC) + timedelta(minutes=5),
        created_by_user_id=client.admin_user.id,
    )
    db_session.add(pin)
    db_session.flush()
    signup = client.post(
        "/auth/signup",
        json={
            "pin_code": code,
            "email": email,
            "password": "password",
            "display_name": "Guest",
        },
    ).json()
    return signup["user"]["id"], signup["token"]


def _headers_for(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


def test_generate_pin_returns_plaintext_code_once(client):
    response = client.post("/admin/pins")
    assert response.status_code == 201
    body = response.json()
    assert len(body["code"]) == 6
    assert body["code"].isdigit()


def test_generate_pin_expires_in_five_minutes(client):
    before = datetime.now(UTC)
    response = client.post("/admin/pins")
    expires_at = datetime.fromisoformat(response.json()["expires_at"])
    delta = expires_at - before
    assert timedelta(minutes=4, seconds=50) < delta < timedelta(minutes=5, seconds=10)


def test_non_admin_cannot_generate_pins(client, db_session):
    _user_id, token = _signup_guest(client, db_session)
    response = client.post("/admin/pins", headers=_headers_for(token))
    assert response.status_code == 403


def test_admin_can_list_users(client, db_session):
    _signup_guest(client, db_session, code="111111", email="one@example.com")
    _signup_guest(client, db_session, code="222222", email="two@example.com")

    response = client.get("/admin/users")
    assert response.status_code == 200
    emails = {u["email"] for u in response.json()}
    assert emails == {"one@example.com", "two@example.com"}
    # the admin account itself never shows up in the guest-user list
    assert client.admin_user.email not in emails


def test_admin_can_suspend_and_unsuspend_a_user(client, db_session):
    user_id, token = _signup_guest(client, db_session)

    response = client.post(f"/admin/users/{user_id}/suspend")
    assert response.status_code == 200
    assert response.json()["is_suspended"] is True
    assert client.get("/auth/me", headers=_headers_for(token)).status_code == 403

    response = client.post(f"/admin/users/{user_id}/unsuspend")
    assert response.status_code == 200
    assert response.json()["is_suspended"] is False
    assert client.get("/auth/me", headers=_headers_for(token)).status_code == 200


def test_admin_can_delete_a_user(client, db_session):
    user_id, _token = _signup_guest(client, db_session)

    response = client.delete(f"/admin/users/{user_id}")
    assert response.status_code == 204
    assert db_session.get(User, user_id) is None


def test_admin_cannot_suspend_or_delete_the_admin_account(client):
    response = client.post(f"/admin/users/{client.admin_user.id}/suspend")
    assert response.status_code == 404

    response = client.delete(f"/admin/users/{client.admin_user.id}")
    assert response.status_code == 404


def test_admin_can_grant_tokens_to_a_user(client, db_session):
    user_id, token = _signup_guest(client, db_session)

    response = client.post(f"/admin/users/{user_id}/grant-tokens", json={"amount": 5})
    assert response.status_code == 200
    assert response.json()["token_balance"] == 5

    me = client.get("/auth/me", headers=_headers_for(token)).json()
    assert me["token_balance"] == 5


def test_non_admin_cannot_manage_other_users(client, db_session):
    target_id, _target_token = _signup_guest(client, db_session, code="333333", email="a@x.com")
    _attacker_id, attacker_token = _signup_guest(
        client, db_session, code="444444", email="b@x.com"
    )

    response = client.post(
        f"/admin/users/{target_id}/suspend", headers=_headers_for(attacker_token)
    )
    assert response.status_code == 403
