"""Tariffs and rules admin classes for liquidaciones module."""

from django.contrib import admin

from modules.liquidaciones.domain.models.liquidacion.liquidacion_tipo.tarifas_reglas import (
    TarifaLiquidacionBase,
    TarifaPorMetroCuadrado,
    TarifaPorCategoriaVisitas,
    TarifaPorcentajeObra,
    DerechoPorcentajeObra,
    DerechoPorMetroCuadrado,
)


# ── Inlines for TarifaLiquidacionBase ───────────────────────────


class TarifaPorMetroCuadradoInline(admin.StackedInline):
    """Inline for TarifaPorMetroCuadrado (OneToOne extension of TarifaLiquidacionBase)."""

    model = TarifaPorMetroCuadrado
    extra = 0
    readonly_fields = ["created_at", "updated_at"]


class TarifaPorCategoriaVisitasInline(admin.TabularInline):
    """Inline for TarifaPorCategoriaVisitas (FK from TarifaLiquidacionBase)."""

    model = TarifaPorCategoriaVisitas
    extra = 1
    readonly_fields = ["created_at", "updated_at"]


class TarifaPorcentajeObraInline(admin.TabularInline):
    """Inline for TarifaPorcentajeObra (OneToOne extension of TarifaLiquidacionBase)."""

    model = TarifaPorcentajeObra
    extra = 0
    readonly_fields = ["created_at", "updated_at"]


# ── Admins ──────────────────────────────────────────────────────


@admin.register(TarifaLiquidacionBase)
class TarifaLiquidacionBaseAdmin(admin.ModelAdmin):
    """Admin for TarifaLiquidacionBase with inlines for its tariff details."""

    list_display = ["tipo_liquidacion", "periodo_inicio", "periodo_fin"]
    search_fields = ["tipo_liquidacion__nombre"]
    list_filter = ["tipo_liquidacion"]
    readonly_fields = ["created_at", "updated_at"]
    inlines = [
        TarifaPorMetroCuadradoInline,
        TarifaPorCategoriaVisitasInline,
        TarifaPorcentajeObraInline,
    ]


@admin.register(TarifaPorMetroCuadrado)
class TarifaPorMetroCuadradoAdmin(admin.ModelAdmin):
    """Standalone admin for TarifaPorMetroCuadrado."""

    list_display = ["tarifa_base", "costo_por_m2"]
    search_fields = ["tarifa_base__tipo_liquidacion__nombre"]
    list_filter = ["tarifa_base__tipo_liquidacion"]
    readonly_fields = ["created_at", "updated_at"]


@admin.register(TarifaPorCategoriaVisitas)
class TarifaPorCategoriaVisitasAdmin(admin.ModelAdmin):
    """Standalone admin for TarifaPorCategoriaVisitas."""

    list_display = ["tarifa_base", "categoria_visitas", "porcentaje_uit"]
    search_fields = ["tarifa_base__tipo_liquidacion__nombre"]
    list_filter = ["tarifa_base__tipo_liquidacion", "categoria_visitas"]
    readonly_fields = ["created_at", "updated_at"]


@admin.register(TarifaPorcentajeObra)
class TarifaPorcentajeObraAdmin(admin.ModelAdmin):
    """Standalone admin for TarifaPorcentajeObra."""

    list_display = ["tarifa_base", "especialidad", "porcentaje_liquidacion"]
    search_fields = [
        "tarifa_base__tipo_liquidacion__nombre",
        "especialidad__nombre",
    ]
    list_filter = ["tarifa_base__tipo_liquidacion", "especialidad"]
    readonly_fields = ["created_at", "updated_at"]


@admin.register(DerechoPorcentajeObra)
class DerechoPorcentajeObraAdmin(admin.ModelAdmin):
    """Admin for DerechoPorcentajeObra (minimum percentage rights)."""

    list_display = [
        "derecho_minimo",
        "derecho_maximo",
        "porcentaje_minimo_uit",
        "periodo_inicio",
        "periodo_fin",
    ]
    search_fields = []
    list_filter = ["periodo_inicio"]
    readonly_fields = ["created_at", "updated_at"]


@admin.register(DerechoPorMetroCuadrado)
class DerechoPorMetroCuadradoAdmin(admin.ModelAdmin):
    """Admin for DerechoPorMetroCuadrado (minimum M2 rights)."""

    list_display = ["derecho_minimo", "derecho_maximo", "periodo_inicio", "periodo_fin"]
    search_fields = []
    list_filter = ["periodo_inicio"]
    readonly_fields = ["created_at", "updated_at"]
