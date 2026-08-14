"""Professionals admin classes: Delegado, Inspector, Proyectista."""

from django.contrib import admin

from modules.liquidaciones.domain.models import (
    Delegado,
    DelegadoMunicipalidad,
    DelegadoMunicipalidadPeriodo,
    Inspector,
    InspectorTipoLiquidacion,
    InspectorAsignacionPeriodo,
    Proyectista,
)


# ── Inlines for Delegado ────────────────────────────────────────


class DelegadoMunicipalidadInline(admin.TabularInline):
    """Inline for DelegadoMunicipalidad (assigned districts to a delegate)."""

    model = DelegadoMunicipalidad
    extra = 1
    readonly_fields = ["created_at", "updated_at"]


class DelegadoMunicipalidadPeriodoInline(admin.TabularInline):
    """Inline for DelegadoMunicipalidadPeriodo (validity periods)."""

    model = DelegadoMunicipalidadPeriodo
    extra = 1
    readonly_fields = ["created_at", "updated_at"]


# ── Inlines for Inspector ───────────────────────────────────────


class InspectorTipoLiquidacionInline(admin.TabularInline):
    """Inline for InspectorTipoLiquidacion (inspector type assignments)."""

    model = InspectorTipoLiquidacion
    extra = 1
    readonly_fields = ["created_at", "updated_at"]


class InspectorAsignacionPeriodoInline(admin.TabularInline):
    """Inline for InspectorAsignacionPeriodo (validity periods)."""

    model = InspectorAsignacionPeriodo
    extra = 1
    readonly_fields = ["created_at", "updated_at"]


# ── Admins ──────────────────────────────────────────────────────


@admin.register(Delegado)
class DelegadoAdmin(admin.ModelAdmin):
    """Admin for Delegado (delegate engineer) with nested inlines."""

    list_display = ["perfil_ingeniero", "especialidad_revision"]
    search_fields = [
        "perfil_ingeniero__nombres",
        "perfil_ingeniero__apellido_paterno",
        "perfil_ingeniero__cip",
    ]
    list_filter = ["especialidad_revision"]
    readonly_fields = ["created_at", "updated_at"]
    inlines = [DelegadoMunicipalidadInline]


@admin.register(DelegadoMunicipalidad)
class DelegadoMunicipalidadAdmin(admin.ModelAdmin):
    """Standalone admin for DelegadoMunicipalidad (not typically needed separately)."""

    list_display = ["delegado", "municipalidad", "liquidacion_revision", "tipo"]
    search_fields = [
        "delegado__perfil_ingeniero__nombres",
        "delegado__perfil_ingeniero__apellido_paterno",
        "municipalidad__nombre",
    ]
    list_filter = ["tipo", "liquidacion_revision"]
    readonly_fields = ["created_at", "updated_at"]
    inlines = [DelegadoMunicipalidadPeriodoInline]


@admin.register(Inspector)
class InspectorAdmin(admin.ModelAdmin):
    """Admin for Inspector with nested inlines."""

    list_display = ["perfil_ingeniero", "especialidad_revision"]
    search_fields = [
        "perfil_ingeniero__nombres",
        "perfil_ingeniero__apellido_paterno",
        "perfil_ingeniero__cip",
    ]
    list_filter = ["especialidad_revision"]
    readonly_fields = ["created_at", "updated_at"]
    inlines = [InspectorTipoLiquidacionInline]


@admin.register(InspectorTipoLiquidacion)
class InspectorTipoLiquidacionAdmin(admin.ModelAdmin):
    """Standalone admin for InspectorTipoLiquidacion."""

    list_display = ["inspector", "tipo_liquidacion", "numero_registro", "categoria"]
    search_fields = [
        "inspector__perfil_ingeniero__nombres",
        "inspector__perfil_ingeniero__apellido_paterno",
        "numero_registro",
    ]
    list_filter = ["tipo_liquidacion", "categoria"]
    readonly_fields = ["created_at", "updated_at"]
    inlines = [InspectorAsignacionPeriodoInline]


@admin.register(Proyectista)
class ProyectistaAdmin(admin.ModelAdmin):
    """Admin for Proyectista (project engineer)."""

    list_display = ["perfil_ingeniero"]
    search_fields = [
        "perfil_ingeniero__nombres",
        "perfil_ingeniero__apellido_paterno",
        "perfil_ingeniero__apellido_materno",
        "perfil_ingeniero__cip",
    ]
    readonly_fields = ["created_at", "updated_at"]
