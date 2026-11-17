"""
Especifico Inspección de Obra schemas — payloads de primera-revisión.
"""
import uuid
from decimal import Decimal
from typing import Literal, Optional, Union
from core.types import BaseSchema
from ninja import Field
from pydantic import ConfigDict

from modules.liquidaciones.domain.constants import ModoCotizacionVisitas
from modules.liquidaciones.presentation.schemas.liquidacion_general.general_schemas import (
    ContactoInlineSchema,
    LiquidacionGeneralOutput,
    LiquidacionGeneralRevisionIn,
)
from modules.liquidaciones.presentation.schemas.liquidacion_especifico.liquidacion_cotizar_edicion_schemas import (
    CotizarEdicionVisitasDatosIn,
    CotizarEdicionVisitasTarifaIn,
)
from modules.liquidaciones.presentation.schemas.liquidacion_tipo.tipo_schemas import (
    LiquidacionTipoOutput,
)
from modules.liquidaciones.presentation.schemas.liquidacion_tipo.visitas_schemas import (
    CotizarPorCategoriaVisitasCalculoOutputSchema,
    CotizarPorCategoriaVisitasDatosOutputSchema,
    LiquidacionPorCategoriaVisitasDatosIn,
    LiquidacionPorCategoriaVisitasDatosOut,
    LiquidacionPorCategoriaVisitasTarifaIn,
)


class LiquidacionInspeccionObraOutput(BaseSchema):
    """Payload de salida: Cabecera + Tipo Identidad + cálculo de Visitas."""
    liquidacion_general: LiquidacionGeneralOutput
    liquidacion_especifica: LiquidacionTipoOutput
    liquidacion_tipo: LiquidacionPorCategoriaVisitasDatosOut


# =============================================================================
# POST /nueva-liquidacion/primera-revision — IO desde liquidación previa
# Hereda proyecto/municipalidad/entidad de la liquidación previa.
# =============================================================================
class LiquidacionInspeccionObraNuevaRevisionDatosIn(BaseSchema):
    """
    Datos específicos de la revisión IO.

    categoria is nullable — for the legacy/manual path (CATEGORIA=0), no valid
    tariff category exists, so categoria is stored as null along with a null tarifa.
    Normal requests derive it from tarifa_visitas_id; the optional input is kept
    only for legacy compatibility and is never authoritative when a tariff exists.
    """
    cantidad_visitas: int = Field(..., description="Cantidad de visitas solicitadas")
    categoria: Optional[str] = Field(
        None,
        description="Categoría legacy opcional. Se deriva de la tarifa cuando existe.",
    )


class LiquidacionInspeccionObraNuevaRevisionTarifaIn(BaseSchema):
    """
    Tarifa aplicada a la liquidación IO.

    tarifa_visitas_id is nullable — for the legacy/manual path (CATEGORIA=0 or
    unmatched tariff), no valid tariff exists, so the record is created with a
    null FK and modo_calculo=MANUAL.
    Uses Union to preserve Pydantic string→UUID coercion for string inputs.
    Normal UI path should still enforce a valid tarifa_visitas_id.
    """
    tarifa_visitas_id: Union[uuid.UUID, str, None] = Field(
        None,
        description="ID de la tarifa por categoría a aplicar. Null for legacy CATEGORIA=0 records.",
    )


