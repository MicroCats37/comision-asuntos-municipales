"""Proxy-based admin classes for LiquidacionGeneral filtered by tipo.

Each proxy model (LiquidacionEdificacionProxy, etc.) is a filtered view of
LiquidacionGeneral by tipo_liquidacion__codigo. Native inlines work because
the parent model is LiquidacionGeneral and the specific models (edificaciones,
etc.) have FK back to it.
"""

from django.contrib import admin
from django.db.models import Q

# Import from domain/models (re-exported via models.py)
from modules.liquidaciones.models import (
    LiquidacionGeneral,
    LiquidacionContacto,
    LiquidacionDocumentos,
    LiquidacionProyectista,
    LiquidacionDelegado,
    LiquidacionComprobante,
    # Specific models (for inlines)
    LiquidacionEdificacion,
    LiquidacionHabilitacionUrbana,
    LiquidacionMecanicaSuelos,
    LiquidacionTaludes,
    LiquidacionInspeccionObra,
    LiquidacionImpactoVial,
    # Calculation models (for inlines)
    LiquidacionPorMetroCuadrado,
    LiquidacionPorCategoriaVisitas,
    LiquidacionPorcentajeObra,
    LiquidacionPorcentajeObraDetalle,
    # Inspector
    LiquidacionInspector,
    # Proxy models
    LiquidacionEdificacionProxy,
    LiquidacionHabilitacionUrbanaProxy,
    LiquidacionMecanicaSuelosProxy,
    LiquidacionTaludesProxy,
    LiquidacionInspeccionObraProxy,
    LiquidacionImpactoVialProxy,
)
# LiquidacionCodigo imported directly from domain (not in models.py re-exports)
from modules.liquidaciones.domain.models.liquidacion.liquidacion_general.liquidacion import (
    LiquidacionCodigo,
)
from modules.liquidaciones.domain.constants import TipoLiquidacion


# =============================================================================
# ALWAYS-VISIBLE INLINES (attached to LiquidacionGeneral)
# =============================================================================


class LiquidacionDelegadoInline(admin.TabularInline):
    """Inline for LiquidacionDelegado (delegate assigned to this liquidation)."""

    model = LiquidacionDelegado
    extra = 1
    readonly_fields = ["created_at", "updated_at"]


class LiquidacionProyectistaInline(admin.TabularInline):
    """Inline for LiquidacionProyectista (proyectista on this liquidation)."""

    model = LiquidacionProyectista
    extra = 1
    readonly_fields = ["created_at", "updated_at"]


class LiquidacionContactoInline(admin.TabularInline):
    """Inline for LiquidacionContacto (contact on this liquidation)."""

    model = LiquidacionContacto
    extra = 1
    readonly_fields = ["created_at", "updated_at"]


class LiquidacionDocumentosInline(admin.TabularInline):
    """Inline for LiquidacionDocumentos (uploaded documents)."""

    model = LiquidacionDocumentos
    extra = 1
    readonly_fields = ["created_at", "updated_at"]


class LiquidacionComprobanteInline(admin.TabularInline):
    """Inline for LiquidacionComprobante (comprobantes de liquidación)."""

    model = LiquidacionComprobante
    extra = 1
    readonly_fields = ["created_at", "updated_at"]


# =============================================================================
# SPECIFIC MODEL INLINES (OneToOne extensions — conditional by tipo_liquidacion)
# =============================================================================


class LiquidacionEdificacionInline(admin.StackedInline):
    """Inline for LiquidacionEdificacion (OneToOne extension, EDIFICACION only)."""

    model = LiquidacionEdificacion
    extra = 0
    readonly_fields = ["created_at", "updated_at"]


class LiquidacionHabilitacionUrbanaInline(admin.StackedInline):
    """Inline for LiquidacionHabilitacionUrbana (OneToOne, HABILITACION_URBANA only)."""

    model = LiquidacionHabilitacionUrbana
    extra = 0
    readonly_fields = ["created_at", "updated_at"]


