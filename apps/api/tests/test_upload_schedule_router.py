def _create_project(client):
    response = client.post("/projects", json={"name": "Weekly Stories"})
    assert response.status_code == 201
    return response.json()["id"]


def test_create_and_list_schedule(client):
    project_id = _create_project(client)

    response = client.post(
        "/upload-schedules",
        json={
            "project_id": project_id,
            "day_of_week": 0,
            "trigger_time": "16:00",
            "topic": "Storytelling: Hero's Journey",
            "target_duration_seconds": 300,
        },
    )
    assert response.status_code == 201
    body = response.json()
    assert body["day_of_week"] == 0
    assert body["trigger_time"] == "16:00"
    assert body["enabled"] is True

    list_response = client.get("/upload-schedules")
    assert list_response.status_code == 200
    assert len(list_response.json()) == 1


def test_create_rejects_bad_time_format(client):
    project_id = _create_project(client)

    response = client.post(
        "/upload-schedules",
        json={
            "project_id": project_id,
            "day_of_week": 0,
            "trigger_time": "5pm",
            "topic": "x",
            "target_duration_seconds": 300,
        },
    )
    assert response.status_code == 422


def test_create_rejects_other_users_project(client, db_session):
    from app.auth.security import hash_password
    from app.models.enums import UserRole
    from app.models.project import Project
    from app.models.user import User

    other_owner = User(
        email="other@local",
        display_name="Other",
        password_hash=hash_password("x"),
        role=UserRole.USER,
    )
    db_session.add(other_owner)
    db_session.flush()
    other_project = Project(owner_id=other_owner.id, name="Not Nobert's")
    db_session.add(other_project)
    db_session.flush()

    response = client.post(
        "/upload-schedules",
        json={
            "project_id": str(other_project.id),
            "day_of_week": 0,
            "trigger_time": "16:00",
            "topic": "x",
            "target_duration_seconds": 300,
        },
    )
    assert response.status_code == 404


def test_disable_and_delete_schedule(client):
    project_id = _create_project(client)
    create_response = client.post(
        "/upload-schedules",
        json={
            "project_id": project_id,
            "day_of_week": 2,
            "trigger_time": "09:00",
            "topic": "x",
            "target_duration_seconds": 300,
        },
    )
    schedule_id = create_response.json()["id"]

    disable_response = client.patch(
        f"/upload-schedules/{schedule_id}", json={"enabled": False}
    )
    assert disable_response.status_code == 200
    assert disable_response.json()["enabled"] is False

    delete_response = client.delete(f"/upload-schedules/{schedule_id}")
    assert delete_response.status_code == 204
    assert client.get("/upload-schedules").json() == []


def test_activate_auto_publish(client):
    project_id = _create_project(client)
    create_response = client.post(
        "/upload-schedules",
        json={
            "project_id": project_id,
            "day_of_week": 3,
            "trigger_time": "10:00",
            "topic": "x",
            "target_duration_seconds": 300,
        },
    )
    schedule_id = create_response.json()["id"]
    assert create_response.json()["auto_publish"] is False

    response = client.patch(f"/upload-schedules/{schedule_id}", json={"auto_publish": True})
    assert response.status_code == 200
    body = response.json()
    assert body["auto_publish"] is True
    assert body["enabled"] is True  # unspecified field untouched
