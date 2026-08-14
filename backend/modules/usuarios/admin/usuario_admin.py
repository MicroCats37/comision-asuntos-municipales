"""Usuario model admin — extends UserAdmin for custom user with DNI."""

from django.contrib import admin
from django.contrib.auth.admin import UserAdmin

from modules.usuarios.domain.models import Usuario


@admin.register(Usuario)
class UsuarioAdmin(UserAdmin):
    """Admin for custom Usuario model (DNI-based auth)."""

    list_display = [
        "username",
        "dni",
        "nombres",
        "apellidos",
        "email",
        "is_staff",
        "is_active",
    ]
    search_fields = ["username", "dni", "email", "nombres", "apellidos"]
    list_filter = ["is_staff", "is_active", "is_superuser"]

    # Override fieldsets to match custom Usuario fields
    fieldsets = UserAdmin.fieldsets + (
        (
            "Datos personales",
            {
                "fields": (
                    "dni",
                    "nombres",
                    "apellidos",
                )
            },
        ),
    )

    # Fields shown when creating a user via admin
    add_fieldsets = UserAdmin.add_fieldsets + (
        (
            "Datos personales",
            {
                "fields": (
                    "dni",
                    "nombres",
                    "apellidos",
                )
            },
        ),
    )

    readonly_fields = ["created_at", "updated_at"]