class LiquidacionMecanicaSuelosInline(admin.StackedInline):
    """Inline for LiquidacionMecanicaSuelos (OneToOne, MECANICA_SUELOS only)."""

    model = LiquidacionMecanicaSuelos
    extra = 0
    readonly_fields = ["created_at", "updated_at"]


class LiquidacionTaludesInline(admin.StackedInline):
    """Inline for LiquidacionTaludes (OneToOne, TALUDES only)."""

    model = LiquidacionTaludes
    extra = 0
    readonly_fields = ["created_at", "updated_at"]


class LiquidacionInspeccionObraInline(admin.StackedInline):
    """Inline for LiquidacionInspeccionObra (OneToOne, INSPECCION_OBRA only)."""

    model = LiquidacionInspeccionObra
    extra = 0
    readonly_fields = ["created_at", "updated_at"]


class LiquidacionImpactoVialInline(admin.StackedInline):
    """Inline for LiquidacionImpactoVial (OneToOne, IMPACTO_VIAL only)."""

    model = LiquidacionImpactoVial
    extra = 0
    readonly_fields = ["created_at", "updated_at"]


# =============================================================================
# CALCULATION MODEL INLINES (conditional by tipo_liquidacion)
# =============================================================================


class LiquidacionPorMetroCuadradoInline(admin.StackedInline):
    """Inline for LiquidacionPorMetroCuadrado (M2 calculation, HU/MS/Taludes/IV)."""

    model = LiquidacionPorMetroCuadrado
    extra = 0
    readonly_fields = ["created_at", "updated_at"]


class LiquidacionPorCategoriaVisitasInline(admin.StackedInline):
    """Inline for LiquidacionPorCategoriaVisitas (visits calculation, IO only)."""

    model = LiquidacionPorCategoriaVisitas
    extra = 0
    readonly_fields = ["created_at", "updated_at"]


class LiquidacionPorcentajeObraInline(admin.StackedInline):
    """Inline for LiquidacionPorcentajeObra (OneToOne, percentage calculation, Edificacion)."""

    model = LiquidacionPorcentajeObra
    extra = 0
    readonly_fields = ["created_at", "updated_at"]


class LiquidacionPorcentajeObraDetalleInline(admin.TabularInline):
    """Inline for LiquidacionPorcentajeObraDetalle (nested in LiquidacionPorcentajeObra)."""

    model = LiquidacionPorcentajeObraDetalle
    extra = 1
    readonly_fields = ["created_at", "updated_at"]


# =============================================================================
# ALWAYS-VISIBLE INLINES LIST
# =============================================================================


ALL_INLINES = [
    LiquidacionDelegadoInline,
    LiquidacionProyectistaInline,
    LiquidacionContactoInline,
    LiquidacionDocumentosInline,
    LiquidacionComprobanteInline,
]


# =============================================================================
# BASE ADMIN FOR PROXY MODELS
# Reusable base class that filters by tipo_liquidacion__codigo and provides
# all general fields from LiquidacionGeneral plus type-specific inlines.
# =============================================================================


