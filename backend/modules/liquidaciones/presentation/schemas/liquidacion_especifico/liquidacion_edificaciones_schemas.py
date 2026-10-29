"""
Presentation schemas for Edificaciones (PorcentajeObra).

Input: 2 wrappers (general + especifica)
Output: 3 wrappers (general + especifica=identidad + tipo=cálculo)
"""
import uuid
from decimal import Decimal
from typing import Optional, List, Literal, Union
from ninja import Field
from pydantic import ConfigDict
from core.types import BaseSchema
from modules.liquidaciones.domain.constants import EstrategiaCotizacionPO
from modules.liquidaciones.presentation.schemas.liquidacion_general.general_schemas import (
    LiquidacionGeneralOutput,
    LiquidacionGeneralRevisionIn,
    ContactoInlineSchema,
    NumeroRevisionRequeridoMixin,
)
from modules.liquidaciones.presentation.schemas.liquidacion_tipo.porcentaje_schemas import (
    LiquidacionPorcentajeObraIn,
    LiquidacionPorcentajeObraDatosOut,
    LiquidacionPorcentajeObraDetalleOut,
    LiquidacionPorcentajeObraTarifaIn,
    EspecialidadOut,
)
from modules.liquidaciones.presentation.schemas.liquidacion_especifico.liquidacion_patch_po_schemas import (
    LiquidacionPatchPOGeneralIn,
    TarifaPatchIn,
)


class LiquidacionTipoOutput(BaseSchema):
    """Output de identidad: solo id + numero."""
    id: uuid.UUID
    numero: Optional[int] = Field(None, description="Número secuencial correlativo de la especialidad")


# ── Union discriminado de estrategias de cotización PO (SOLO Edificaciones) ───
#
# La union existe únicamente para Edificaciones: Taludes, Impacto Vial, edge y
# legacy siguen usando `LiquidacionPorcentajeObraIn` sin tocar, de modo que los
# campos de estrategia NO se filtran a otros motores (contrato de schemas DRY).
#
# Hay exactamente TRES estrategias (no hay alias ni cuarto modo):
#   - NORMAL_SELECCIONADAS: `valor_declarado` + seleccionadas. El discriminador
#     es opcional para preservar el payload vigente byte-compatible.
#   - TARIFA_HABILITADAS_PARTICIPANTES: `valor_declarado` + participantes. El
#     discriminador es obligatorio: H lo resuelve el catálogo, nunca el cliente.
#   - TOTAL_EXPLICITO: `total_explicito` + participantes. El discriminador es
#     obligatorio y `valor_declarado` está prohibido (el total es autoritativo).
#
# Cada variante declara `extra="forbid"`: un payload mixto (campos de dos
# estrategias), incompleto (falta un campo obligatorio de la estrategia) o con
# campos prohibidos se rechaza con 422. No se aceptan campos desconocidos.
#
# Los valores del discriminador se derivan del enum canónico
# (`EstrategiaCotizacionPO`) para que no exista deriva entre schema y dominio.

ESTRATEGIA_NORMAL = EstrategiaCotizacionPO.NORMAL_SELECCIONADAS.value
ESTRATEGIA_HABILITADAS = EstrategiaCotizacionPO.TARIFA_HABILITADAS_PARTICIPANTES.value
ESTRATEGIA_TOTAL = EstrategiaCotizacionPO.TOTAL_EXPLICITO.value


class LiquidacionEdificacionesEstrategiaNormalDatosIn(BaseSchema):
    """Datos de NORMAL_SELECCIONADAS: valor declarado del proyecto."""

    model_config = ConfigDict(extra="forbid")

    valor_declarado: Decimal = Field(
        ...,
        le=Decimal("9999999999.99"),
        max_digits=12,
        decimal_places=2,
        description="Valor declarado máximo compatible con DecimalField(max_digits=12, decimal_places=2).",
    )
    tipo_tramite: Optional[str] = None


