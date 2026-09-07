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

    # Completely override fieldsets — do NOT inherit from UserAdmin.fieldsets
    # The Usuario model inherits from AbstractBaseUser and lacks first_name, last_name, date_joined
    fieldsets = (
        (None, {"fields": ("username", "password")}),
        (
            "Datos personales",
            {
                "fields": (
                    "nombres",
                    "apellidos",
                    "dni",
                    "email",
                )
            },
        ),
        (
            "Permisos",
            {
                "fields": (
                    "is_active",
                    "is_staff",
                    "is_superuser",
                    "groups",
                    "user_permissions",
                )
            },
        ),
        (
            "Fechas importantes",
            {"fields": ("last_login",)},
        ),
    )

    # Fields shown when creating a user via admin
    # UserCreationForm handles password automatically, so we only supply the needed fields
    add_fieldsets = (
        (None, {
            "classes": ("wide",),
            "fields": ("username", "email", "dni", "nombres", "apellidos"),
        }),
    )

    readonly_fields = ["created_at", "updated_at"]
