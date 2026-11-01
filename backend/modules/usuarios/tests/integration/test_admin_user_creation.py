import pytest
from django.contrib.auth import get_user_model
from django.urls import reverse
from django.test import override_settings


@pytest.mark.django_db
@override_settings(STORAGES={"staticfiles": {"BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage"}})
def test_admin_user_add_renders_password_errors_and_creates_valid_user(client):
    user_model = get_user_model()
    admin_user = user_model.objects.create_superuser(
        username="admin_user",
        password="admin-pass-123",
        email="admin@example.com",
    )
    client.force_login(admin_user)

    url = reverse("admin:usuarios_usuario_add")
    response = client.get(url)

    assert response.status_code == 200
    assert "password1" in response.content.decode()
    assert "password2" in response.content.decode()

    response = client.post(
        url,
        {
            "username": "new_user",
            "email": "new_user@example.com",
            "dni": "12345678",
            "nombres": "New",
            "apellidos": "User",
            "password1": "safe-password-123",
            "password2": "different-password-123",
            "_save": "Save",
        },
    )

    assert response.status_code == 200
    assert "password2" in response.context["adminform"].form.errors
    assert not user_model.objects.filter(username="new_user").exists()

    response = client.post(
        url,
        {
            "username": "new_user",
            "email": "new_user@example.com",
            "dni": "12345678",
            "nombres": "New",
            "apellidos": "User",
            "password1": "safe-password-123",
            "password2": "safe-password-123",
            "_save": "Save",
        },
    )

    assert response.status_code == 302
    created_user = user_model.objects.get(username="new_user")
    assert created_user.check_password("safe-password-123")