class LiquidacionEdificacionesEstrategiaHabilitadasDatosIn(BaseSchema):
    """Datos de TARIFA_HABILITADAS_PARTICIPANTES: valor declarado del proyecto."""

    model_config = ConfigDict(extra="forbid")

    valor_declarado: Decimal = Field(
        ...,
        le=Decimal("9999999999.99"),
        max_digits=12,
        decimal_places=2,
        description="Valor declarado máximo compatible con DecimalField(max_digits=12, decimal_places=2).",
    )
    tipo_tramite: Optional[str] = None


class LiquidacionEdificacionesEstrategiaTotalExplicitoDatosIn(BaseSchema):
    """Datos de TOTAL_EXPLICITO: valor informativo y total final autoritativo."""

    model_config = ConfigDict(extra="forbid")

    valor_declarado: Decimal = Field(
        ...,
        le=Decimal("9999999999.99"),
        max_digits=12,
        decimal_places=2,
        description="Valor informativo de la obra; no interviene en el cálculo.",
    )
    total_explicito: Decimal = Field(
        ...,
        gt=Decimal("0"),
        le=Decimal("9999999999.99"),
        max_digits=12,
        decimal_places=2,
        description="Total final autoritativo con IGV incluido.",
    )
    tipo_tramite: Optional[str] = None


class LiquidacionEdificacionesEstrategiaNormalIn(BaseSchema):
    """
    NORMAL_SELECCIONADAS — las seleccionadas determinan padre y detalles.

    El discriminador es OPCIONAL: si no viene, se asume esta estrategia y el
    payload vigente (modo normal) permanece byte-compatible.
    """

    model_config = ConfigDict(extra="forbid")

    estrategia_cotizacion: Literal[ESTRATEGIA_NORMAL] = ESTRATEGIA_NORMAL
    datos: LiquidacionEdificacionesEstrategiaNormalDatosIn
    tipo_tramite: Optional[str] = None
    tarifas: List[LiquidacionPorcentajeObraTarifaIn] = []


class LiquidacionEdificacionesEstrategiaHabilitadasIn(BaseSchema):
    """
    TARIFA_HABILITADAS_PARTICIPANTES — el padre cobra H habilitadas del catálogo.

    El discriminador es OBLIGATORIO: la cantidad de habilitadas (H) la resuelve
    el catálogo para la fecha efectiva, nunca el cliente ni los participantes.
    """

    model_config = ConfigDict(extra="forbid")

    estrategia_cotizacion: Literal[ESTRATEGIA_HABILITADAS]
    datos: LiquidacionEdificacionesEstrategiaHabilitadasDatosIn
    tipo_tramite: Optional[str] = None
    tarifas: List[LiquidacionPorcentajeObraTarifaIn] = []


class LiquidacionEdificacionesEstrategiaTotalExplicitoIn(BaseSchema):
    """
    TOTAL_EXPLICITO — el total ingresado con IGV es autoritativo.

    El discriminador es OBLIGATORIO y `valor_declarado` está prohibido: el
    backend extrae el subtotal del total y los porcentajes quedan NULL.
    """

    model_config = ConfigDict(extra="forbid")

    estrategia_cotizacion: Literal[ESTRATEGIA_TOTAL]
    datos: LiquidacionEdificacionesEstrategiaTotalExplicitoDatosIn
    tipo_tramite: Optional[str] = None
    tarifas: List[LiquidacionPorcentajeObraTarifaIn] = []


# El orden importa: con el discriminador ausente, gana la primera variante
# compatible. NORMAL_SELECCIONADAS va primero porque es la estrategia vigente.
LiquidacionEdificacionesEstrategiaIn = Union[
    LiquidacionEdificacionesEstrategiaNormalIn,
    LiquidacionEdificacionesEstrategiaHabilitadasIn,
    LiquidacionEdificacionesEstrategiaTotalExplicitoIn,
]


