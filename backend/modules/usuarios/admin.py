"""Admin configuration for usuarios module."""

from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from simple_history.admin import SimpleHistoryAdmin

from .models import Usuario, PerfilIngeniero
from .domain.models.perfil_ingeniero import Capitulo


@admin.register(Usuario)
class UsuarioAdmin(BaseUserAdmin, SimpleHistoryAdmin):
    """Admin para modelo Usuario customizado (basado en DNI)."""

    list_display = ["dni", "nombres", "apellidos", "username", "email", "is_staff", "is_active"]
    list_display_links = ["dni"]
    list_filter = ["is_staff", "is_active", "is_superuser"]
    search_fields = ["dni", "nombres", "apellidos", "username", "email"]
    ordering = ["dni"]
    autocomplete_fields = ["groups"]

    # username es el USERNAME_FIELD - se usa como identificador
    username_field = "username"

    # Campos mostrados al ver/editar un usuario
    fieldsets = (
        ("Identificación", {"fields": ("username", "dni")}),
        ("Información Personal", {"fields": ("nombres", "apellidos", "email")}),
        ("Permisos", {"fields": ("is_active", "is_staff", "is_superuser", "groups", "user_permissions")}),
        ("Fechas", {"fields": ("last_login", "created_at", "updated_at")}),
    )
    readonly_fields = ["last_login", "created_at", "updated_at"]

    # Campos mostrados al crear un usuario
    add_fieldsets = (
        (None, {
            "classes": ("wide",),
            "fields": ("username", "password1", "password2"),
        }),
    )


@admin.register(PerfilIngeniero)
class PerfilIngenieroAdmin(SimpleHistoryAdmin):
    """Admin para PerfilIngeniero."""

    list_display = ["cip", "nombres", "apellido_paterno", "apellido_materno", "capitulo", "genero_display"]
    list_display_links = ["cip"]
    list_filter = ["capitulo", "genero"]
    search_fields = ["cip", "nombres", "apellido_paterno", "apellido_materno", "correo_personal", "correo_institucional"]
    ordering = ["apellido_paterno", "apellido_materno", "nombres"]
    readonly_fields = ["created_at", "updated_at"]
    autocomplete_fields = ["capitulo"]

    fieldsets = (
        (None, {"fields": ("cip", "capitulo")}),
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
    """Admin para Capitulo."""

    list_display = ["codigo", "abreviacion", "nombre", "grupo_envio_intitucional"]
    list_display_links = ["codigo"]
    list_filter = ["nombre"]
    search_fields = ["registro_id", "abreviacion", "nombre"]
    ordering = ["nombre"]
    readonly_fields = ["created_at", "updated_at"]

    def codigo(self, obj):
        """Muestra registro_id como 'Código' para evitar confusión con IDs técnicos."""
        return obj.registro_id
    codigo.short_description = "Código"
    codigo.allow_tags = True