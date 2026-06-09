"""Admin — minimal registration for liquidaciones models."""

from django.contrib import admin
from django.utils.html import format_html
from django.templatetags.static import static
from nested_admin import NestedModelAdmin, NestedTabularInline
from simple_history.admin import SimpleHistoryAdmin

from .models import Delegado, Proyectista, Liquidacion, Revision, RevisionDelegado, Igv, Uit


class RevisionDelegadoInline(NestedTabularInline):
    """Inline para gestionar delegados de una revisión — nested dentro de RevisionInline."""

    model = RevisionDelegado
    fk_name = "revision"
    fields = ["delegado"]
    extra = 1
    autocomplete_fields = ["delegado"]
    ordering = ["delegado__perfil_ingeniero__apellido_paterno"]


class RevisionInline(NestedTabularInline):
    """Inline para gestionar revisiones desde la pantalla de Liquidacion."""

    model = Revision
    fk_name = "liquidacion"
    fields = ["numero", "delegados_resumen", "created_at"]
    extra = 1
    readonly_fields = ["numero", "delegados_resumen", "created_at"]
    ordering = ["numero"]
    show_change_link = True
    inlines = [RevisionDelegadoInline]

    def delegados_resumen(self, obj):
        """Muestra un resumen corto de delegados asociados a esta revisión."""
        rd_count = obj.revision_delegados.count()
        if rd_count == 0:
            return "Sin delegados"
        rd_list = obj.revision_delegados.select_related(
            "delegado__perfil_ingeniero"
        ).order_by("delegado__perfil_ingeniero__apellido_paterno")[:3]
        nombres = [rd.delegado.perfil_ingeniero.apellido_paterno for rd in rd_list]
        if rd_count > 3:
            return f"{', '.join(nombres)} (+{rd_count - 3})"
        return f"{', '.join(nombres)}"
    delegados_resumen.short_description = "Delegados"


@admin.register(Delegado)
class DelegadoAdmin(SimpleHistoryAdmin):
    list_display = ["perfil_ingeniero", "municipalidad", "especialidad", "banco", "status", "distrito"]
    list_filter = ["status", "municipalidad", "banco"]
    search_fields = [
        "perfil_ingeniero__nombres",
        "perfil_ingeniero__apellido_paterno",
        "perfil_ingeniero__apellido_materno",
        "perfil_ingeniero__cip",
        "especialidad",
        "municipalidad__nombre",
        "banco__nombre",
    ]
    readonly_fields = ["created_at", "updated_at"]
    autocomplete_fields = ["perfil_ingeniero", "municipalidad", "banco"]
    ordering = ["perfil_ingeniero__apellido_paterno", "perfil_ingeniero__apellido_materno"]


@admin.register(Proyectista)
class ProyectistaAdmin(SimpleHistoryAdmin):
    list_display = ["nombre"]
    search_fields = ["nombre"]
    readonly_fields = ["created_at", "updated_at"]
    ordering = ["nombre"]


