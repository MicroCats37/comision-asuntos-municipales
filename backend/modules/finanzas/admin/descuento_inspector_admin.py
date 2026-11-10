"""Escala de descuento y recibos de honorarios de inspectores — admin."""

from django.contrib import admin

from core_application.vigencia.admin import VigenciaAdminMixin, VigenteHoyFilter
from modules.finanzas.domain.models.descuento_inspector import (
    EscalaDescuentoInspector,
    RangoDescuentoInspector,
)
from modules.finanzas.domain.models.recibo_honorario_inspector import (
    ReciboHonorarioInspector,
)


class RangoDescuentoInspectorInline(admin.TabularInline):
    """Inline para editar los rangos dentro de la escala."""

    model = RangoDescuentoInspector
    extra = 0


@admin.register(EscalaDescuentoInspector)
class EscalaDescuentoInspectorAdmin(VigenciaAdminMixin):
    """Admin para la escala de descuento de inspectores."""

    list_display = ["nombre", "periodo_inicio", "periodo_fin"]
    search_fields = ["nombre"]
    list_filter = [VigenteHoyFilter]
    readonly_fields = ["created_at", "updated_at"]
    inlines = [RangoDescuentoInspectorInline]


@admin.register(RangoDescuentoInspector)
class RangoDescuentoInspectorAdmin(admin.ModelAdmin):
    """Admin para los rangos de la escala de descuento."""

    list_display = [
        "escala",
        "monto_minimo",
        "monto_maximo",
        "porcentaje_descuento",
    ]
    list_filter = ["escala"]
    search_fields = ["escala__nombre"]
    readonly_fields = ["created_at", "updated_at"]


@admin.register(ReciboHonorarioInspector)
class ReciboHonorarioInspectorAdmin(admin.ModelAdmin):
    """Admin para los recibos de honorarios de inspectores."""

    list_display = [
        "liquidacion_inspector",
        "escala_descuento",
        "inspecciones_mes",
        "monto_bruto",
        "descuento",
        "honorarios",
        "created_at",
    ]
    list_filter = ["escala_descuento", "created_at"]
    search_fields = [
        "liquidacion_inspector__inspector__perfil_ingeniero__cip",
        "liquidacion_inspector__inspector__perfil_ingeniero__dni",
    ]
    readonly_fields = [
        "created_at",
        "updated_at",
        "inspecciones_programadas",
        "costo_por_inspeccion",
        "inspecciones_mes",
        "monto_bruto",
        "inspecciones_pagadas",
        "saldo_inspecciones",
        "sub_total",
        "tasa_descuento_aplicada",
        "descuento",
        "honorarios",
    ]