class LiquidacionInspeccionObraContinuidadIn(BaseSchema):
    """
    Bloque OPCIONAL de CONTINUIDAD de visitas (Inspección de Obra).

    Se activa desde `Liquidaciones > Inspección de Obra > Continuar` y permite
    registrar que B (la liquidación nueva) continúa un trabajo de inspección
    previo, acreditando el crédito de las visitas no realizadas de A.

    El bloque es autocontenido: NO existe un endpoint de candidatas de
    continuidad. La previa puede venir de CAM (referenciada por
    `liquidacion_previa_id`, obtained del listado/detalle de IO existente) o
    puede estar fuera de CAM (datos manuales: la referencia se omite).

    Lo que NO se envía (lo calcula el servidor):
    - `monto_acumulado` / `total_acumulado`: el valor completo del trabajo de B
      a la tarifa de B.
    - `total_credito`: la contraparte bruta de `subtotal_credito`.

    Los campos numéricos aceptan `null`: el servidor aplica el default
    (`visitas_previas_pendientes` → 0, `subtotal_credito` → 0).

    La NO-NEGATIVIDAD del crédito NO se valida aquí a propósito: es una regla
    de NEGOCIO y la resuelve el orquestador con un 400 explícito. Si se
    declarara `ge=0` en este schema, la petición moriría antes como 422
    (error de validación de pydantic) y el mensaje de negocio nunca llegaría
    al cliente.

    `total_pagado_previa` sí es un dato DECLARADO con rango acotado: por eso
    valida aquí (`gt=0`, `max_digits=12`, `decimal_places=2`) y un valor
    inválido muere como 422.
    """

    liquidacion_previa_id: Optional[uuid.UUID] = Field(
        None,
        description="ID de la liquidación de IO previa (A). Opcional: si la previa "
                    "no está en CAM, se omiten y el crédito se ingresa manual.",
    )
    visitas_previas_pendientes: Optional[int] = Field(
        0,
        ge=0,
        le=9999,
        description="Cantidad de visitas de la previa que se acreditan (0..9999). "
                    "Null equivale a 0.",
    )
    visitas_previas_totales: Optional[int] = Field(
        None,
        ge=0,
        le=9999,
        description="Cantidad total de visitas de la previa. Si se referencia la "
                    "previa en CAM, el servidor lo deriva de ella.",
    )
    categoria_previa: Optional[str] = Field(
        None,
        max_length=20,
        description="Categoría de la previa (informativo).",
    )
    subtotal_credito: Optional[Decimal] = Field(
        Decimal("0"),
        max_digits=12,
        decimal_places=2,
        description="Crédito NETO que se descuenta del valor completo de B. "
                    "Null equivale a 0. El servidor valida que no sea negativo "
                    "(400 si lo es) y deriva `total_credito` aplicando el IGV. "
                    "Se IGNORA si viene `total_pagado_previa`.",
    )
    total_pagado_previa: Optional[Decimal] = Field(
        None,
        gt=Decimal("0"),
        max_digits=12,
        decimal_places=2,
        description="Monto BRUTO pagado en la IO previa, IGV incluido. Si viene, "
                    "MANDA: el servidor deriva el crédito NETO con el IGV vigente "
                    "y `subtotal_credito` (neto) se ignora. Si no viene, se "
                    "conserva el camino vigente por `subtotal_credito`.",
    )
    observacion: Optional[str] = Field(
        None,
        description="Observación sobre la continuidad.",
    )


class LiquidacionInspeccionObraNuevaRevisionEspecificaIn(BaseSchema):
    """
    Payload específico para IO primera-revision (con o sin previa).

    Para sin previa (nueva-liquidacion): inspector_operacion_id es OBLIGATORIO.
    La especialidad_revision se deriva de InspectorOperacion.especialidad_revision.
    El inspector se deriva de InspectorOperacion.inspector.

    Para con previa (relacionada): inspector_operacion_id es OBLIGATORIO.
    Se valida que InspectorOperacion.tipo_liquidacion coincida con la previa.

    inspector_id es OPCIONAL — se usa solo para cross-validación con
    InspectorOperacion.inspector_id cuando ambos están presentes.
    tipo_liquidacion ya no va en el input — se deriva de InspectorOperacion.

    `continuidad` es OPCIONAL: cuando está presente, la liquidación nueva cobra
    solo la DIFERENCIA respecto del valor completo del trabajo.
    """
    datos: LiquidacionInspeccionObraNuevaRevisionDatosIn
    tarifa: LiquidacionInspeccionObraNuevaRevisionTarifaIn
    inspector_id: Optional[uuid.UUID] = Field(
        None,
        description="ID del inspector asignado. Opcional — se valida contra inspector_operacion si ambos presentes.",
    )
    inspector_operacion_id: uuid.UUID = Field(
        ...,
        description="ID de la InspectorOperacion del inspector seleccionado. "
                    "Obligatorio para ambos flujos (nueva y relacionada). "
                    "Se usa para derivar inspector, especialidad_revision y tipo_liquidacion. "
                    "Obtenido del endpoint /seleccionables.",
    )
    continuidad: Optional[LiquidacionInspeccionObraContinuidadIn] = Field(
        None,
        description="Bloque opcional de continuidad con la liquidación previa. "
                    "Ausente = IO normal (comportamiento vigente).",
    )