class LiquidacionEdificacionesAcumulacionOut(BaseSchema):
    """Acumulación vigente del PO: diferencia entre el padre y la suma de sus detalles."""

    porcentaje_acumulado: Optional[Decimal] = Field(
        None,
        description="Porcentaje acumulado. NULL en TOTAL_EXPLICITO.",
    )
    subtotal_acumulado: Decimal = Field(
        ...,
        description="Diferencia monetaria entre el subtotal del padre y la suma de los detalles.",
    )


# ── Cotizar-edición: union discriminado SOLO de Edificaciones ─────────────────
#
# El preview de edición usa la MISMA union de estrategias que el preview de
# creación, pero con `tarifas` OBLIGATORIO: en edición los participantes NO se
# auto-completan (auto-rellenar cambiaría en silencio el alcance del cálculo).
#
# Se declara aquí y no en `liquidacion_cotizar_edicion_schemas.py` porque ese
# archivo es COMPARTIDO con Taludes e Impacto Vial, que no usan estrategias.


class LiquidacionEdificacionesCotizarEdicionNormalIn(BaseSchema):
    """
    NORMAL_SELECCIONADAS — cotizar-edición.

    El discriminador es OPCIONAL: si no viene, se asume esta estrategia y el
    payload vigente (modo normal) permanece byte-compatible.
    """

    model_config = ConfigDict(extra="forbid")

    estrategia_cotizacion: Literal[ESTRATEGIA_NORMAL] = ESTRATEGIA_NORMAL
    datos: LiquidacionEdificacionesEstrategiaNormalDatosIn
    tipo_tramite: Optional[str] = None
    tarifas: List[LiquidacionPorcentajeObraTarifaIn] = Field(
        ...,
        description="Participantes cotizados. Obligatorio en edición: no se auto-completa.",
    )


class LiquidacionEdificacionesCotizarEdicionHabilitadasIn(BaseSchema):
    """TARIFA_HABILITADAS_PARTICIPANTES — cotizar-edición."""

    model_config = ConfigDict(extra="forbid")

    estrategia_cotizacion: Literal[ESTRATEGIA_HABILITADAS]
    datos: LiquidacionEdificacionesEstrategiaHabilitadasDatosIn
    tipo_tramite: Optional[str] = None
    tarifas: List[LiquidacionPorcentajeObraTarifaIn] = Field(
        ...,
        description="Participantes cotizados. Obligatorio en edición: no se auto-completa.",
    )


class LiquidacionEdificacionesCotizarEdicionTotalExplicitoIn(BaseSchema):
    """TOTAL_EXPLICITO — cotizar-edición."""

    model_config = ConfigDict(extra="forbid")

    estrategia_cotizacion: Literal[ESTRATEGIA_TOTAL]
    datos: LiquidacionEdificacionesEstrategiaTotalExplicitoDatosIn
    tipo_tramite: Optional[str] = None
    tarifas: List[LiquidacionPorcentajeObraTarifaIn] = Field(
        ...,
        description="Participantes cotizados. Obligatorio en edición: no se auto-completa.",
    )


LiquidacionEdificacionesCotizarEdicionEstrategiaIn = Union[
    LiquidacionEdificacionesCotizarEdicionNormalIn,
    LiquidacionEdificacionesCotizarEdicionHabilitadasIn,
    LiquidacionEdificacionesCotizarEdicionTotalExplicitoIn,
]


class LiquidacionEdificacionesCotizarEdicionIn(BaseSchema):
    """
    Input de `POST /liquidaciones/edificaciones/{id}/cotizar-edicion`.

    Usa el wrapper `liquidacion_tipo` con la union discriminado de estrategias.
    El backend resuelve IGV, UIT y derechos por `fecha_registro` (histórico) y
    H por el contrato de snapshot/catálogo: el cliente nunca los envía.
    """

    liquidacion_tipo: LiquidacionEdificacionesCotizarEdicionEstrategiaIn


