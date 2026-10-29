import pytest
from ninja_jwt.authentication import JWTAuth

from config.api import api


PUBLIC_OPERATIONS = {
    ("POST", "/auth/login/dni"),
    ("POST", "/auth/login/email"),
    ("POST", "/auth/login/username"),
    ("POST", "/token/blacklist"),
    ("POST", "/token/refresh"),
    ("POST", "/token/verify"),
}


def _operations():
    for prefix, router in api._routers:
        for path, path_operation in router.path_operations.items():
            for operation in path_operation.operations:
                full_path = f"{prefix}{path}"
                for method in operation.methods:
                    yield method, full_path, operation


def test_public_api_surface_matches_exact_allowlist():
    actual = {
        (method, path)
        for method, path, operation in _operations()
        if not operation.auth_callbacks
    }

    assert actual == PUBLIC_OPERATIONS


def test_every_protected_operation_uses_jwt_auth():
    for method, path, operation in _operations():
        if (method, path) in PUBLIC_OPERATIONS:
            continue

        assert any(isinstance(auth, JWTAuth) for auth in operation.auth_callbacks), (
            f"{method} {path} does not use JWTAuth"
        )


@pytest.mark.django_db
def test_token_pair_requires_an_access_token(api_client):
    response = api_client.post(
        "/token/pair",
        json={"username": "testuser_cam", "password": "testpass123"},
    )

    assert response.status_code == 401


@pytest.mark.django_db
def test_authenticated_user_can_request_token_pair(auth_client):
    response = auth_client.post(
        "/token/pair",
        json={"username": "testuser_cam", "password": "testpass123"},
    )

    assert response.status_code == 200
    assert response.json()["access"]
    assert response.json()["refresh"]


@pytest.mark.django_db
@pytest.mark.parametrize("path", ["/api/docs", "/api/openapi.json"])
def test_docs_and_schema_require_jwt(client, path):
    response = client.get(path)

    assert response.status_code == 401


@pytest.mark.django_db
@pytest.mark.parametrize("path", ["/api/docs", "/api/openapi.json"])
def test_authenticated_user_can_access_docs_and_schema(client, auth_token, path):
    response = client.get(path, HTTP_AUTHORIZATION=f"Bearer {auth_token}")

    assert response.status_code == 200
