"""RH Mensual (Delegado, Inspector) y Repartición Estacional — admin."""

from django.contrib import admin

from modules.finanzas.domain.models.detalle_honorario_delegado import (
    DetalleHonorarioDelegado,
)
from modules.finanzas.domain.models.detalle_honorario_inspector import (
    DetalleHonorarioInspector,
)
from modules.finanzas.domain.models.recibo_honorario import (
    ReciboHonorarioDelegado,
)
from modules.finanzas.domain.models.recibo_honorario_delegado_mensual import (
    ReciboHonorarioDelegadoMensual,
)
from modules.finanzas.domain.models.recibo_honorario_inspector_mensual import (
    ReciboHonorarioInspectorMensual,
)
from modules.finanzas.domain.models.registro_pago_inspector import (
    RegistroPagoInspector,
)
from modules.finanzas.domain.models.rh_reparticion_estacional import (
    RHReparticionEstacional,
    RHReparticionEstacionalDelegado,
    RHReparticionEstacionalCapitulo,
)


# ── Inlines ────────────────────────────────────────────────────────────────────


class DetalleHonorarioDelegadoInline(admin.TabularInline):
    """Inline para los detalles de un recibo mensual del delegado."""

    model = DetalleHonorarioDelegado
    extra = 0
    readonly_fields = ["created_at", "updated_at"]


class DetalleHonorarioInspectorInline(admin.TabularInline):
    """Inline para los detalles de un recibo mensual del inspector."""

    model = DetalleHonorarioInspector
    extra = 0
    readonly_fields = ["created_at", "updated_at"]


class RHReparticionEstacionalDelegadoInline(admin.TabularInline):
    """Inline para los detalles de delegado de una repartición estacional."""

    model = RHReparticionEstacionalDelegado
    extra = 0
    readonly_fields = ["created_at", "updated_at"]


class RHReparticionEstacionalCapituloInline(admin.TabularInline):
    """Inline para los detalles de capítulo de una repartición estacional."""

    model = RHReparticionEstacionalCapitulo
    extra = 0
    readonly_fields = ["created_at", "updated_at"]


# ── Admins ─────────────────────────────────────────────────────────────────────


@admin.register(ReciboHonorarioDelegado)
class ReciboHonorarioDelegadoAdmin(admin.ModelAdmin):
    """Admin para los recibos de honorarios del delegado."""

    list_display = [
        "liquidacion_delegado",
        "imp_bruto",
        "renta_cip",
        "aporte_codemu",
        "fondo_comun",
        "neto_honorario",
        "honorario",
        "created_at",
    ]
    list_filter = ["created_at"]
    search_fields = [
        "liquidacion_delegado__delegado__perfil_ingeniero__cip",
        "liquidacion_delegado__delegado__perfil_ingeniero__dni",
    ]
    readonly_fields = [
        "created_at",
        "updated_at",
        "sub_total",
        "imp_bruto",
        "renta_cip",
        "aporte_codemu",
        "fondo_comun",
        "neto_honorario",
        "honorario",
    ]


@admin.register(ReciboHonorarioDelegadoMensual)
class ReciboHonorarioDelegadoMensualAdmin(admin.ModelAdmin):
    """Admin para los recibos de honorarios mensuales del delegado."""

    list_display = [
        "delegado",
        "periodo",
        "mes",
        "sub_total",
        "renta_cip",
        "aporte_codemu",
        "fondo_comun",
        "neto_honorario",
        "fecha_registro",
    ]
    list_filter = ["periodo", "mes", "delegado"]
    search_fields = [
        "delegado__perfil_ingeniero__cip",
        "delegado__perfil_ingeniero__dni",
        "delegado__perfil_ingeniero__nombre_completo",
    ]
    readonly_fields = ["created_at", "updated_at", "fecha_registro"]
    inlines = [DetalleHonorarioDelegadoInline]


@admin.register(ReciboHonorarioInspectorMensual)
class ReciboHonorarioInspectorMensualAdmin(admin.ModelAdmin):
    """Admin para los recibos de honorarios mensuales del inspector."""

    list_display = [
        "inspector",
        "periodo",
        "mes",
        "numero",
        "escala_descuento",
        "sub_total",
        "descuento",
        "honorarios",
        "fecha_registro",
    ]
    list_filter = ["periodo", "mes", "escala_descuento"]
    search_fields = [
        "inspector__perfil_ingeniero__cip",
        "inspector__perfil_ingeniero__dni",
        "inspector__perfil_ingeniero__nombre_completo",
    ]
    readonly_fields = ["created_at", "updated_at", "fecha_registro"]
    inlines = [DetalleHonorarioInspectorInline]


@admin.register(RegistroPagoInspector)
class RegistroPagoInspectorAdmin(admin.ModelAdmin):
    """Admin para los registros de pago de inspecciones."""

    list_display = [
        "liquidacion_por_categoria_visitas",
        "periodo",
        "mes",
        "inspecciones_pagadas",
        "fecha_registro",
    ]
    list_filter = ["periodo", "mes"]
    search_fields = [
        "liquidacion_por_categoria_visitas__liquidacion_general__expediente",
    ]
    readonly_fields = ["created_at", "updated_at", "fecha_registro"]


@admin.register(RHReparticionEstacional)
class RHReparticionEstacionalAdmin(admin.ModelAdmin):
    """Admin para las reparticiones estacionales de fondo común."""

    list_display = [
        "especialidad_revision",
        "periodo",
        "mes_desde",
        "mes_hasta",
        "total_fondo_comun",
        "numero_delegados",
        "numero_capitulos",
        "monto_por_participacion",
        "residual",
    ]
    list_filter = ["periodo", "especialidad_revision"]
    search_fields = [
        "especialidad_revision__nombre",
    ]
    readonly_fields = [
        "created_at",
        "updated_at",
        "is_deleted",
        "deleted_at",
        "numero_capitulos",
        "numero_delegados",
        "monto_por_participacion",
        "residual",
    ]
    inlines = [RHReparticionEstacionalDelegadoInline, RHReparticionEstacionalCapituloInline]