class BaseLiquidacionProxyAdmin(admin.ModelAdmin):
    """
    Base admin for LiquidacionGeneral proxy models.

    Each subclass must define:
        tipo_codigo: The TipoLiquidacion enum value (e.g., TipoLiquidacion.EDIFICACION)
        specific_inline: The OneToOne extension inline class (e.g., LiquidacionEdificacionInline)
        calc_inline: The calculation inline class (e.g., LiquidacionPorcentajeObraInline) or None
        specific_related_name: The related_name on LiquidacionGeneral for the specific model
    """

    # General list display fields from LiquidacionGeneral
    list_display = [
        "numero",
        "expediente",
        "proyecto",
        "municipalidad",
        "estado",
        "total",
        "numero_revision",
        "fecha_registro",
    ]

    search_fields = [
        "expediente",
        "proyecto__nombre_propietario",
        "proyecto__entidad_numero_documento",
    ]

    list_filter = [
        "estado",
        "municipalidad",
        "fecha_registro",
        "legacy",
    ]

    fields = [
        "expediente",
        "proyecto",
        "municipalidad",
        "tipo_liquidacion",
        "estado",
        "numero_revision",
        "sub_total",
        "total",
        "fecha_registro",
        "observacion",
        "retencion",
        "legacy",
        "created_at",
        "updated_at",
    ]

    readonly_fields = [
        "proyecto",
        "municipalidad",
        "tipo_liquidacion",
        "total",
        "sub_total",
        "fecha_registro",
        "legacy",
        "created_at",
        "updated_at",
    ]

    filter_horizontal = []

    # Disable expensive full count query in Django admin changelist.
    # The filtered proxy queryset makes a precise count cost-prohibitive for large tables.
    show_full_result_count = False

    def get_queryset(self, request):
        """Filter by tipo_liquidacion__codigo and optimize with select_related."""
        qs = super().get_queryset(request)
        qs = qs.filter(tipo_liquidacion__codigo=self.tipo_codigo)
        # Dynamically add specific related name to avoid N+1 on numero() display method.
        related_name = getattr(self, "specific_related_name", None)
        if related_name:
            qs = qs.select_related(
                "proyecto",
                "municipalidad",
                "tipo_liquidacion",
                "usuario_creador",
                related_name,
            )
        else:
            qs = qs.select_related(
                "proyecto",
                "municipalidad",
                "tipo_liquidacion",
                "usuario_creador",
            )
        return qs

    # ── Display methods ────────────────────────────────────────────

    def numero(self, obj):
        """Display numero from the specific related model."""
        related_name = getattr(self, "specific_related_name", None)
        if related_name and hasattr(obj, related_name):
            specific = getattr(obj, related_name, None)
            if specific and hasattr(specific, "numero"):
                return specific.numero
        return "-"

    numero.short_description = "N°"
    # Prevent admin from sorting by this column — it would re-introduce the JOIN.
    numero.admin_order_field = None

    def expediente(self, obj):
        return obj.expediente or "-"

    expediente.short_description = "Expediente"

    def proyecto(self, obj):
        return str(obj.proyecto) if obj.proyecto else "-"

    proyecto.short_description = "Proyecto"

    def municipalidad(self, obj):
        return str(obj.municipalidad) if obj.municipalidad else "-"

    municipalidad.short_description = "Municipalidad"

    def estado(self, obj):
        return obj.estado or "-"

    estado.short_description = "Estado"

    def total(self, obj):
        if obj.total is None:
            return "-"
        return f"S/ {obj.total:,.2f}"

    total.short_description = "Total"

    def numero_revision(self, obj):
        return obj.numero_revision or "-"

    numero_revision.short_description = "Rev."

    def fecha_registro(self, obj):
        if not obj.fecha_registro:
            return "-"
        return obj.fecha_registro.strftime("%d/%m/%Y")

    fecha_registro.short_description = "Fecha"

    # ── Inlines ───────────────────────────────────────────────────

    def get_inlines(self, request, obj):
        """Return only the specific identity inline and its calculation inline."""
        inlines = []
        if obj is not None:
            inlines.append(self.specific_inline)
            if self.calc_inline is not None:
                inlines.append(self.calc_inline)
        return inlines

    # ── Auto-populate especialidades_revisadas on creation ───────

    def save_model(self, request, obj, form, change):
        """Auto-populate especialidades_revisadas when empty and tipo_liquidacion is set."""
        from datetime import date
        from modules.liquidaciones.domain.models.liquidacion.liquidacion_general.liquidacion import (
            LiquidacionEspecialidadDisponibles,
        )

        super().save_model(request, obj, form, change)

        # Only auto-populate on creation (not on edit), and only if empty
        if (
            not change
            and not obj.especialidades_revisadas.exists()
            and obj.tipo_liquidacion_id
        ):
            today = date.today()
            disponibles = LiquidacionEspecialidadDisponibles.objects.filter(
                tipo_liquidacion=obj.tipo_liquidacion_id,
                activo=True,
                periodo_inicio__lte=today,
            ).filter(Q(periodo_fin__isnull=True) | Q(periodo_fin__gte=today))
            for disp in disponibles:
                obj.especialidades_revisadas.add(disp.especialidad)


