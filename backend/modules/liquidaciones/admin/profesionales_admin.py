"""Professionals admin classes: Delegado, Inspector, Proyectista."""

from django.contrib import admin
from import_export.admin import ImportExportMixin

from modules.liquidaciones.domain.models import (
    Delegado,
    DelegadoOperacion,
    DelegadoOperacionPeriodo,
    Inspector,
    InspectorOperacion,
    InspectorOperacionPeriodo,
    Proyectista,
)
from modules.liquidaciones.domain.resources import (
    DelegadoOperacionResource,
    InspectorOperacionResource,
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
class DelegadoOperacionAdmin(ImportExportMixin, admin.ModelAdmin):
    """Standalone admin for DelegadoOperacion with Excel import/export support."""

    list_display = ["delegado_nombre", "delegado_cip", "municipalidad", "tipo_liquidacion", "tipo", "vigente"]
    search_fields = [
        "delegado__perfil_ingeniero__nombres",
        "delegado__perfil_ingeniero__apellido_paterno",
        "municipalidad__nombre",
    ]
    list_filter = ["tipo", "tipo_liquidacion"]
    readonly_fields = ["created_at", "updated_at"]
    inlines = [DelegadoOperacionPeriodoInline]
    resource_classes = [DelegadoOperacionResource]

    @admin.display(description="Delegado", ordering="delegado__perfil_ingeniero__apellido_paterno")
    def delegado_nombre(self, obj):
        return obj.delegado.perfil_ingeniero.nombre_completo

    @admin.display(description="CIP", ordering="delegado__perfil_ingeniero__cip")
    def delegado_cip(self, obj):
        return obj.delegado.perfil_ingeniero.cip

    @admin.display(description="Activo", boolean=True)
    def vigente(self, obj):
        """Check if DelegadoOperacion has at least one currently-valid period."""
        return obj.periodos.vigentes().exists()


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
class InspectorOperacionAdmin(ImportExportMixin, admin.ModelAdmin):
    """Standalone admin for InspectorOperacion with Excel import/export support."""

    list_display = ["inspector_nombre", "inspector_cip", "tipo_liquidacion", "numero_registro", "categoria", "vigente"]
    search_fields = [
        "inspector__perfil_ingeniero__nombres",
        "inspector__perfil_ingeniero__apellido_paterno",
        "numero_registro",
    ]
    list_filter = ["tipo_liquidacion", "categoria"]
    readonly_fields = ["created_at", "updated_at"]
    inlines = [InspectorOperacionPeriodoInline]
    resource_classes = [InspectorOperacionResource]

    @admin.display(description="Inspector", ordering="inspector__perfil_ingeniero__apellido_paterno")
    def inspector_nombre(self, obj):
        return obj.inspector.perfil_ingeniero.nombre_completo

    @admin.display(description="CIP", ordering="inspector__perfil_ingeniero__cip")
    def inspector_cip(self, obj):
        return obj.inspector.perfil_ingeniero.cip

    @admin.display(description="Activo", boolean=True)
    def vigente(self, obj):
        """Check if InspectorOperacion has at least one currently-valid period."""
        return obj.periodos.vigentes().exists()


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
