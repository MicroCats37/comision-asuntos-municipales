"""Admin para IGV y UIT - modelos de catálogo con vigencia."""

from django.contrib import admin

from core_application.vigencia.admin import VigenciaAdminMixin, VigenteHoyFilter
from modules.finanzas.domain.models import IGV, UIT


@admin.register(IGV)
class IGVAdmin(VigenciaAdminMixin):
    """Admin para IGV (tasa del impuesto general a las ventas con vigencia)."""

    list_display = ["valor", "periodo_inicio", "periodo_fin"]
    search_fields = []
    list_filter = [VigenteHoyFilter]
    readonly_fields = ["created_at", "updated_at"]


@admin.register(UIT)
class UITAdmin(VigenciaAdminMixin):
    """Admin para UIT (valor de la unidad impositiva tributaria en soles con vigencia)."""

    list_display = ["valor", "periodo_inicio", "periodo_fin"]
    search_fields = []
    list_filter = [VigenteHoyFilter]
    readonly_fields = ["created_at", "updated_at"]
