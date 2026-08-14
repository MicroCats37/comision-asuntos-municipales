"""IGV and UIT admin — catalog models with validity."""

from django.contrib import admin

from modules.finanzas.domain.models import IGV, UIT


@admin.register(IGV)
class IGVAdmin(admin.ModelAdmin):
    """Admin for IGV (sales tax rate with validity)."""

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
    """Admin for UIT (tax unit value in soles with validity)."""

    list_display = ["valor", "periodo_inicio", "periodo_fin", "vigente"]
    search_fields = []
    list_filter = ["periodo_inicio"]
    readonly_fields = ["created_at", "updated_at", "vigente"]

    def vigente(self, obj):
        return obj.vigente

    vigente.short_description = "Vigente"
    vigente.boolean = True
