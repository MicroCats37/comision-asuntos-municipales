"""Admin configuration for usuarios module."""

from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from simple_history.admin import SimpleHistoryAdmin

from .models import Usuario, PerfilIngeniero
from .domain.models.perfil_ingeniero import Capitulo


@admin.register(Usuario)
class UsuarioAdmin(BaseUserAdmin, SimpleHistoryAdmin):
    """Admin for custom Usuario model (DNI-based)."""

    list_display = ["dni", "nombres", "apellidos", "username", "email", "is_staff", "is_active"]
    list_display_links = ["dni"]
    list_filter = ["is_staff", "is_active", "is_superuser"]
    search_fields = ["dni", "nombres", "apellidos", "username", "email"]
    ordering = ["dni"]
    autocomplete_fields = ["groups"]

    # DNI is the USERNAME_FIELD - use it as identifier
    username_field = "dni"

    # Fields shown when viewing/editing a user
    fieldsets = (
        ("Identificación", {"fields": ("dni",)}),
        ("Información Personal", {"fields": ("nombres", "apellidos", "email", "username")}),
        ("Permisos", {"fields": ("is_active", "is_staff", "is_superuser", "groups", "user_permissions")}),
        ("Fechas", {"fields": ("last_login", "created_at", "updated_at")}),
    )
    readonly_fields = ["last_login", "created_at", "updated_at"]

    # Fields shown when creating a user
    add_fieldsets = (
        (None, {
            "classes": ("wide",),
            "fields": ("dni", "password1", "password2"),
        }),
    )


@admin.register(PerfilIngeniero)
class PerfilIngenieroAdmin(SimpleHistoryAdmin):
    """Admin for PerfilIngeniero."""

    list_display = ["cip", "nombres", "apellido_paterno", "apellido_materno", "usuario", "capitulo", "genero_display"]
    list_display_links = ["cip"]
    list_filter = ["capitulo", "genero"]
    search_fields = ["cip", "nombres", "apellido_paterno", "apellido_materno", "usuario__dni", "correo_personal", "correo_institucional"]
    ordering = ["apellido_paterno", "apellido_materno", "nombres"]
    readonly_fields = ["created_at", "updated_at"]
    autocomplete_fields = ["usuario", "capitulo"]

    fieldsets = (
        (None, {"fields": ("usuario", "cip", "capitulo")}),
        ("Datos Personales", {"fields": ("nombres", "apellido_paterno", "apellido_materno", "fecha_nacimiento", "genero")}),
        ("Información de Contacto", {"fields": ("correo_personal", "correo_institucional", "direccion", "ubigeo")}),
        ("Información Profesional", {"fields": ("codigo_especialidad",)}),
        ("Auditoría", {"fields": ("created_at", "updated_at")}),
    )

    def genero_display(self, obj):
        return obj.genero or "—"
    genero_display.short_description = "Género"
    genero_display.allow_tags = True


@admin.register(Capitulo)
class CapituloAdmin(SimpleHistoryAdmin):
    """Admin for Capitulo."""

    list_display = ["codigo", "abreviacion", "nombre", "grupo_envio_intitucional"]
    list_display_links = ["codigo"]
    list_filter = ["nombre"]
    search_fields = ["registro_id", "abreviacion", "nombre"]
    ordering = ["nombre"]
    readonly_fields = ["created_at", "updated_at"]

    def codigo(self, obj):
        """Display registro_id as 'Código' to avoid confusion with technical IDs."""
        return obj.registro_id
    codigo.short_description = "Código"
    codigo.allow_tags = True