@admin.register(Liquidacion)
class LiquidacionAdmin(NestedModelAdmin, SimpleHistoryAdmin):
    """Admin para Liquidacion con soporte nested inlines.

    Herencia resuelta: NestedModelAdmin primero para que los inlines anidados
    (Revision -> RevisionDelegado) funcionen correctamente, seguido de
    SimpleHistoryAdmin para el seguimiento histórico.
    """
    list_display = [
        "proyectista",
        "empresa_razon_social_display",
        "empresa_ruc_display",
        "igv_porcentaje_display",
        "uit_porcentaje_display",
        "valor_obra",
        "monto_igv_display",
        "monto_uit_display",
        "total_calculado_display",
        "created_at",
    ]
    list_filter = ["empresa", "igv", "uit", "created_at"]
    search_fields = [
        "proyectista__nombre",
        "empresa__razon_social",
        "empresa__ruc",
    ]
    readonly_fields = [
        "created_at",
        "updated_at",
        # ─── Detalle empresa (readonly) ───
        "empresa_razon_social_display",
        "empresa_ruc_display",
        "empresa_direccion_display",
        # ─── Detalle proyectista (readonly) ───
        "proyectista_nombre_display",
        # ─── Detalle IGV/UIT (readonly) ───
        "igv_detalle_display",
        "uit_detalle_display",
        # ─── Cálculos visuales (readonly) ───
        "monto_igv_display",
        "monto_uit_display",
        "total_calculado_display",
        # ─── Referencia visual (readonly) ───
        "referencia_visual_legacy",
    ]
    autocomplete_fields = ["proyectista", "empresa", "igv", "uit"]
    ordering = ["-created_at"]
    inlines = [RevisionInline]

    # ─── Métodos de visualización ───────────────────────────────────────────────

    def empresa_razon_social_display(self, obj):
        if obj.empresa:
            return obj.empresa.razon_social
        return "-"
    empresa_razon_social_display.short_description = "Razón Social"

    def empresa_ruc_display(self, obj):
        if obj.empresa:
            return obj.empresa.ruc
        return "-"
    empresa_ruc_display.short_description = "RUC"

    def empresa_direccion_display(self, obj):
        if obj.empresa and obj.empresa.direccion:
            return obj.empresa.direccion
        return "-"
    empresa_direccion_display.short_description = "Dirección"

    def proyectista_nombre_display(self, obj):
        if obj.proyectista:
            return obj.proyectista.nombre
        return "-"
    proyectista_nombre_display.short_description = "Nombre del Proyectista"

    def igv_porcentaje_display(self, obj):
        if obj.igv:
            return f"{obj.igv.porcentaje}%"
        return "-"
    igv_porcentaje_display.short_description = "IGV %"

    def uit_porcentaje_display(self, obj):
        if obj.uit:
            return f"{obj.uit.porcentaje}%"
        return "-"
    uit_porcentaje_display.short_description = "UIT %"

    def igv_detalle_display(self, obj):
        if not obj.igv:
            return "-"
        fin = obj.igv.fecha_fin.strftime("%d/%m/%Y") if obj.igv.fecha_fin else "vigente"
        return f"IGV {obj.igv.porcentaje}% | Desde: {obj.igv.fecha_inicio.strftime('%d/%m/%Y')} | Hasta: {fin}"
    igv_detalle_display.short_description = "Detalle IGV"

    def uit_detalle_display(self, obj):
        if not obj.uit:
            return "-"
        fin = obj.uit.fecha_fin.strftime("%d/%m/%Y") if obj.uit.fecha_fin else "vigente"
        return f"UIT {obj.uit.porcentaje}% | Desde: {obj.uit.fecha_inicio.strftime('%d/%m/%Y')} | Hasta: {fin}"
    uit_detalle_display.short_description = "Detalle UIT"

    def monto_igv_display(self, obj):
        return f"S/ {obj.monto_igv:,.2f}"
    monto_igv_display.short_description = "Monto IGV"

    def monto_uit_display(self, obj):
        return f"S/ {obj.monto_uit:,.2f}"
    monto_uit_display.short_description = "Monto UIT"

    def total_calculado_display(self, obj):
        return f"S/ {obj.total_calculado:,.2f}"
    total_calculado_display.short_description = "Total Calculado"

    def delegado_display(self, obj):
        primera = obj.revisiones.order_by("numero").first()
        if primera:
            rd = primera.revision_delegados.select_related("delegado").first()
            if rd:
                return str(rd.delegado)
        return "-"
    delegado_display.short_description = "Delegado"

    # ─── Referencia visual ──────────────────────────────────────────────────────

    def referencia_visual_legacy(self, obj):
        """Muestra imagen de referencia si está disponible en static/admin/liquidaciones/."""
        image_path = "images/referencia-liquidacion.png"
        # Verificar si el archivo existe usando STATIC_URL (solo funciona en DEBUG)
        from django.conf import settings
        if settings.DEBUG:
            from django.contrib.staticfiles.finders import find
            if find(image_path):
                return format_html(
                    '<img src="{}" alt="Referencia visual" style="max-width:600px; border:1px solid #ccc;" />',
                    static(image_path),
                )
        return format_html(
            '<span style="color:#999; font-style:italic;">'
            'Colocar imagen en backend/static/images/referencia-liquidacion.png'
            '</span>'
        )
    referencia_visual_legacy.short_description = "Referencia visual"

    # ─── Fieldsets actualizado ────────────────────────────────────────────────

    fieldsets = (
        # ── Sección 1: Datos Principales ──
        (
            "Datos Principales",
            {
                "fields": (
                    "proyectista",
                    "empresa",
                    "valor_obra",
                    "derecho_minimo",
                    "porcentaje",
                ),
            },
        ),
        # ── Sección 2: Detalle de Empresa y Proyectista ──
        (
            "Detalle de Empresa y Proyectista",
            {
                "fields": (
                    "empresa_razon_social_display",
                    "empresa_ruc_display",
                    "empresa_direccion_display",
                    "proyectista_nombre_display",
                ),
                "description": "Información de referencia de la empresa y el proyectista asociado.",
            },
        ),
        # ── Sección 3: Parámetros de Cálculo (IGV / UIT) ──
        (
            "Parámetros de Cálculo",
            {
                "fields": (
                    "igv",
                    "uit",
                    "igv_detalle_display",
                    "uit_detalle_display",
                ),
                "description": "Parámetros fiscales con su vigencia.",
            },
        ),
        # ── Sección 4: Cálculos Visuales ──
        (
            "Cálculos Visuales",
            {
                "fields": (
                    "monto_igv_display",
                    "monto_uit_display",
                    "total_calculado_display",
                ),
                "description": "Montos calculados en base al valor de obra y los parámetros fiscales.",
            },
        ),
        # ── Sección 5: Referencia visual ──
        (
            "Referencia visual",
            {
                "fields": ("referencia_visual_legacy",),
                "description": "Imagen de referencia para flujo de trabajo.",
            },
        ),
    )


