"""
Unit tests for auth HTTP schemas — validates request/response schemas.
"""
import pytest
from pydantic_core import ValidationError

from modules.usuarios.presentation.schemas.auth_schemas import (
    LoginUsernameIn,
    LoginDniIn,
    LoginEmailIn,
)


class TestLoginUsernameIn:
    def test_valid_username_and_password(self):
        schema = LoginUsernameIn(username="admin", password="secret123")
        assert schema.username == "admin"
        assert schema.password == "secret123"

    def test_empty_username_fails(self):
        with pytest.raises(ValidationError):
            LoginUsernameIn(username="", password="secret123")

    def test_empty_password_fails(self):
        with pytest.raises(ValidationError):
            LoginUsernameIn(username="admin", password="")


class TestLoginDniIn:
    def test_valid_dni_and_password(self):
        schema = LoginDniIn(dni="12345678", password="secret123")
        assert schema.dni == "12345678"
        assert schema.password == "secret123"

    def test_dni_too_short_fails(self):
        with pytest.raises(ValidationError):
            LoginDniIn(dni="1234567", password="secret123")

    def test_dni_too_long_fails(self):
        with pytest.raises(ValidationError):
            LoginDniIn(dni="123456789", password="secret123")

    def test_empty_password_fails(self):
        with pytest.raises(ValidationError):
            LoginDniIn(dni="12345678", password="")


class TestLoginEmailIn:
    def test_valid_email_and_password(self):
        schema = LoginEmailIn(email="user@example.com", password="secret123")
        assert schema.email == "user@example.com"
        assert schema.password == "secret123"

    def test_any_string_for_email_succeeds(self):
        """LoginEmailIn accepts any string for email — no format validation."""
        schema = LoginEmailIn(email="not-an-email", password="secret123")
        assert schema.email == "not-an-email"

    def test_empty_password_fails(self):
        with pytest.raises(ValidationError):
            LoginEmailIn(email="user@example.com", password="")
