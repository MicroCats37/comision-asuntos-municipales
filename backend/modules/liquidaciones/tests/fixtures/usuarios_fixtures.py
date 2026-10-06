"""
Usuarios fixtures — auth client, user creation.

Re-exports: api_client, create_user, auth_client, usuario_admin
"""
import pytest
from ninja.testing import TestClient
from ninja_jwt.tokens import AccessToken
from config.api import api
from django.contrib.auth import get_user_model


@pytest.fixture
def api_client(db):
    """Ninja TestClient for testing Ninja endpoints with proper async handling."""
    return TestClient(api)


@pytest.fixture
def create_user(db):
    """Create a test user (needed for FK to usuarios_usuario on LiquidacionGeneral)."""
    User = get_user_model()
    return User.objects.create_user(
        username="testuser_edif",
        email="test_edif@example.com",
        password="testpass123",
        dni="12345678",
    )


@pytest.fixture
def auth_client(api_client, create_user):
    """Authenticate the test client using JWT token."""
    user = create_user
    token = AccessToken.for_user(user)
    api_client.headers.update({"Authorization": f"Bearer {token}"})
    api_client.user = user
    return api_client


@pytest.fixture
def usuario_admin(db, create_user):
    """Alias for create_user to match naming convention used in some tests."""
    return create_user
