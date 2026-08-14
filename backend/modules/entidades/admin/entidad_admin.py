"""Entidad admin — master entity (RUC/DNI)."""

from django.contrib import admin

from modules.entidades.domain.models import Entidad


@admin.register(Entidad)
class EntidadAdmin(admin.ModelAdmin):
    """Admin for Entidad (unified entity: RUC institution or DNI natural person)."""

    list_display = ["numero_documento", "tipo_documento", "nombre_completo"]
    search_fields = ["numero_documento"]
    list_filter = ["tipo_documento"]
    readonly_fields = ["created_at", "updated_at"]

    def nombre_completo(self, obj):
        # entidad.nombre_completo returns numero_documento as identifier
        return f"({obj.numero_documento})"

    nombre_completo.short_description = "Identificador"
