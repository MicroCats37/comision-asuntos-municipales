"""PerfilIngeniero admin."""

from django.contrib import admin

from modules.usuarios.domain.models import PerfilIngeniero


@admin.register(PerfilIngeniero)
class PerfilIngenieroAdmin(admin.ModelAdmin):
    """Admin for PerfilIngeniero (linked to Usuario)."""

    list_display = [
        "cip",
        "nombre_completo",
        "dni",
        "especialidad",
        "capitulo",
        "correo_institucional",
    ]
    search_fields = [
        "cip",
        "dni",
        "nombres",
        "apellido_paterno",
        "apellido_materno",
        "correo_personal",
        "correo_institucional",
    ]
    list_filter = ["especialidad", "capitulo", "genero"]
    readonly_fields = ["created_at", "updated_at"]

    def nombre_completo(self, obj):
        return obj.nombre_completo

    nombre_completo.short_description = "Nombre completo"