class LiquidacionEdificacionesPorcentajeObraDatosOut(LiquidacionPorcentajeObraDatosOut):
    """
    Wrapper de cálculo PO de Edificaciones: agrega estrategia, snapshots y
    acumulación al wrapper PO compartido.

    Se mantiene separado de `LiquidacionPorcentajeObraDatosOut` para que
    Taludes, Impacto Vial, edge y legacy NO expongan campos de estrategia PO.
    """

    estrategia_cotizacion: Optional[str] = Field(
        None,
        description="Estrategia de cotización persistida: NORMAL_SELECCIONADAS, "
        "TARIFA_HABILITADAS_PARTICIPANTES o TOTAL_EXPLICITO.",
    )
    count_habilitadas: Optional[int] = Field(
        None,
        description="Snapshot de H (habilitadas del catálogo en la fecha efectiva).",
    )
    total_explicito: Optional[Decimal] = Field(
        None,
        description="Total final autoritativo persistido (TOTAL_EXPLICITO).",
    )
    porcentaje_tarifa: Optional[Decimal] = Field(
        None,
        description="Snapshot del porcentaje unitario (f) de la tarifa aplicada.",
    )
    tarifa_aplicada_id: Optional[uuid.UUID] = Field(
        None,
        description="Tarifa que genera el subtotal del padre (FK null → sin snapshot).",
    )
    acumulacion: Optional[LiquidacionEdificacionesAcumulacionOut] = Field(
        None,
        description="Proyección vigente de la diferencia padre - detalles. NULL si no hay diferencia.",
    )


class LiquidacionEdificacionesInput(NumeroRevisionRequeridoMixin):
    """Input: 2 wrappers + número de revisión."""
    liquidacion_general: LiquidacionGeneralRevisionIn
    liquidacion_especifica: LiquidacionEdificacionesEstrategiaIn


class LiquidacionEdificacionesOutput(BaseSchema):
    """Output: 3 wrappers."""
    liquidacion_general: LiquidacionGeneralOutput
    liquidacion_especifica: LiquidacionTipoOutput  # identidad
    liquidacion_tipo: LiquidacionEdificacionesPorcentajeObraDatosOut  # cálculo


class LiquidacionEdificacionesCotizarInput(BaseSchema):
    """
    Input for /cotizar endpoint.

    Only liquidacion_especifica is needed (no liquidacion_general).
    `liquidacion_especifica` es la union discriminado de estrategias PO.
    """
    liquidacion_especifica: LiquidacionEdificacionesEstrategiaIn


class LiquidacionEdificacionesCotizarTarifaOut(BaseSchema):
    """Tarifa applied in cotizacion."""
    tarifa_id: uuid.UUID
    porcentaje_aplicado: Decimal
    especialidad_id: uuid.UUID


class LiquidacionEdificacionesCotizarDetalleOut(BaseSchema):
    """Detalle of cotizacion."""
    tarifa_id: Optional[uuid.UUID] = None
    especialidad: Optional[EspecialidadOut] = None
    porcentaje_aplicado: Optional[Decimal] = None
    subtotal: Decimal


class LiquidacionGeneralNuevaRevisionIn(BaseSchema):
    """Input reducido para nueva revisión — solo campos editables (sin municipalidad/proyecto)."""
    expediente: Optional[str] = Field(None, description="Número de expediente")
    observacion: Optional[str] = Field(None, description="Observación opcional")
    denominacion_de_proyecto: Optional[str] = Field(None, description="Denominación del proyecto (opcional, hereda de la previa si no se provee)")
    contacto: Optional[ContactoInlineSchema] = Field(None, description="Contacto principal (se crea inline)")