class LiquidacionInspeccionObraNuevaLiquidacionInput(BaseSchema):
    """
    Payload de entrada para crear una IO primera-revision SIN liquidación previa.
    Entidad y Proyecto se crean desde cero a partir de los datos del usuario.
    No requiere liquidacion_previa_id.
    """
    liquidacion_general: LiquidacionGeneralRevisionIn = Field(
        ..., description="Datos generales con proyecto, entidad y municipalidad desde entrada del usuario"
    )
    liquidacion_especifica: LiquidacionInspeccionObraNuevaRevisionEspecificaIn = Field(
        ..., description="Datos específicos IO: datos, tarifa e inspector_id"
    )


class LiquidacionInspeccionObraNuevaRevisionInput(BaseSchema):
    """
    Payload de entrada para crear una IO primera-revision heredando
    proyecto/municipalidad/entidad de una liquidación previa (Edificación o Habilitación Urbana).
    """
    liquidacion_previa_id: uuid.UUID = Field(..., description="ID de la liquidación previa (Edificación o Habilitación Urbana)")
    liquidacion_especifica: LiquidacionInspeccionObraNuevaRevisionEspecificaIn
    contacto: Optional[ContactoInlineSchema] = Field(None, description="Contacto principal (se crea inline)")


# =============================================================================
# Cotización de IO — union discriminada de MODO (NORMAL | CONTINUAR)
# =============================================================================
#
# La union se declara AQUÍ (módulo de IO) y se COMPOSE con los bloques
# compartidos de Visitas: `visitas_schemas.py` y `liquidacion_cotizar_edicion_schemas.py`
# NO se tocan (SCHEMA_DRY_INTENTION).
#
# Hay exactamente DOS modos:
#   - NORMAL    → la cotización vigente (sin continuidad). El discriminador es
#                 OPCIONAL: el payload vigente queda byte-compatible.
#   - CONTINUAR → la liquidación continúa un trabajo previo. El discriminador y
#                 el bloque `continuidad` son OBLIGATORIOS.
#
# Cada variante declara `extra="forbid"`: un payload mixto (continuidad en
# NORMAL), incompleto (CONTINUAR sin `total_pagado_previa`) o con campos
# desconocidos se rechaza con 422.
#
# Los valores del discriminador se derivan del enum canónico
# (`ModoCotizacionVisitas`) para que no exista deriva entre schema y dominio.

MODO_COTIZACION_IO_NORMAL = ModoCotizacionVisitas.NORMAL.value
MODO_COTIZACION_IO_CONTINUAR = ModoCotizacionVisitas.CONTINUAR.value


class LiquidacionInspeccionObraCotizarContinuidadIn(BaseSchema):
    """
    Datos DECLARADOS por el cliente para el modo CONTINUAR.

    NO lleva `liquidacion_previa_id`: la ruta de cotización es `AllowAny` y
    desreferenciar la previa desde el servidor permitiría a un llamador no
    autenticado sondear el monto pagado de liquidaciones ajenas. El bruto es
    una DECLARACIÓN del cliente que el servidor valida y convierte.
    """

    model_config = ConfigDict(extra="forbid")

    total_pagado_previa: Decimal = Field(
        ...,
        gt=Decimal("0"),
        max_digits=12,
        decimal_places=2,
        description="Monto BRUTO pagado en la liquidación de IO previa, IGV incluido. "
                    "Es la cifra que se resta del valor completo de B. El servidor "
                    "deriva el crédito neto con el IGV efectivo de la ruta.",
    )


class LiquidacionInspeccionObraCotizarNormalIn(BaseSchema):
    """
    NORMAL — la cotización vigente de IO (sin continuidad).

    El discriminador es OPCIONAL: si no viene, se asume NORMAL y el payload
    vigente permanece byte-compatible.
    """

    model_config = ConfigDict(extra="forbid")

    modo_cotizacion: Literal[MODO_COTIZACION_IO_NORMAL] = MODO_COTIZACION_IO_NORMAL
    datos: LiquidacionPorCategoriaVisitasDatosIn
    tarifa: LiquidacionPorCategoriaVisitasTarifaIn


class LiquidacionInspeccionObraCotizarContinuarIn(BaseSchema):
    """CONTINUAR — la liquidación continúa un trabajo previo (IO)."""

    model_config = ConfigDict(extra="forbid")

    modo_cotizacion: Literal[MODO_COTIZACION_IO_CONTINUAR]
    datos: LiquidacionPorCategoriaVisitasDatosIn
    tarifa: LiquidacionPorCategoriaVisitasTarifaIn
    continuidad: LiquidacionInspeccionObraCotizarContinuidadIn