@admin.register(Revision)
class RevisionAdmin(SimpleHistoryAdmin):
    list_display = ["numero", "liquidacion", "delegados_display", "created_at"]
    list_filter = ["liquidacion__empresa"]
    search_fields = [
        "liquidacion__proyectista__nombre",
        "liquidacion__empresa__razon_social",
    ]
    readonly_fields = ["created_at", "updated_at", "delegados_display"]
    autocomplete_fields = ["liquidacion"]
    ordering = ["liquidacion", "numero"]
    inlines = [RevisionDelegadoInline]

    def delegados_display(self, obj):
        """Resume los delegados asociados a esta revisión como texto legible."""
        rd_list = obj.revision_delegados.select_related(
            "delegado__perfil_ingeniero"
        ).order_by("delegado__perfil_ingeniero__apellido_paterno")[:5]
        if not rd_list:
            return "-"
        nombres = [str(rd.delegado) for rd in rd_list]
        total = obj.revision_delegados.count()
        if total > 5:
            return ", ".join(nombres) + f" (+{total - 5} más)"
        return ", ".join(nombres)
    delegados_display.short_description = "Delegados"


@admin.register(RevisionDelegado)
class RevisionDelegadoAdmin(SimpleHistoryAdmin):
    list_display = ["revision", "delegado", "created_at"]
    list_filter = ["delegado__municipalidad", "delegado__especialidad"]
    search_fields = [
        "revision__liquidacion__proyectista__nombre",
        "revision__liquidacion__empresa__razon_social",
        "delegado__perfil_ingeniero__nombres",
        "delegado__perfil_ingeniero__apellido_paterno",
        "delegado__perfil_ingeniero__apellido_materno",
    ]
    readonly_fields = ["created_at", "updated_at"]
    autocomplete_fields = ["revision", "delegado"]
    ordering = ["revision", "delegado"]


@admin.register(Igv)
class IgvAdmin(SimpleHistoryAdmin):
    list_display = ["porcentaje", "fecha_inicio", "fecha_fin"]
    list_filter = ["fecha_inicio"]
    search_fields = ["porcentaje"]
    readonly_fields = ["created_at", "updated_at"]
    ordering = ["-fecha_inicio"]


@admin.register(Uit)
class UitAdmin(SimpleHistoryAdmin):
    list_display = ["porcentaje", "fecha_inicio", "fecha_fin"]
    list_filter = ["fecha_inicio"]
    search_fields = ["porcentaje"]
    readonly_fields = ["created_at", "updated_at"]
    ordering = ["-fecha_inicio"]