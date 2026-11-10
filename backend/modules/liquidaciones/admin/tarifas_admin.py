"""Tariffs and rules admin classes for liquidaciones module."""

from django.contrib import admin

from core_application.vigencia.admin import VigenciaAdminMixin, VigenteHoyFilter
from modules.liquidaciones.domain.constants import TipoLiquidacion
from modules.liquidaciones.domain.models.liquidacion.liquidacion_tipo.tarifas_reglas import (
    TarifaBaseMetroCuadradoProxy,
    TarifaBasePorcentajeObraProxy,
    TarifaBaseVisitasProxy,
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


class BaseTarifaLiquidacionProxyAdmin(VigenciaAdminMixin):
    """Admin behaviour shared by a tariff family with one calculation method."""

    list_display = ["tipo_liquidacion", "periodo_inicio", "periodo_fin"]
    search_fields = ["tipo_liquidacion__nombre"]
    list_filter = ["tipo_liquidacion", VigenteHoyFilter]
    ordering = ["tipo_liquidacion", "-periodo_inicio"]
    readonly_fields = ["created_at", "updated_at"]
    tipo_codigos = ()

    def get_queryset(self, request):
        return super().get_queryset(request).filter(
            tipo_liquidacion__codigo__in=self.tipo_codigos
        )

    def get_form(self, request, obj=None, **kwargs):
        form_class = super().get_form(request, obj, **kwargs)
        form_class.base_fields["tipo_liquidacion"].queryset = (
            form_class.base_fields["tipo_liquidacion"].queryset.filter(
                codigo__in=self.tipo_codigos
            )
        )
        return form_class


@admin.register(TarifaBasePorcentajeObraProxy)
class TarifaBasePorcentajeObraProxyAdmin(BaseTarifaLiquidacionProxyAdmin):
    """Tariff bases for Edificación, Impacto Vial, and Taludes."""

    tipo_codigos = (
        TipoLiquidacion.EDIFICACION,
        TipoLiquidacion.IMPACTO_VIAL,
        TipoLiquidacion.TALUDES,
    )
    inlines = [TarifaPorcentajeObraInline]


@admin.register(TarifaBaseMetroCuadradoProxy)
class TarifaBaseMetroCuadradoProxyAdmin(BaseTarifaLiquidacionProxyAdmin):
    """Tariff bases for Habilitación Urbana and Mecánica de Suelos."""

    tipo_codigos = (
        TipoLiquidacion.HABILITACION_URBANA,
        TipoLiquidacion.MECANICA_SUELOS,
    )
    inlines = [TarifaPorMetroCuadradoInline]


@admin.register(TarifaBaseVisitasProxy)
class TarifaBaseVisitasProxyAdmin(BaseTarifaLiquidacionProxyAdmin):
    """Tariff bases for Inspección de Obra."""

    tipo_codigos = (TipoLiquidacion.INSPECCION_OBRA,)
    inlines = [TarifaPorCategoriaVisitasInline]


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

    list_display = ["tarifa_base", "porcentaje_liquidacion"]
    search_fields = [
        "tarifa_base__tipo_liquidacion__nombre",
    ]
    list_filter = ["tarifa_base__tipo_liquidacion"]
    readonly_fields = ["created_at", "updated_at"]


@admin.register(DerechoPorcentajeObra)
class DerechoPorcentajeObraAdmin(VigenciaAdminMixin):
    """Admin for DerechoPorcentajeObra (minimum percentage rights)."""

    list_display = [
        "derecho_minimo",
        "derecho_maximo",
        "porcentaje_minimo_uit",
        "periodo_inicio",
        "periodo_fin",
    ]
    search_fields = []
    list_filter = [VigenteHoyFilter]
    readonly_fields = ["created_at", "updated_at"]


@admin.register(DerechoPorMetroCuadrado)
class DerechoPorMetroCuadradoAdmin(VigenciaAdminMixin):
    """Admin for DerechoPorMetroCuadrado (minimum M2 rights)."""

    list_display = ["derecho_minimo", "derecho_maximo", "periodo_inicio", "periodo_fin"]
    search_fields = []
    list_filter = [VigenteHoyFilter]
    readonly_fields = ["created_at", "updated_at"]