# =============================================================================
# PROXY ADMIN CLASSES
# =============================================================================


@admin.register(LiquidacionEdificacionProxy)
class LiquidacionEdificacionProxyAdmin(BaseLiquidacionProxyAdmin):
    """Admin for LiquidacionGeneral filtered to Edificación type."""

    tipo_codigo = TipoLiquidacion.EDIFICACION
    specific_inline = LiquidacionEdificacionInline
    calc_inline = LiquidacionPorcentajeObraInline
    specific_related_name = "edificaciones"

    list_display = BaseLiquidacionProxyAdmin.list_display + ["tipo_tramite_list"]

    def tipo_tramite_list(self, obj):
        calc = getattr(obj, "liquidacion_porcentaje_obra", None)
        if not calc:
            return "-"
        return calc.tipo_tramite if calc and calc.tipo_tramite else "-"

    tipo_tramite_list.short_description = "Tipo Trámite"


@admin.register(LiquidacionHabilitacionUrbanaProxy)
class LiquidacionHabilitacionUrbanaProxyAdmin(BaseLiquidacionProxyAdmin):
    """Admin for LiquidacionGeneral filtered to Habilitación Urbana type."""

    tipo_codigo = TipoLiquidacion.HABILITACION_URBANA
    specific_inline = LiquidacionHabilitacionUrbanaInline
    calc_inline = LiquidacionPorMetroCuadradoInline
    specific_related_name = "habilitacion_urbana"

    list_display = BaseLiquidacionProxyAdmin.list_display + ["area_list"]

    def area_list(self, obj):
        calc = getattr(obj, "liquidacion_m2", None)
        if not calc:
            return "-"
        calc = calc.first()
        if not calc:
            return "-"
        return f"{calc.area_m2:,.2f} m²" if calc.area_m2 else "-"

    area_list.short_description = "Área"


@admin.register(LiquidacionMecanicaSuelosProxy)
class LiquidacionMecanicaSuelosProxyAdmin(BaseLiquidacionProxyAdmin):
    """Admin for LiquidacionGeneral filtered to Mecánica de Suelos type."""

    tipo_codigo = TipoLiquidacion.MECANICA_SUELOS
    specific_inline = LiquidacionMecanicaSuelosInline
    calc_inline = LiquidacionPorMetroCuadradoInline
    specific_related_name = "mecanica_suelos"

    list_display = BaseLiquidacionProxyAdmin.list_display + ["area_list"]

    def area_list(self, obj):
        calc = getattr(obj, "liquidacion_m2", None)
        if not calc:
            return "-"
        calc = calc.first()
        if not calc:
            return "-"
        return f"{calc.area_m2:,.2f} m²" if calc.area_m2 else "-"

    area_list.short_description = "Área"


@admin.register(LiquidacionTaludesProxy)
class LiquidacionTaludesProxyAdmin(BaseLiquidacionProxyAdmin):
    """Admin for LiquidacionGeneral filtered to Taludes type."""

    tipo_codigo = TipoLiquidacion.TALUDES
    specific_inline = LiquidacionTaludesInline
    calc_inline = LiquidacionPorcentajeObraInline
    specific_related_name = "taludes"

    list_display = BaseLiquidacionProxyAdmin.list_display + ["tipo_tramite_list"]

    def tipo_tramite_list(self, obj):
        calc = getattr(obj, "liquidacion_porcentaje_obra", None)
        if not calc:
            return "-"
        return calc.tipo_tramite if calc.tipo_tramite else "-"

    tipo_tramite_list.short_description = "Tipo Trámite"


