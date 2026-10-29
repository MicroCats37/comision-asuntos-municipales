"""
Canonical authentication fixtures shared by every backend test module.

Source of truth for the JWT test pattern used across the suite:

    token = AccessToken.for_user(user)
    headers = {"Authorization": f"Bearer {token}"}

The fixtures live here (and not directly in a ``conftest.py``) per
``contract/TEST_ARCHITECTURE_CONTRACT.md`` §3.1/§5: the root
``backend/conftest.py`` imports them so every module can rely on them.

Resolution note: ``auth_client`` depends on ``create_user``. A test module may
still declare its own ``create_user`` fixture (with module-specific data);
pytest resolves the closest definition, so the shared ``auth_client`` picks it
up automatically. That is why the JWT logic is centralised here instead of
being duplicated per test file.
"""

import pytest


@pytest.fixture
def api_client(db):
    """Ninja TestClient — anonymous (no ``Authorization`` header).

    Use it for the login/token public surface and for explicit 401 boundary
    assertions. Business endpoints must be exercised with ``auth_client``.
    """
    from ninja.testing import TestClient

    from config.api import api

    return TestClient(api)


@pytest.fixture
def create_user(db):
    """Create the default test user backing the shared auth fixtures."""
    from django.contrib.auth import get_user_model

    User = get_user_model()
    return User.objects.create_user(
        username="testuser_cam",
        email="test_cam@example.com",
        password="testpass123",
        dni="10000001",
    )


@pytest.fixture
def auth_token(create_user):
    """Raw JWT access token for ``create_user``."""
    from ninja_jwt.tokens import AccessToken

    return AccessToken.for_user(create_user)


@pytest.fixture
def auth_headers(create_user):
    """``Authorization`` header for Django test clients (``Client``/``AsyncClient``).

    Django's test clients do not go through ``ninja.testing.TestClient``, so the
    bearer token has to be injected explicitly.
    """
    from ninja_jwt.tokens import AccessToken

    token = AccessToken.for_user(create_user)
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def auth_client(api_client, create_user):
    """Ninja TestClient authenticated with a JWT access token."""
    from ninja_jwt.tokens import AccessToken

    token = AccessToken.for_user(create_user)
    api_client.headers.update({"Authorization": f"Bearer {token}"})
    api_client.user = create_user
    return api_client


@pytest.fixture
def usuario_admin(db, create_user):
    """Alias of ``create_user`` kept for naming compatibility."""
    return create_user
