"""Proyecto admin."""

from django.contrib import admin

from modules.liquidaciones.domain.models import Proyecto


@admin.register(Proyecto)
class ProyectoAdmin(admin.ModelAdmin):
    """Admin for Proyecto (project linked to a liquidacion)."""

    list_display = [
        "denominacion",
        "nombre_propietario",
        "entidad",
        "distrito",
        "urbanizacion",
    ]
    search_fields = [
        "denominacion",
        "nombre_propietario",
        "entidad_numero_documento",
        "urbanizacion",
    ]
    list_filter = ["distrito__provincia__departamento"]
    readonly_fields = ["created_at", "updated_at"]
