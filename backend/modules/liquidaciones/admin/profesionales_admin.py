"""Professionals admin classes: Delegado, Inspector, Proyectista."""

from django.contrib import admin

from modules.liquidaciones.domain.models import (
    Delegado,
    DelegadoOperacion,
    DelegadoOperacionPeriodo,
    Inspector,
    InspectorOperacion,
    InspectorOperacionPeriodo,
    Proyectista,
)


# ── Inlines for Delegado ────────────────────────────────────────


class DelegadoOperacionInline(admin.TabularInline):
    """Inline for DelegadoOperacion (assigned districts to a delegate)."""

    model = DelegadoOperacion
    extra = 1
    readonly_fields = ["created_at", "updated_at"]


class DelegadoOperacionPeriodoInline(admin.TabularInline):
    """Inline for DelegadoOperacionPeriodo (validity periods)."""

    model = DelegadoOperacionPeriodo
    extra = 1
    readonly_fields = ["created_at", "updated_at"]


# ── Inlines for Inspector ───────────────────────────────────────


class InspectorOperacionInline(admin.TabularInline):
    """Inline for InspectorOperacion (inspector type assignments)."""

    model = InspectorOperacion
    extra = 1
    readonly_fields = ["created_at", "updated_at"]


class InspectorOperacionPeriodoInline(admin.TabularInline):
    """Inline for InspectorOperacionPeriodo (validity periods)."""

    model = InspectorOperacionPeriodo
    extra = 1
    readonly_fields = ["created_at", "updated_at"]


# ── Admins ──────────────────────────────────────────────────────


@admin.register(Delegado)
class DelegadoAdmin(admin.ModelAdmin):
    """Admin for Delegado (delegate engineer) with nested inlines."""

    list_display = ["perfil_ingeniero"]
    search_fields = [
        "perfil_ingeniero__nombres",
        "perfil_ingeniero__apellido_paterno",
        "perfil_ingeniero__cip",
    ]
    readonly_fields = ["created_at", "updated_at"]
    inlines = [DelegadoOperacionInline]


@admin.register(DelegadoOperacion)
class DelegadoOperacionAdmin(admin.ModelAdmin):
    """Standalone admin for DelegadoOperacion (not typically needed separately)."""

    list_display = ["delegado", "municipalidad", "liquidacion_revision", "tipo"]
    search_fields = [
        "delegado__perfil_ingeniero__nombres",
        "delegado__perfil_ingeniero__apellido_paterno",
        "municipalidad__nombre",
    ]
    list_filter = ["tipo", "liquidacion_revision"]
    readonly_fields = ["created_at", "updated_at"]
    inlines = [DelegadoOperacionPeriodoInline]


@admin.register(Inspector)
class InspectorAdmin(admin.ModelAdmin):
    """Admin for Inspector with nested inlines."""

    list_display = ["perfil_ingeniero"]
    search_fields = [
        "perfil_ingeniero__nombres",
        "perfil_ingeniero__apellido_paterno",
        "perfil_ingeniero__cip",
    ]
    readonly_fields = ["created_at", "updated_at"]
    inlines = [InspectorOperacionInline]


@admin.register(InspectorOperacion)
class InspectorOperacionAdmin(admin.ModelAdmin):
    """Standalone admin for InspectorOperacion."""

    list_display = ["inspector", "tipo_liquidacion", "numero_registro", "categoria"]
    search_fields = [
        "inspector__perfil_ingeniero__nombres",
        "inspector__perfil_ingeniero__apellido_paterno",
        "numero_registro",
    ]
    list_filter = ["tipo_liquidacion", "categoria"]
    readonly_fields = ["created_at", "updated_at"]
    inlines = [InspectorOperacionPeriodoInline]


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
