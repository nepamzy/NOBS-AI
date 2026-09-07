from datetime import UTC, datetime, timedelta

from app.auth.security import hash_lookup_value
from app.models.auth import SignupPin


def _make_pin(db_session, client, code="123456", expires_in=timedelta(minutes=5), used=False):
    pin = SignupPin(
        code_hash=hash_lookup_value(code),
        expires_at=datetime.now(UTC) + expires_in,
        used=used,
        created_by_user_id=client.admin_user.id,
    )
    db_session.add(pin)
    db_session.flush()
    return pin


def test_signup_with_valid_pin_creates_user_and_returns_token(client, db_session):
    _make_pin(db_session, client, code="111111")

    response = client.post(
        "/auth/signup",
        json={
            "pin_code": "111111",
            "email": "guest@example.com",
            "password": "correct horse battery staple",
            "display_name": "Guest",
        },
    )
    assert response.status_code == 201
    body = response.json()
    assert body["user"]["role"] == "user"
    assert body["user"]["token_balance"] == 0
    assert "token" in body


def test_signup_marks_pin_used_so_it_cannot_be_reused(client, db_session):
    _make_pin(db_session, client, code="222222")
    payload = {
        "pin_code": "222222",
        "email": "first@example.com",
        "password": "password one",
        "display_name": "First",
    }
    assert client.post("/auth/signup", json=payload).status_code == 201

    payload["email"] = "second@example.com"
    response = client.post("/auth/signup", json=payload)
    assert response.status_code == 400
    assert "invalid" in response.json()["detail"].lower()


def test_signup_rejects_expired_pin(client, db_session):
    _make_pin(db_session, client, code="333333", expires_in=timedelta(minutes=-1))

    response = client.post(
        "/auth/signup",
        json={
            "pin_code": "333333",
            "email": "late@example.com",
            "password": "password",
            "display_name": "Late",
        },
    )
    assert response.status_code == 400


def test_signup_rejects_wrong_pin(client, db_session):
    _make_pin(db_session, client, code="444444")

    response = client.post(
        "/auth/signup",
        json={
            "pin_code": "000000",
            "email": "wrong@example.com",
            "password": "password",
            "display_name": "Wrong",
        },
    )
    assert response.status_code == 400


def test_login_with_correct_credentials_returns_token(client, db_session):
    _make_pin(db_session, client, code="555555")
    client.post(
        "/auth/signup",
        json={
            "pin_code": "555555",
            "email": "login@example.com",
            "password": "correct password",
            "display_name": "Login Test",
        },
    )

    response = client.post(
        "/auth/login", json={"email": "login@example.com", "password": "correct password"}
    )
    assert response.status_code == 200
    assert "token" in response.json()


def test_login_with_wrong_password_rejected(client, db_session):
    _make_pin(db_session, client, code="666666")
    client.post(
        "/auth/signup",
        json={
            "pin_code": "666666",
            "email": "wrongpw@example.com",
            "password": "correct password",
            "display_name": "T",
        },
    )

    response = client.post(
        "/auth/login", json={"email": "wrongpw@example.com", "password": "wrong password"}
    )
    assert response.status_code == 401


def test_suspended_user_cannot_login_or_use_existing_session(client, db_session):
    from app.models.user import User

    _make_pin(db_session, client, code="777777")
    signup = client.post(
        "/auth/signup",
        json={
            "pin_code": "777777",
            "email": "suspend@example.com",
            "password": "password",
            "display_name": "T",
        },
    ).json()
    token = signup["token"]
    user_id = signup["user"]["id"]

    # suspend takes effect immediately, even for a session issued before it
    user = db_session.get(User, user_id)
    user.is_suspended = True
    db_session.flush()

    response = client.get("/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 403

    response = client.post(
        "/auth/login", json={"email": "suspend@example.com", "password": "password"}
    )
    assert response.status_code == 403


def test_logout_invalidates_the_session(client, db_session):
    _make_pin(db_session, client, code="888888")
    signup = client.post(
        "/auth/signup",
        json={
            "pin_code": "888888",
            "email": "logout@example.com",
            "password": "password",
            "display_name": "T",
        },
    ).json()
    token = signup["token"]
    headers = {"Authorization": f"Bearer {token}"}

    assert client.get("/auth/me", headers=headers).status_code == 200
    assert client.post("/auth/logout", headers=headers).status_code == 204
    assert client.get("/auth/me", headers=headers).status_code == 401


def test_unauthenticated_request_rejected(client):
    response = client.get("/auth/me", headers={"Authorization": ""})
    assert response.status_code == 401


def _signup(client, db_session, code, email, password):
    _make_pin(db_session, client, code=code)
    signup = client.post(
        "/auth/signup",
        json={"pin_code": code, "email": email, "password": password, "display_name": "T"},
    ).json()
    return signup["token"]


def test_change_password_with_correct_current_password_succeeds(client, db_session):
    token = _signup(client, db_session, "999001", "pw1@example.com", "original password")
    headers = {"Authorization": f"Bearer {token}"}

    response = client.put(
        "/auth/password",
        json={"current_password": "original password", "new_password": "new password 123"},
        headers=headers,
    )
    assert response.status_code == 200

    # old password no longer works, new one does
    assert (
        client.post(
            "/auth/login", json={"email": "pw1@example.com", "password": "original password"}
        ).status_code
        == 401
    )
    assert (
        client.post(
            "/auth/login", json={"email": "pw1@example.com", "password": "new password 123"}
        ).status_code
        == 200
    )


def test_change_password_with_wrong_current_password_rejected(client, db_session):
    token = _signup(client, db_session, "999002", "pw2@example.com", "original password")
    headers = {"Authorization": f"Bearer {token}"}

    response = client.put(
        "/auth/password",
        json={"current_password": "wrong password", "new_password": "new password 123"},
        headers=headers,
    )
    assert response.status_code == 401

    # original password still works — nothing changed
    assert (
        client.post(
            "/auth/login", json={"email": "pw2@example.com", "password": "original password"}
        ).status_code
        == 200
    )


def test_change_password_rejects_a_too_short_new_password(client, db_session):
    token = _signup(client, db_session, "999003", "pw3@example.com", "original password")
    headers = {"Authorization": f"Bearer {token}"}

    response = client.put(
        "/auth/password",
        json={"current_password": "original password", "new_password": "short"},
        headers=headers,
    )
    assert response.status_code == 422


def test_change_password_signs_out_other_sessions_but_keeps_the_current_one(client, db_session):
    token = _signup(client, db_session, "999004", "pw4@example.com", "original password")
    headers = {"Authorization": f"Bearer {token}"}

    # a second session for the same account (e.g. logged in on another device)
    other_login = client.post(
        "/auth/login", json={"email": "pw4@example.com", "password": "original password"}
    ).json()
    other_headers = {"Authorization": f"Bearer {other_login['token']}"}
    assert client.get("/auth/me", headers=other_headers).status_code == 200

    response = client.put(
        "/auth/password",
        json={"current_password": "original password", "new_password": "new password 123"},
        headers=headers,
    )
    assert response.status_code == 200

    # the session that made the change stays valid...
    assert client.get("/auth/me", headers=headers).status_code == 200
    # ...but the other one is signed out
    assert client.get("/auth/me", headers=other_headers).status_code == 401
