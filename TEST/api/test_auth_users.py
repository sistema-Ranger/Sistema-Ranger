# TEST/api/test_auth_users.py
from collections.abc import Callable

from fastapi.testclient import TestClient

from app.models import User, UserRole
from conftest import TEST_PASSWORD


def _login(client: TestClient, email: str, password: str = TEST_PASSWORD):
    return client.post("/api/v1/auth/login", data={"username": email, "password": password})


def test_login_ok_returns_token_and_user(
    client: TestClient, make_user: Callable[..., User]
) -> None:
    user = make_user(UserRole.infra, email="infra@ranger.test")
    res = _login(client, " Infra@Ranger.TEST ")
    assert res.status_code == 200
    body = res.json()
    assert body["token_type"] == "bearer"
    assert body["user"]["email"] == user.email
    assert body["user"]["role"] == "infra"
    me = client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {body['access_token']}"})
    assert me.status_code == 200
    assert me.json()["last_login_at"] is not None


def test_login_wrong_password_401(client: TestClient, make_user: Callable[..., User]) -> None:
    user = make_user()
    res = _login(client, user.email, "incorrecta")
    assert res.status_code == 401
    assert res.json()["code"] == "INVALID_CREDENTIALS"


def test_login_inactive_user_401(client: TestClient, make_user: Callable[..., User], db) -> None:
    user = make_user()
    user.is_active = False
    db.commit()
    assert _login(client, user.email).status_code == 401


def test_me_without_token_401(client: TestClient) -> None:
    res = client.get("/api/v1/auth/me")
    assert res.status_code == 401
    assert res.json() == {"detail": "No autenticado", "code": "UNAUTHORIZED"}


def test_me_invalid_token_401(client: TestClient) -> None:
    res = client.get("/api/v1/auth/me", headers={"Authorization": "Bearer basura"})
    assert res.status_code == 401


def test_users_forbidden_for_non_admin(client: TestClient, auth_headers) -> None:
    for role in (UserRole.infra, UserRole.viewer):
        res = client.get("/api/v1/users", headers=auth_headers(role))
        assert res.status_code == 403
        assert res.json()["code"] == "FORBIDDEN"


def test_users_crud_as_admin(client: TestClient, auth_headers) -> None:
    headers = auth_headers(UserRole.admin)
    payload = {"email": "dev@ranger.test", "full_name": "Dev", "password": "password1"}
    created = client.post("/api/v1/users", json=payload, headers=headers)
    assert created.status_code == 201
    user = created.json()
    assert user["role"] == "viewer"
    assert "password" not in user and "password_hash" not in user

    dup = client.post("/api/v1/users", json=payload, headers=headers)
    assert dup.status_code == 409
    assert dup.json()["code"] == "EMAIL_TAKEN"

    listed = client.get("/api/v1/users", headers=headers).json()
    assert listed["total"] == 2 and listed["page"] == 1

    patched = client.patch(
        f"/api/v1/users/{user['id']}", json={"role": "developer"}, headers=headers
    )
    assert patched.json()["role"] == "developer"

    deleted = client.delete(f"/api/v1/users/{user['id']}", headers=headers)
    assert deleted.status_code == 200 and deleted.json()["is_active"] is False
    assert _login(client, "dev@ranger.test", "password1").status_code == 401


def test_users_validation_422(client: TestClient, auth_headers) -> None:
    headers = auth_headers(UserRole.admin)
    bad = {"email": "no-es-email", "full_name": "X", "password": "corta", "role": "jefe"}
    res = client.post("/api/v1/users", json=bad, headers=headers)
    assert res.status_code == 422
    assert res.json()["code"] == "VALIDATION_ERROR"


def test_admin_cannot_deactivate_self(client: TestClient, make_user, db) -> None:
    from app.security.jwt import create_access_token

    admin = make_user(UserRole.admin)
    headers = {"Authorization": f"Bearer {create_access_token(admin.id, 'admin')}"}
    res = client.delete(f"/api/v1/users/{admin.id}", headers=headers)
    assert res.status_code == 400
    assert res.json()["code"] == "SELF_MODIFICATION"


def test_user_not_found_404(client: TestClient, auth_headers) -> None:
    res = client.patch("/api/v1/users/999", json={"full_name": "X"}, headers=auth_headers())
    assert res.status_code == 404
    assert res.json()["code"] == "USER_NOT_FOUND"