class LiquidacionEdificacionesRevisionDatosIn(BaseSchema):
    """
    Datos de la estrategia en revisión (nueva revisión / relacionada / PATCH).

    `valor_declarado` y `total_explicito` son mutuamente excluyentes según la
    estrategia: el backend valida la coherencia y responde 400 si se mezclan.
    """

    model_config = ConfigDict(extra="forbid")

    valor_declarado: Optional[Decimal] = Field(
        None,
        ge=Decimal("0"),
        max_digits=12,
        decimal_places=2,
        description="Valor declarado informativo de la obra (todas las estrategias).",
    )
    total_explicito: Optional[Decimal] = Field(
        None,
        gt=Decimal("0"),
        max_digits=12,
        decimal_places=2,
        description="Total final autoritativo con IGV (estrategia TOTAL_EXPLICITO).",
    )
    tipo_tramite: Optional[str] = Field(
        None,
        description="Tipo de trámite de edificaciones (opcional).",
    )


class LiquidacionEspecificaNuevaRevisionIn(BaseSchema):
    """Input específico para nueva revisión — tarifas + tipo_tramite (sin datos, se hereda de la previa)."""
    tipo_tramite: Optional[str] = Field(
        None,
        description="Tipo de trámite de edificaciones (ej. OBRA_NUEVA, AMPLIACION, etc.)",
    )
    tarifas: List[LiquidacionPorcentajeObraTarifaIn] = Field(
        ...,
        description="Tarifas seleccionadas. NO puede estar vacío y deben estar vigentes.",
    )
    # ── Module 5: estrategia de cotización de la nueva revisión ──────────────
    estrategia_cotizacion: Optional[
        Literal[ESTRATEGIA_NORMAL, ESTRATEGIA_HABILITADAS, ESTRATEGIA_TOTAL]
    ] = Field(
        None,
        description="Estrategia de la nueva revisión. Si se omite, se hereda la de la "
        "liquidación previa. Los datos que exige la estrategia se toman de `datos`.",
    )
    datos: Optional[LiquidacionEdificacionesRevisionDatosIn] = Field(
        None,
        description="Valor declarado y, para TOTAL_EXPLICITO, total final. "
        "Si se omiten, se heredan de la liquidación previa.",
    )


class LiquidacionEdificacionesNuevaRevisionInput(NumeroRevisionRequeridoMixin):
    """Input para /nueva-revision — schema específico reducido.

    Hereda de la liquidación previa: proyecto, municipalidad, valor_declarado.
    Solo se editan: expediente, observacion, contacto y tarifas.
    El número de revisión lo elige el usuario (1, 3 o 5).
    """
    liquidacion_previa_id: uuid.UUID
    liquidacion_general: LiquidacionGeneralNuevaRevisionIn
    liquidacion_especifica: LiquidacionEspecificaNuevaRevisionIn


class LiquidacionEdificacionesRelacionadaInput(NumeroRevisionRequeridoMixin):
    """
    Input para /relacionada — crea una nueva liquidacion vinculada a una
    liquidacion previa existente, con el número de revisión elegido por el usuario.

    Usa la misma estructura que primera-revision (full input) más el
    liquidacion_previa_id para establecer la relación de grupo.

    `liquidacion_especifica` es la union discriminado de estrategias: una
    relacionada puede cambiar de estrategia respecto de la previa.
    """
    liquidacion_previa_id: uuid.UUID
    liquidacion_general: LiquidacionGeneralRevisionIn
    liquidacion_especifica: LiquidacionEdificacionesEstrategiaIn


# ── PATCH de Edificaciones: estrategia + snapshots (SOLO Edificaciones) ────────
#
# El PATCH compartido (`liquidacion_patch_po_schemas.py`) lo usan Taludes,
# Impacto Vial y Edificaciones: no se toca para no filtrarles campos de
# estrategia PO. Aquí se compone el wrapper de Edificaciones reutilizando el
# bloque general compartido (contrato SCHEMA_DRY_INTENTION).


