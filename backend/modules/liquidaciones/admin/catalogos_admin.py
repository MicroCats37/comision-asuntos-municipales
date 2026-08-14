"""Catalog admin classes for liquidaciones module."""

from django.contrib import admin

from modules.liquidaciones.domain.models import TipoLiquidacion
from modules.liquidaciones.domain.models.liquidacion.liquidacion_general.liquidacion import (
    LiquidacionEspecialidadDisponibles,
)


@admin.register(TipoLiquidacion)
class TipoLiquidacionAdmin(admin.ModelAdmin):
    """Admin for TipoLiquidacion (liquidation type catalog)."""

    list_display = ["codigo", "nombre"]
    search_fields = ["codigo", "nombre"]
    readonly_fields = ["created_at", "updated_at"]


@admin.register(LiquidacionEspecialidadDisponibles)
class LiquidacionEspecialidadDisponiblesAdmin(admin.ModelAdmin):
    """Admin for LiquidacionEspecialidadDisponibles (available specialties per type)."""

    list_display = ["tipo_liquidacion", "especialidad", "activo"]
    search_fields = ["tipo_liquidacion__nombre", "especialidad__nombre"]
    list_filter = ["tipo_liquidacion", "activo"]
    readonly_fields = ["created_at", "updated_at"]
