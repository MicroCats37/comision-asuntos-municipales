"""LiquidacionGeneral and LiquidacionCodigo admin classes."""

from django.contrib import admin

# Import from specific submodule files (not all are re-exported via domain/models/__init__.py)
from modules.liquidaciones.domain.models.liquidacion.liquidacion_general.liquidacion import (
    LiquidacionGeneral,
    LiquidacionCodigo,
    LiquidacionContacto,
    LiquidacionDocumentos,
    LiquidacionProyectista,
)
from modules.liquidaciones.domain.models.delegado import (
    LiquidacionDelegado,
)
from modules.liquidaciones.domain.models.inspector import (
    LiquidacionInspector,
)
from modules.liquidaciones.domain.models.liquidacion.liquidacion_especifico.liquidacion_edificaciones import (
    LiquidacionEdificacion,
)
from modules.liquidaciones.domain.models.liquidacion.liquidacion_especifico.liquidacion_habilitacion_urbana import (
    LiquidacionHabilitacionUrbana,
)
from modules.liquidaciones.domain.models.liquidacion.liquidacion_especifico.liquidacion_mecanica_suelos import (
    LiquidacionMecanicaSuelos,
)
from modules.liquidaciones.domain.models.liquidacion.liquidacion_especifico.liquidacion_taludes import (
    LiquidacionTaludes,
)
from modules.liquidaciones.domain.models.liquidacion.liquidacion_especifico.liquidacion_inspeccion_obra import (
    LiquidacionInspeccionObra,
)
from modules.liquidaciones.domain.models.liquidacion.liquidacion_especifico.liquidacion_impacto_vial import (
    LiquidacionImpactoVial,
)
from modules.liquidaciones.domain.models.liquidacion.liquidacion_tipo.liquidacion_tipo import (
    LiquidacionPorMetroCuadrado,
    LiquidacionPorCategoriaVisitas,
    LiquidacionPorcentajeObra,
    LiquidacionPorcentajeObraDetalle,
)
from modules.liquidaciones.domain.constants import TipoLiquidacion


# ── Always-visible inlines ───────────────────────────────────────


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


# ── OneToOne extension inlines (conditional by tipo_liquidacion) ─


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


# ── Calculation model inlines (conditional by tipo_liquidacion) ──


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


# ── Always-visible inlines list ─────────────────────────────────


ALL_INLINES = [
    LiquidacionDelegadoInline,
    LiquidacionProyectistaInline,
    LiquidacionContactoInline,
    LiquidacionDocumentosInline,
]


@admin.register(LiquidacionGeneral)
class LiquidacionGeneralAdmin(admin.ModelAdmin):
    """
    Admin for LiquidacionGeneral (central liquidation model).

    Uses conditional get_inlines() to show only relevant inlines per tipo_liquidacion.
    This prevents the "forced tables" problem where all 15+ inlines would appear
    regardless of the liquidation type.
    """

    list_display = [
        "id",
        "proyecto",
        "municipalidad",
        "tipo_liquidacion",
        "estado",
        "total",
        "fecha_registro",
    ]
    search_fields = [
        "proyecto__denominacion",
        "expediente",
        "proyecto__entidad_numero_documento",
    ]
    list_filter = ["estado", "tipo_liquidacion", "municipalidad", "fecha_registro"]
    readonly_fields = [
        "total",
        "sub_total",
        "fecha_registro",
        "igv_snapshot",
        "uit_snapshot",
        "created_at",
        "updated_at",
    ]

    filter_horizontal = ["especialidades_revisadas", "liquidaciones_previas"]

    def get_inlines(self, request, obj):
        """
        Return conditional inlines based on tipo_liquidacion.

        Strategy:
        - Always show ALL_INLINES (delegado, inspector, proyectista, contacto, documentos)
        - Add type-specific OneToOne extension inline
        - Add type-specific calculation inline (when applicable)
        """
        if obj is None:
            # During add view, show no conditional inlines (no tipo_liquidacion selected yet)
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


@admin.register(LiquidacionCodigo)
class LiquidacionCodigoAdmin(admin.ModelAdmin):
    """Admin for LiquidacionCodigo (account codes by liquidation type)."""

    list_display = ["tipo_liquidacion", "codigo_cta"]
    search_fields = ["tipo_liquidacion__nombre", "codigo_cta"]
    list_filter = ["tipo_liquidacion"]
    readonly_fields = ["created_at", "updated_at"]


@admin.register(LiquidacionInspector)
class LiquidacionInspectorAdmin(admin.ModelAdmin):
    """Admin for LiquidacionInspector (inspector asociado a una IO).

    La IO es una liquidación especial: el inspector se asocia al tipo
    (LiquidacionInspeccionObra), no a la LiquidacionGeneral.
    """

    list_display = ["liquidacion", "inspector", "dictamen_revision", "created_at"]
    search_fields = [
        "liquidacion__liquidacion__expediente",
        "inspector__perfil_ingeniero__nombres",
        "inspector__perfil_ingeniero__apellido_paterno",
    ]
    list_filter = ["dictamen_revision"]
    readonly_fields = ["created_at", "updated_at"]