# El orden importa: con el discriminador ausente, gana la primera variante
# compatible. NORMAL va primero porque es el modo vigente.
LiquidacionInspeccionObraCotizarEspecificaIn = Union[
    LiquidacionInspeccionObraCotizarNormalIn,
    LiquidacionInspeccionObraCotizarContinuarIn,
]


class LiquidacionInspeccionObraCotizarInput(BaseSchema):
    """
    Input de `POST /liquidaciones/inspeccion-obra/cotizar`.

    Solo viaja `liquidacion_especifica`: el wrapper NO cambia. El bloque
    `continuidad` (bruto declarado) es opcional y solo existe en CONTINUAR.
    """

    liquidacion_especifica: LiquidacionInspeccionObraCotizarEspecificaIn


# ── Cotizar-edición: union discriminada SOLO de IO ────────────────────────────
#
# El preview de edición usa la MISMA union de modos que el preview de alta, con
# `tarifa` OBLIGATORIA (igual que hoy) y con el IGV/UIT HISTÓRICOS de la fecha
# de registro.


class LiquidacionInspeccionObraCotizarEdicionNormalIn(BaseSchema):
    """NORMAL — cotizar-edición (el discriminador es opcional)."""

    model_config = ConfigDict(extra="forbid")

    modo_cotizacion: Literal[MODO_COTIZACION_IO_NORMAL] = MODO_COTIZACION_IO_NORMAL
    datos: CotizarEdicionVisitasDatosIn
    tarifa: CotizarEdicionVisitasTarifaIn


class LiquidacionInspeccionObraCotizarEdicionContinuarIn(BaseSchema):
    """CONTINUAR — cotizar-edición."""

    model_config = ConfigDict(extra="forbid")

    modo_cotizacion: Literal[MODO_COTIZACION_IO_CONTINUAR]
    datos: CotizarEdicionVisitasDatosIn
    tarifa: CotizarEdicionVisitasTarifaIn
    continuidad: LiquidacionInspeccionObraCotizarContinuidadIn


LiquidacionInspeccionObraCotizarEdicionTipoIn = Union[
    LiquidacionInspeccionObraCotizarEdicionNormalIn,
    LiquidacionInspeccionObraCotizarEdicionContinuarIn,
]


class LiquidacionInspeccionObraCotizarEdicionInput(BaseSchema):
    """
    Input de `POST /liquidaciones/inspeccion-obra/{id}/cotizar-edicion`.

    Usa el wrapper `liquidacion_tipo` (NO cambia). El backend resuelve IGV, UIT
    y tarifa por `fecha_registro` (histórico): el cliente nunca los envía.
    """

    liquidacion_tipo: LiquidacionInspeccionObraCotizarEdicionTipoIn


# ── Salida de la cotización de IO ─────────────────────────────────────────────


class LiquidacionInspeccionObraCotizarContinuidadOut(BaseSchema):
    """Cifras autoritativas del modo CONTINUAR (netas y brutas)."""

    total_pagado_previa: Decimal = Field(..., description="Bruto declarado por el cliente.")
    valor_completo_neto: Decimal = Field(..., description="Valor completo de B, neto.")
    valor_completo_bruto: Decimal = Field(..., description="Valor completo de B, con IGV.")
    credito_neto: Decimal = Field(..., description="Crédito derivado del bruto declarado.")
    credito_bruto: Decimal = Field(..., description="Crédito bruto (par del crédito neto).")
    diferencia_neto: Decimal = Field(..., description="A cobrar, neto.")
    diferencia_bruto: Decimal = Field(..., description="A cobrar, bruto.")
    igv_porcentaje: Decimal = Field(..., description="IGV efectivo de la ruta.")


class LiquidacionInspeccionObraCotizarOutput(BaseSchema):
    """
    Output de la cotización de IO: bloques compartidos + bloque de IO.

    La respuesta se ENSANCHA: `datos` y `calculo` no cambian y el eco
    `modo_cotizacion` siempre viaja. El bloque `continuidad` es opcional
    (null en NORMAL).
    """

    datos: CotizarPorCategoriaVisitasDatosOutputSchema
    calculo: CotizarPorCategoriaVisitasCalculoOutputSchema
    modo_cotizacion: Optional[str] = Field(None, description="NORMAL | CONTINUAR")
    continuidad: Optional[LiquidacionInspeccionObraCotizarContinuidadOut] = None
