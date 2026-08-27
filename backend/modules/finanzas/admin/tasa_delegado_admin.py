"""Tasa de Delegado — admin."""

from django.contrib import admin

from modules.finanzas.domain.models.tasa_delegado import TasaDelegado


@admin.register(TasaDelegado)
class TasaDelegadoAdmin(admin.ModelAdmin):
    """Admin para las tasas de delegado."""

    list_display = ["nombre", "periodo_inicio", "periodo_fin", "vigente", "renta_cip", "aporte_codemu", "fondo_comun"]
    search_fields = ["nombre"]
    list_filter = ["periodo_inicio"]
    readonly_fields = ["created_at", "updated_at", "vigente"]

    def vigente(self, obj):
        return obj.periodo_fin is None

    vigente.short_description = "Vigente"
    vigente.boolean = True