@admin.register(LiquidacionInspeccionObraProxy)
class LiquidacionInspeccionObraProxyAdmin(BaseLiquidacionProxyAdmin):
    """Admin for LiquidacionGeneral filtered to Inspección de Obra type."""

    tipo_codigo = TipoLiquidacion.INSPECCION_OBRA
    specific_inline = LiquidacionInspeccionObraInline
    calc_inline = LiquidacionPorCategoriaVisitasInline
    specific_related_name = "inspeccion_obra"

    list_display = BaseLiquidacionProxyAdmin.list_display + ["categoria_list", "visitas_list"]

    def categoria_list(self, obj):
        calc = getattr(obj, "liquidacion_visitas", None)
        if not calc:
            return "-"
        calc = calc.first()
        if not calc:
            return "-"
        return calc.categoria if calc.categoria else "-"

    categoria_list.short_description = "Categoría"

    def visitas_list(self, obj):
        calc = getattr(obj, "liquidacion_visitas", None)
        if not calc:
            return "-"
        calc = calc.first()
        if not calc:
            return "-"
        return str(calc.cantidad_visitas) if calc.cantidad_visitas else "-"

    visitas_list.short_description = "Visitas"


@admin.register(LiquidacionImpactoVialProxy)
class LiquidacionImpactoVialProxyAdmin(BaseLiquidacionProxyAdmin):
    """Admin for LiquidacionGeneral filtered to Impacto Vial type."""

    tipo_codigo = TipoLiquidacion.IMPACTO_VIAL
    specific_inline = LiquidacionImpactoVialInline
    calc_inline = LiquidacionPorcentajeObraInline
    specific_related_name = "impacto_vial"

    list_display = BaseLiquidacionProxyAdmin.list_display + ["tipo_tramite_list"]

    def tipo_tramite_list(self, obj):
        calc = getattr(obj, "liquidacion_porcentaje_obra", None)
        if not calc:
            return "-"
        return calc.tipo_tramite if calc.tipo_tramite else "-"

    tipo_tramite_list.short_description = "Tipo Trámite"


# =============================================================================
# LIQUIDACIONGENERAL ADMIN (general view — all types)
# =============================================================================


@admin.register(LiquidacionGeneral)
class LiquidacionGeneralAdmin(admin.ModelAdmin):
    """
    Admin for LiquidacionGeneral (central liquidation model).

    Uses conditional get_inlines() to show only relevant inlines per tipo_liquidacion.
    """

    list_display = [
        "id",
        "proyecto",
        "municipalidad",
        "tipo_liquidacion",
        "estado",
        "total",
        "legacy",
        "fecha_registro",
    ]
    search_fields = [
        "proyecto__nombre_propietario",
        "expediente",
        "proyecto__entidad_numero_documento",
    ]
    list_filter = ["estado", "tipo_liquidacion", "municipalidad", "fecha_registro", "legacy"]
    readonly_fields = [
        "total",
        "sub_total",
        "fecha_registro",
        "igv_snapshot",
        "uit_snapshot",
        "legacy",
        "created_at",
        "updated_at",
    ]

    filter_horizontal = ["especialidades_revisadas"]

    def save_model(self, request, obj, form, change):
        """
        Auto-populate especialidades_revisadas from LiquidacionEspecialidadDisponibles
        when the field is empty and tipo_liquidacion is set.
        """
        from datetime import date
        from modules.liquidaciones.domain.models.liquidacion.liquidacion_general.liquidacion import (
            LiquidacionEspecialidadDisponibles,
        )

        super().save_model(request, obj, form, change)

        if not change and not obj.especialidades_revisadas.exists() and obj.tipo_liquidacion_id:
            today = date.today()
            disponibles = LiquidacionEspecialidadDisponibles.objects.filter(
                tipo_liquidacion=obj.tipo_liquidacion_id,
                activo=True,
                periodo_inicio__lte=today,
            ).filter(Q(periodo_fin__isnull=True) | Q(periodo_fin__gte=today))
            for disp in disponibles:
                obj.especialidades_revisadas.add(disp.especialidad)

    def get_inlines(self, request, obj):
        """
        Return conditional inlines based on tipo_liquidacion.
        """
        if obj is None:
            return ALL_INLINES

        tipo = obj.tipo_liquidacion.codigo if obj.tipo_liquidacion else None

        inlines = list(ALL_INLINES)

        if tipo == TipoLiquidacion.EDIFICACION:
            inlines.append(LiquidacionEdificacionInline)
            inlines.append(LiquidacionPorcentajeObraInline)
        elif tipo == TipoLiquidacion.HABILITACION_URBANA:
            inlines.append(LiquidacionHabilitacionUrbanaInline)
            inlines.append(LiquidacionPorMetroCuadradoInline)
        elif tipo == TipoLiquidacion.MECANICA_SUELOS:
            inlines.append(LiquidacionMecanicaSuelosInline)
            inlines.append(LiquidacionPorMetroCuadradoInline)
        elif tipo == TipoLiquidacion.TALUDES:
            inlines.append(LiquidacionTaludesInline)
            inlines.append(LiquidacionPorMetroCuadradoInline)
        elif tipo == TipoLiquidacion.INSPECCION_OBRA:
            inlines.append(LiquidacionInspeccionObraInline)
            inlines.append(LiquidacionPorCategoriaVisitasInline)
        elif tipo == TipoLiquidacion.IMPACTO_VIAL:
            inlines.append(LiquidacionImpactoVialInline)
            inlines.append(LiquidacionPorMetroCuadradoInline)

        return inlines