class LiquidacionEdificacionesPatchTipoIn(BaseSchema):
    """
    Wrapper `liquidacion_tipo` del PATCH de Edificaciones.

    Todos los campos son opcionales: lo que se omite se preserva.

    - `estrategia_cotizacion`: si se omite, se conserva la estrategia
      persistida; si se envía, se transiciona a esa estrategia.
    - `datos.valor_declarado` / `datos.total_explicito`: el dato que exige la
      estrategia. Mezclarlos es un error de negocio (400).
    - `tarifas`: participantes a aplicar; si se omite se preservan los actuales.
    """

    model_config = ConfigDict(extra="forbid")

    estrategia_cotizacion: Optional[
        Literal[ESTRATEGIA_NORMAL, ESTRATEGIA_HABILITADAS, ESTRATEGIA_TOTAL]
    ] = Field(
        None,
        description="Estrategia a la que se transiciona. Si se omite, se conserva la persistida.",
    )
    datos: Optional[LiquidacionEdificacionesRevisionDatosIn] = Field(
        None,
        description="Datos del cálculo (valor declarado o total explícito).",
    )
    tipo_tramite: Optional[str] = Field(
        None,
        description="Tipo de trámite de edificaciones (opcional).",
    )
    tarifas: Optional[List[LiquidacionPorcentajeObraTarifaIn]] = Field(
        None,
        description="Participantes a aplicar (opcional, preserva los actuales si se omite).",
    )


class LiquidacionEdificacionesPatchIn(BaseSchema):
    """
    Input del PATCH de Edificaciones.

    Mantiene los dos formatos soportados por el PATCH PO (wrapper actual y
    flat legacy) y añade el bloque de estrategia en `liquidacion_tipo`.
    """

    liquidacion_general: Optional[LiquidacionPatchPOGeneralIn] = Field(
        None,
        description="Campos generales opcionales (expediente, proyecto, municipalidad, "
        "numero_revision, etc.).",
    )
    liquidacion_tipo: Optional[LiquidacionEdificacionesPatchTipoIn] = Field(
        None,
        description="Campos de cálculo tipo PO (estrategia, datos, tarifas).",
    )
    # Flat format (legacy/backward compat)
    valor_declarado: Optional[Decimal] = Field(
        None,
        ge=Decimal("0"),
        max_digits=12,
        decimal_places=2,
        description="Nuevo valor declarado (flat legacy format, opcional).",
    )
    tarifas: Optional[List[TarifaPatchIn]] = Field(
        None,
        description="Lista de tarifas a aplicar (flat legacy format, opcional).",
    )


class LiquidacionEdificacionesCotizarOutput(BaseSchema):
    """Output for /cotizar endpoint."""
    valor_declarado: Optional[Decimal] = None
    porcentaje_liquidacion: Optional[Decimal] = None
    derecho_minimo: Optional[Decimal] = None
    derecho_maximo: Optional[Decimal] = None
    porcentaje_minimo_uit: Optional[Decimal] = None
    derecho_aplicado_id: Optional[uuid.UUID] = None
    estrategia_cotizacion: Optional[str] = Field(
        None,
        description="Estrategia aplicada en la cotización: NORMAL_SELECCIONADAS, "
        "TARIFA_HABILITADAS_PARTICIPANTES o TOTAL_EXPLICITO.",
    )
    count_habilitadas: Optional[int] = Field(
        None,
        description="H (habilitadas del catálogo) resuelto para la fecha efectiva.",
    )
    total_explicito: Optional[Decimal] = Field(
        None,
        description="Total final autoritativo (TOTAL_EXPLICITO).",
    )
    porcentaje_tarifa: Optional[Decimal] = Field(
        None,
        description="Porcentaje unitario (f) de la tarifa aplicable al padre.",
    )
    acumulacion: Optional[LiquidacionEdificacionesAcumulacionOut] = Field(
        None,
        description="Proyección efímera de la diferencia padre - detalles. "
        "El preview NUNCA la persiste.",
    )
    detalles: List[LiquidacionEdificacionesCotizarDetalleOut]
    total_subtotal: Decimal
    total: Decimal
