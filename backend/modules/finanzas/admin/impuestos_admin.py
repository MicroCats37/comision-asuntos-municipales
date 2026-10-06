"""Admin para IGV y UIT — modelos de catálogo con vigencia."""

from django.contrib import admin

from modules.finanzas.domain.models import IGV, UIT


@admin.register(IGV)
class IGVAdmin(admin.ModelAdmin):
    """Admin para IGV (tasa del impuesto general a las ventas con vigencia)."""

    list_display = ["valor", "periodo_inicio", "periodo_fin", "vigente"]
    search_fields = []
    list_filter = ["periodo_inicio"]
    readonly_fields = ["created_at", "updated_at", "vigente"]

    def vigente(self, obj):
        return obj.vigente

    vigente.short_description = "Vigente"
    vigente.boolean = True


@admin.register(UIT)
class UITAdmin(admin.ModelAdmin):
    """Admin para UIT (valor de la unidad impositiva tributaria en soles con vigencia)."""

    list_display = ["valor", "periodo_inicio", "periodo_fin", "vigente"]
    search_fields = []
    list_filter = ["periodo_inicio"]
    readonly_fields = ["created_at", "updated_at", "vigente"]

    def vigente(self, obj):
        return obj.vigente

    vigente.short_description = "Vigente"
    vigente.boolean = True
