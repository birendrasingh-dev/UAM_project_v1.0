import pytest
from app.db.models import Project, Dataset, ProjectDataset


def test_dataset_project_join_lookup(db):
    """
    Regression test: verify that the Dataset-to-project lookup used by runs.py
    works via the ProjectDataset association table, not Dataset.project_id
    (which doesn't exist on the Dataset model).
    """
    from app.db.models import User
    from app.utils.auth import get_password_hash

    # Create a user directly in the test db
    user = User(
        name="Lookup User",
        email="lookup@example.com",
        password_hash=get_password_hash("password123"),
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    # Create a project
    project = Project(id="proj-1", user_id=user.id, name="Lookup Project")
    db.add(project)

    # Create a dataset
    dataset = Dataset(
        id="ds-1",
        user_id=user.id,
        filename="test.csv",
        storage_key="datasets/test.csv",
    )
    db.add(dataset)
    db.commit()

    # Link dataset to project via ProjectDataset association table
    link = ProjectDataset(project_id="proj-1", dataset_id="ds-1")
    db.add(link)
    db.commit()

    # This is the exact query pattern used in runs.py after the fix
    from sqlalchemy.orm import joinedload
    found = (
        db.query(Dataset)
        .join(ProjectDataset, Dataset.id == ProjectDataset.dataset_id)
        .filter(
            Dataset.id == "ds-1",
            ProjectDataset.project_id == "proj-1",
        )
        .first()
    )
    assert found is not None
    assert found.id == "ds-1"

    # Verify the OLD (buggy) query would fail — Dataset has no project_id attribute
    assert not hasattr(Dataset, "project_id"), "Dataset should not have project_id column"


def test_delete_user_string_uuid(client):
    """
    Regression test: delete_user previously declared user_id: int but User.id is a
    String UUID, so it could never match a real user. Now accepts string UUID.
    """
    # Register user A and get token
    reg_resp = client.post("/api/auth/register", json={
        "name": "User A",
        "email": "delete_usera@example.com",
        "password": "password123"
    })
    assert reg_resp.status_code == 200
    token_a = reg_resp.json()["access_token"]
    headers_a = {"Authorization": f"Bearer {token_a}"}

    # Get user A's id
    me_resp = client.get("/api/auth/me", headers=headers_a)
    assert me_resp.status_code == 200
    user_a_id = me_resp.json()["id"]

    # Register user B
    reg_resp_b = client.post("/api/auth/register", json={
        "name": "User B",
        "email": "delete_userb@example.com",
        "password": "password123"
    })
    assert reg_resp_b.status_code == 200
    token_b = reg_resp_b.json()["access_token"]
    headers_b = {"Authorization": f"Bearer {token_b}"}

    # User A deletes their own account (string UUID)
    del_resp = client.delete(f"/api/auth/users/{user_a_id}", headers=headers_a)
    assert del_resp.status_code == 204, f"Self-delete failed: {del_resp.text}"

    # User B tries to delete user A (who no longer exists) -> 403 (not authorized since B is not admin)
    del_resp_b = client.delete(f"/api/auth/users/{user_a_id}", headers=headers_b)
    assert del_resp_b.status_code == 403

    # User B tries to delete themselves with string id
    me_resp_b = client.get("/api/auth/me", headers=headers_b)
    user_b_id = me_resp_b.json()["id"]
    del_resp_b2 = client.delete(f"/api/auth/users/{user_b_id}", headers=headers_b)
    assert del_resp_b2.status_code == 204


def test_error_handlers_do_not_leak_internals(client):
    """
    Security test: error handlers should not leak raw exception messages,
    schema internals, or stack traces to clients.
    """
    # Trigger a database integrity error by registering with duplicate email
    client.post("/api/auth/register", json={
        "name": "Dup User",
        "email": "leak_check@example.com",
        "password": "password123"
    })
    resp = client.post("/api/auth/register", json={
        "name": "Dup User 2",
        "email": "leak_check@example.com",
        "password": "password123"
    })
    assert resp.status_code == 400
    body = resp.json()
    # Should not contain raw SQL or stack trace internals
    assert "message" not in body or "sqlalchemy" not in str(body.get("message", "")).lower()
    assert "detail" in body


def test_security_headers_present(client):
    """
    Security test: responses should include security headers (X-Content-Type-Options,
    X-Frame-Options, etc.)
    """
    resp = client.get("/api/")
    assert resp.status_code == 200
    headers = resp.headers
    assert headers.get("x-content-type-options") == "nosniff"
    assert headers.get("x-frame-options") == "DENY"
    assert headers.get("referrer-policy") == "strict-origin-when-cross-origin"


def test_cors_preflight(client):
    """
    Security test: CORS preflight should respond with allowed methods/headers
    restricted to a safe set (not wildcard allow_headers).
    """
    resp = client.options("/api/auth/register", headers={
        "origin": "http://localhost:5173",
        "access-control-request-method": "POST",
        "access-control-request-headers": "Authorization, Content-Type",
    })
    assert resp.status_code in (200, 204)
    allow_headers = resp.headers.get("access-control-allow-headers", "")
    # Should NOT be wildcard "*"
    assert "*" not in allow_headers.lower().split(",") or len(allow_headers.split(",")) > 1


def test_health_endpoint_structure(client):
    """
    Health endpoint should return proper structure with status/database/redis keys.
    """
    resp = client.get("/api/health")
    assert resp.status_code in (200, 503)
    data = resp.json()
    assert "status" in data
    assert "database" in data
    assert "redis" in data