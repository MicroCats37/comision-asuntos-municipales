"""
Integration tests for auth login endpoints — tests full login flow with DB.
"""
import pytest
from django.test import Client

from modules.usuarios.tests.factories.usuario_factory import UsuarioFactory


@pytest.mark.django_db
class TestLoginEndpoint:
    """Test login endpoints via HTTP."""

    def setup_method(self):
        """Create a test user before each test."""
        self.user = UsuarioFactory(
            username="12345678",
            dni="12345678",
            password="secret123",
        )

    def test_login_username_returns_tokens(self, client: Client):
        """
        POST /api/auth/login/username should return access_token,
        refresh_token, and user data on valid credentials.
        """
        response = client.post(
            "/api/auth/login/username",
            data={"username": "12345678", "password": "secret123"},
            content_type="application/json",
        )
        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data["data"]
        assert "refresh_token" in data["data"]
        assert "user" in data["data"]

    def test_login_username_invalid_password(self, client: Client):
        """Invalid password should return 401 or error."""
        response = client.post(
            "/api/auth/login/username",
            data={"username": "12345678", "password": "wrongpassword"},
            content_type="application/json",
        )
        # Auth failure returns 401 or error in data
        assert response.status_code in (401, 400)

    def test_login_username_nonexistent_user(self, client: Client):
        """Nonexistent user should return error."""
        response = client.post(
            "/api/auth/login/username",
            data={"username": "00000000", "password": "secret123"},
            content_type="application/json",
        )
        assert response.status_code in (401, 400)

    def test_login_dni_returns_tokens(self, client: Client):
        """
        POST /api/auth/login/dni should return tokens on valid DNI + password.
        """
        response = client.post(
            "/api/auth/login/dni",
            data={"dni": "12345678", "password": "secret123"},
            content_type="application/json",
        )
        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data["data"]
        assert "refresh_token" in data["data"]

    def test_login_email_returns_tokens(self, client: Client):
        """
        POST /api/auth/login/email should return tokens on valid email + password.
        """
        response = client.post(
            "/api/auth/login/email",
            data={"email": "12345678@example.com", "password": "secret123"},
            content_type="application/json",
        )
        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data["data"]
        assert "refresh_token" in data["data"]

    def test_login_dni_invalid_password(self, client: Client):
        """DNI with wrong password should return 401 or error."""
        response = client.post(
            "/api/auth/login/dni",
            data={"dni": "12345678", "password": "wrongpassword"},
            content_type="application/json",
        )
        assert response.status_code in (401, 400)

    def test_login_dni_nonexistent_user(self, client: Client):
        """Nonexistent DNI should return error."""
        response = client.post(
            "/api/auth/login/dni",
            data={"dni": "00000000", "password": "secret123"},
            content_type="application/json",
        )
        assert response.status_code in (401, 400)

    def test_login_email_invalid_password(self, client: Client):
        """Email with wrong password should return 401 or error."""
        response = client.post(
            "/api/auth/login/email",
            data={"email": "12345678@example.com", "password": "wrongpassword"},
            content_type="application/json",
        )
        assert response.status_code in (401, 400)

    def test_login_email_nonexistent_user(self, client: Client):
        """Nonexistent email should return error."""
        response = client.post(
            "/api/auth/login/email",
            data={"email": "nonexistent@example.com", "password": "secret123"},
            content_type="application/json",
        )
        assert response.status_code in (401, 400)
