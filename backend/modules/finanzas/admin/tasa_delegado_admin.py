"""Tasa de Delegado — admin."""

from django.contrib import admin

from core_application.vigencia.admin import VigenciaAdminMixin, VigenteHoyFilter
from modules.finanzas.domain.models.tasa_delegado import TasaDelegado


@admin.register(TasaDelegado)
class TasaDelegadoAdmin(VigenciaAdminMixin):
    """Admin para las tasas de delegado."""

    list_display = [
        "tipo_liquidacion",
        "nombre",
        "periodo_inicio",
        "periodo_fin",
        "renta_cip",
        "aporte_codemu",
        "fondo_comun",
    ]
    search_fields = ["nombre"]
    list_filter = ["tipo_liquidacion", VigenteHoyFilter]
    readonly_fields = ["created_at", "updated_at"]