# =============================================================================
# LIQUIDACIONCODIGO ADMIN (hidden lookup table)
# =============================================================================


@admin.register(LiquidacionCodigo)
class LiquidacionCodigoAdmin(admin.ModelAdmin):
    """
    Admin for LiquidacionCodigo (account codes by liquidation type).

    NOTE: Hidden from sidebar (show_in_index=False) because it is a configuration
    lookup table used only when setting up tipo_liquidacion codes, not for daily work.
    Access via TipoLiquidacion admin inlines instead.
    """

    list_display = ["tipo_liquidacion", "codigo_cta"]
    search_fields = ["tipo_liquidacion__nombre", "codigo_cta"]
    list_filter = ["tipo_liquidacion"]
    readonly_fields = ["created_at", "updated_at"]

    def has_module_permission(self, request):
        """Hide from admin sidebar - only accessible via inlines or direct URL."""
        return False


# =============================================================================
# HIDDEN WRAPPER ADMINS
# Registered but hidden from sidebar — use proxy admins for entry points.
# The wrapper admins (LiquidacionEdificacionAdmin, etc.) are hidden from the
# sidebar to avoid duplicate sections. They remain registered for backward
# compatibility with existing URLs.
# =============================================================================


class HiddenWrapperAdmin(admin.ModelAdmin):
    """Base for wrapper admins that are hidden from sidebar."""

    def has_module_permission(self, request):
        """Hide from sidebar index."""
        return False


# Register wrapper admins (specific models) as hidden
admin.site.register(LiquidacionEdificacion, HiddenWrapperAdmin)
admin.site.register(LiquidacionHabilitacionUrbana, HiddenWrapperAdmin)
admin.site.register(LiquidacionMecanicaSuelos, HiddenWrapperAdmin)
admin.site.register(LiquidacionTaludes, HiddenWrapperAdmin)
admin.site.register(LiquidacionInspeccionObra, HiddenWrapperAdmin)
admin.site.register(LiquidacionImpactoVial, HiddenWrapperAdmin)


# =============================================================================
# LIQUIDACIONINSPECTOR ADMIN
# =============================================================================


@admin.register(LiquidacionInspector)
class LiquidacionInspectorAdmin(admin.ModelAdmin):
    """Admin for LiquidacionInspector (inspector associated to IO)."""

    list_display = ["liquidacion", "inspector", "dictamen_revision", "created_at"]
    search_fields = [
        "liquidacion__liquidacion__expediente",
        "inspector__perfil_ingeniero__nombres",
        "inspector__perfil_ingeniero__apellido_paterno",
    ]
    list_filter = ["dictamen_revision"]
    readonly_fields = ["created_at", "updated_at"]
