"""
Typed legacy registration schemas — composición de bloques para las seis rutas
`POST /liquidaciones/{tipo}/nueva-liquidacion/legacy`.

Filosofía (contrato SCHEMA_DRY_INTENTION): COMPOSICIÓN sobre herencia. Cada
input legacy se compone de TRES bloques:

1. Bloque GENERAL      → `LegacyGeneralIn` (municipalidad, expediente,
   observacion, proyecto, contacto, denominación de proyecto).
2. Bloque IDENTIDAD    → `LegacyRegistroMixin` (`numero` + `fecha_registro`),
   la identidad histórica explícita del registro.
3. Bloque ESPECÍFICO   → el bloque de cálculo del tipo, reutilizando el bloque
   vigente de cada motor (PO / M2 / Visitas) en su versión ESTRICTA.

Todos los bloques legacy declaran `extra="forbid"`. Consecuencia directa:
- `legacy` (flag controlado por el servidor) → 422
- `cotizacion_legacy` (totales manuales / bypass de cálculo) → 422
- `uit_valor_override` / `uit_id_override` (bypass de valores financieros) → 422
- cualquier otro campo desconocido → 422

El flag `legacy` NO se acepta en el payload: la RUTA es el discriminador y el
servidor asigna `legacy=True`.

Los bloques compartidos por el camino normal (`ProyectoCotizarSchema`,
`ContactoInlineSchema`) NO se modifican: el camino normal conserva su
comportamiento actual (no rechaza campos desconocidos).
"""
import uuid
from datetime import date
from decimal import Decimal
from typing import List, Optional, Union

from core.types import BaseSchema
from ninja import Field
from pydantic import ConfigDict

from modules.liquidaciones.presentation.schemas.liquidacion_general.general_schemas import (
    ContactoInlineSchema,
    NumeroRevisionRequeridoMixin,
    ProyectoCotizarSchema,
)
from modules.liquidaciones.presentation.schemas.liquidacion_especifico.liquidacion_edificaciones_schemas import (
    LiquidacionEdificacionesEstrategiaIn,
)


# ── Bloque 1 — IDENTIDAD histórica (numero + fecha_registro) ─────────────────


class LegacyRegistroMixin(BaseSchema):
    """
    Identidad histórica explícita del registro legacy.

    `numero` es informativo y REPETIBLE: se persiste tal cual, sin unicidad,
    sin validación de duplicados y sin respuesta 409.

    `fecha_registro` gobierna TODA la resolución histórica (IGV, UIT, tarifas
    y derechos). Es obligatoria: el registro legacy siempre tiene fecha.
    """

    model_config = ConfigDict(extra="forbid")

    numero: int = Field(
        ...,
        ge=1,
        le=2147483647,
        description="Número explícito del registro histórico. Informativo y repetible. "
        "Cota superior = PositiveIntegerField del wrapper específico.",
    )
    fecha_registro: date = Field(
        ...,
        description="Fecha efectiva del registro. Gobierna la resolución histórica de IGV, UIT, tarifas y derechos.",
    )


# ── Bloque 2 — GENERAL ──────────────────────────────────────────────────────


class LegacyGeneralIn(BaseSchema):
    """
    Bloque general del registro legacy.

    Replica el bloque general vigente (`LiquidacionGeneralRevisionIn`) en su
    versión estricta: mismos campos, sin `fecha_registro` (esa vive en el
    bloque de identidad) y sin `descripcion_legacy`/`retencion` (seams del
    importador, no del registro manual).
    """

    model_config = ConfigDict(extra="forbid")

    municipalidad_id: uuid.UUID = Field(..., description="ID de la municipalidad")
    expediente: Optional[str] = Field(None, description="Número de expediente")
    observacion: Optional[str] = Field(None, description="Observación opcional")
    denominacion_de_proyecto: Optional[str] = Field(
        None, description="Denominación del proyecto (opcional)"
    )
    proyecto: ProyectoCotizarSchema = Field(..., description="Datos del proyecto")
    contacto: Optional[ContactoInlineSchema] = Field(
        None, description="Contacto principal (se crea inline)"
    )


# ── Bloque 3 — ESPECÍFICO por motor ─────────────────────────────────────────


class LegacyPorcentajeObraDatosIn(BaseSchema):
    """Datos del motor PorcentajeObra en versión estricta (sin extras)."""

    model_config = ConfigDict(extra="forbid")

    valor_declarado: Decimal = Field(
        ...,
        le=Decimal("9999999999.99"),
        max_digits=12,
        decimal_places=2,
        description="Valor declarado máximo compatible con DecimalField(max_digits=12, decimal_places=2).",
    )
    tipo_tramite: Optional[str] = None


class LegacyPorcentajeObraTarifaIn(BaseSchema):
    """Tarifa PO en versión estricta (sin extras)."""

    model_config = ConfigDict(extra="forbid")

    tarifa_porcentaje_obra_id: uuid.UUID
    especialidad_id: uuid.UUID


class LegacyPorcentajeObraIn(BaseSchema):
    """
    Bloque específico PorcentajeObra en versión estricta.

    Es el bloque vigente (`LiquidacionPorcentajeObraIn`) con `extra="forbid"`
    en los tres niveles: no se aceptan totales manuales ni overrides.
    """

    model_config = ConfigDict(extra="forbid")

    datos: LegacyPorcentajeObraDatosIn
    tipo_tramite: Optional[str] = None
    tarifas: List[LegacyPorcentajeObraTarifaIn] = []


