"""
Unit tests for create_admin management command.
"""
import pytest
from django.contrib.auth import get_user_model
from django.core.management import call_command

Usuario = get_user_model()


@pytest.mark.django_db
class TestCreateAdmin:
    """Test create_admin management command."""

    def test_create_admin_creates_superuser(self):
        """
        The create_admin command should create a staff/superuser with
        the expected fixed identity (DNI: 00000000).
        """
        call_command("create_admin")

        user = Usuario.objects.get(dni="00000000")
        assert user is not None
        assert user.is_superuser is True
        assert user.is_staff is True
        assert user.is_active is True

    def test_create_admin_sets_correct_credentials(self):
        """
        The admin user should have the expected fixed credentials:
        DNI: 00000000, password: admin.
        """
        call_command("create_admin")

        user = Usuario.objects.get(dni="00000000")
        assert user.check_password("admin") is True

    def test_create_admin_sets_expected_identity_fields(self):
        """
        The admin user should have expected identity fields:
        nombres='Admin', apellidos='Sistema', email='admin@example.com'.
        """
        call_command("create_admin")

        user = Usuario.objects.get(dni="00000000")
        assert user.nombres == "Admin"
        assert user.apellidos == "Sistema"
        assert user.email == "admin@example.com"
        assert user.username == "admin"

    def test_create_admin_is_idempotent(self):
        """
        Running create_admin twice should not fail; it should update
        the existing user rather than creating a duplicate.
        """
        call_command("create_admin")
        call_command("create_admin")  # Should not raise

        users = Usuario.objects.filter(dni="00000000")
        assert users.count() == 1, "Should have exactly one admin user"

    def test_create_admin_with_force_resets_password(self):
        """
        Running create_admin --force should reset the password even if
        the user already exists.
        """
        call_command("create_admin")
        user = Usuario.objects.get(dni="00000000")
        user.set_password("different_password")
        user.save()

        call_command("create_admin", "--force")
        user.refresh_from_db()
        assert user.check_password("admin") is True