class LegacyPorMetroCuadradoDatosIn(BaseSchema):
    """Datos del motor M2 en versión estricta (sin extras)."""

    model_config = ConfigDict(extra="forbid")

    area_solicitada: Decimal = Field(
        ...,
        max_digits=12,
        decimal_places=2,
        description="Área solicitada en metros cuadrados",
    )


class LegacyPorMetroCuadradoTarifaIn(BaseSchema):
    """Tarifa M2 en versión estricta (sin extras)."""

    model_config = ConfigDict(extra="forbid")

    tarifa_m2_id: uuid.UUID


class LegacyPorMetroCuadradoIn(BaseSchema):
    """Bloque específico M2 en versión estricta."""

    model_config = ConfigDict(extra="forbid")

    datos: LegacyPorMetroCuadradoDatosIn
    tarifa: LegacyPorMetroCuadradoTarifaIn


class LegacyVisitasDatosIn(BaseSchema):
    """Datos del motor Visitas en versión estricta (sin extras)."""

    model_config = ConfigDict(extra="forbid")

    cantidad_visitas: int = Field(
        ...,
        ge=1,
        description="Cantidad de visitas solicitadas",
    )
    categoria: Optional[str] = Field(
        None,
        description="Categoría informativa. Se deriva de la tarifa vigente en la fecha efectiva.",
    )


class LegacyVisitasTarifaIn(BaseSchema):
    """Tarifa de visitas en versión estricta (sin extras)."""

    model_config = ConfigDict(extra="forbid")

    tarifa_visitas_id: Union[uuid.UUID, str] = Field(
        ...,
        description="ID de la tarifa por categoría a aplicar, vigente en la fecha efectiva.",
    )


class LegacyVisitasIn(BaseSchema):
    """
    Bloque específico Visitas (Inspección de Obra) en versión estricta.

    No incluye `liquidacion_previa_id`. El inspector es opcional: cuando se
    selecciona, se envía junto con su operación, sin exigir que siga vigente.
    """

    model_config = ConfigDict(extra="forbid")

    datos: LegacyVisitasDatosIn
    tarifa: LegacyVisitasTarifaIn
    inspector_id: Optional[uuid.UUID] = None
    inspector_operacion_id: Optional[uuid.UUID] = None


# ── INPUTS COMPUESTOS (uno por tipo) ────────────────────────────────────────


class LiquidacionEdificacionesLegacyInput(LegacyRegistroMixin, NumeroRevisionRequeridoMixin):
    """
    `POST /liquidaciones/edificaciones/nueva-liquidacion/legacy`

    Edificaciones reutiliza la UNION discriminado de estrategias vigente: el
    registro legacy usa EXACTAMENTE el mismo bloque de cálculo que el registro
    normal, y sólo añade la identidad histórica.
    """

    model_config = ConfigDict(extra="forbid")

    liquidacion_general: LegacyGeneralIn
    liquidacion_especifica: LiquidacionEdificacionesEstrategiaIn


class LiquidacionTaludesLegacyInput(LegacyRegistroMixin, NumeroRevisionRequeridoMixin):
    """`POST /liquidaciones/taludes/nueva-liquidacion/legacy`"""

    model_config = ConfigDict(extra="forbid")

    liquidacion_general: LegacyGeneralIn
    liquidacion_especifica: LegacyPorcentajeObraIn


class LiquidacionImpactoVialLegacyInput(LegacyRegistroMixin, NumeroRevisionRequeridoMixin):
    """`POST /liquidaciones/impacto-vial/nueva-liquidacion/legacy`"""

    model_config = ConfigDict(extra="forbid")

    liquidacion_general: LegacyGeneralIn
    liquidacion_especifica: LegacyPorcentajeObraIn


class LiquidacionHabilitacionUrbanaLegacyInput(LegacyRegistroMixin, NumeroRevisionRequeridoMixin):
    """`POST /liquidaciones/habilitacion-urbana/nueva-liquidacion/legacy`"""

    model_config = ConfigDict(extra="forbid")

    liquidacion_general: LegacyGeneralIn
    liquidacion_especifica: LegacyPorMetroCuadradoIn


class LiquidacionMecanicaSuelosLegacyInput(LegacyRegistroMixin, NumeroRevisionRequeridoMixin):
    """`POST /liquidaciones/mecanica-suelos/nueva-liquidacion/legacy`"""

    model_config = ConfigDict(extra="forbid")

    liquidacion_general: LegacyGeneralIn
    liquidacion_especifica: LegacyPorMetroCuadradoIn


class LiquidacionInspeccionObraLegacyInput(LegacyRegistroMixin):
    """
    `POST /liquidaciones/inspeccion-obra/nueva-liquidacion/legacy`

    IO es estructuralmente revision-less: `numero_revision` es siempre 1 y no
    se expone en el payload.
    """

    model_config = ConfigDict(extra="forbid")

    liquidacion_general: LegacyGeneralIn
    liquidacion_especifica: LegacyVisitasIn
