"""
PATCH input schemas for Visitas types (Inspeccion Obra).

Two input formats are supported:
1. Flat (legacy): `LiquidacionPatchVisitasIn` — direct calculation fields only.
2. Wrapper (current): `LiquidacionPatchVisitasWrapperIn` — `liquidacion_general` + `liquidacion_tipo`
   matching the creation contract structure.

Used by PATCH /liquidaciones/{type}/{id} endpoints for recalculating
calculation inputs (cantidad_visitas, categoria, tarifa_visitas_id) while
keeping the liquidacion in PENDIENTE state.
"""
import uuid
from decimal import Decimal
from typing import Optional

from ninja import Field
from core.types import BaseSchema
from modules.liquidaciones.domain.constants import ModoContinuidadVisitas
from modules.liquidaciones.presentation.schemas.liquidacion_general.general_schemas import (
    ContactoInlineSchema,
    EntidadUpdateSchema,
    ProyectoUpdateSchema,
)


class LiquidacionPatchVisitasIn(BaseSchema):
    """
    PATCH input for Visitas recalculation (flat/legacy format).

    All fields are optional — omitted fields preserve current stored values.

    Business rules:
    - cantidad_visitas: optional; if provided must be >= 1.
    - categoria: optional; if changed without explicit tarifa_visitas_id,
      the correct tariff for that categoria at fecha_registro will be looked up.
    - tarifa_visitas_id: optional; if provided must be vigente at fecha_registro.
    - Only editable when estado == PENDIENTE.
    """
    cantidad_visitas: Optional[int] = Field(
        None,
        ge=1,
        le=9999,
        description="Nueva cantidad de visitas (opcional, preserva actual si se omite)",
    )
    categoria: Optional[str] = Field(
        None,
        description="Nueva categoria (ej. A, B, C) (opcional, preserva actual si se omite)",
    )
    tarifa_visitas_id: Optional[uuid.UUID] = Field(
        None,
        description="ID de la tarifa de visitas a aplicar (opcional, preserva actual si se omite)",
    )


# ── Wrapper schema (liquidacion_general + liquidacion_tipo) ──────────────────

class LiquidacionPatchVisitasGeneralIn(BaseSchema):
    """
    Partial update schema for general fields inside Visitas PATCH wrapper.

    Exposes the same conditional-editing rules as LiquidacionGeneralUpdateIn
    (municipalidad_id and proyecto only editable at revision 1 with no previas).

    Fields are optional — omitted fields preserve current stored values.
    """
    expediente: Optional[str] = Field(None, description="Número de expediente")
    observacion: Optional[str] = Field(None, description="Observación")
    denominacion_de_proyecto: Optional[str] = Field(None, description="Denominación del proyecto (opcional)")
    contacto: Optional[ContactoInlineSchema] = Field(
        None,
        description="Contacto principal (opcional)",
    )
    municipalidad_id: Optional[uuid.UUID] = Field(
        None,
        description="ID de municipalidad (solo editable si revision==1 y sin previas)",
    )
    proyecto: Optional[ProyectoUpdateSchema] = Field(
        None,
        description="Datos del proyecto (parcial, solo editable si revision==1 y sin previas)",
    )


class LiquidacionPatchVisitasDatosIn(BaseSchema):
    """Datos portion of liquidacion_tipo for Visitas PATCH."""
    cantidad_visitas: Optional[int] = Field(
        None,
        ge=1,
        le=9999,
        description="Nueva cantidad de visitas (opcional, preserva actual si se omite)",
    )
    categoria: Optional[str] = Field(
        None,
        description="Nueva categoria (ej. A, B, C) (opcional, preserva actual si se omite)",
    )


class LiquidacionPatchVisitasTarifaIn(BaseSchema):
    """Tarifa portion of liquidacion_tipo for Visitas PATCH."""
    tarifa_visitas_id: uuid.UUID = Field(..., description="ID de la tarifa de visitas a aplicar")


class LiquidacionPatchVisitasContinuidadIn(BaseSchema):
    """
    Bloque OPCIONAL de CONTINUIDAD de visitas en el PATCH de IO, con su
    DISCRIMINADOR DE MODO (`modo`).

    Es la única vía de edición de la continuidad: encender, mantener y apagar
    viajan por la MISMA transacción del PATCH (no hay endpoint dedicado).

    Matriz de transición (Explorer §5.1):

    | Estado persistido | `modo`       | Resultado                        |
    |--------------------|--------------|----------------------------------|
    | Sin continuidad    | `activar`    | Crea la fila; cobra la diferencia|
    | Sin continuidad    | `mantener`   | 400 (no hay nada que mantener)   |
    | Sin continuidad    | `desactivar` | 400 (no hay nada que apagar)     |
    | Con continuidad    | `mantener`   | Actualiza la fila y reaplica     |
    | Con continuidad    | `activar`    | 400 (ya está encendida)          |
    | Con continuidad    | `desactivar` | Elimina la fila; restaura montos |

    Semántica de los campos (todos opcionales):
    - `desactivar` ignora el resto del bloque: solo elimina la fila.
    - `activar` toma los valores enviados; los omitidos valen 0 (crédito 0,
      pendientes 0).
    - `mantener` reemplaza los campos ENVIADOS y conserva los omitidos con el
      valor vigente del registro (semántica replace por campo, nunca se pierde
      el ancla histórica de A ni el crédito por omisión).

    Lo que NO se envía (lo calcula el servidor):
    - `monto_acumulado` / `total_acumulado`: el valor completo del trabajo de B.
    - `total_credito`: la contraparte bruta de `subtotal_credito`, derivada
      aplicando el IGV HISTÓRICO de `fecha_registro` (el mismo del recálculo),
      para que el documento cuadre al centavo.

    El BRUTO declarado (`total_pagado_previa`) es la ENTRADA autoritativa del
    crédito cuando viene: manda sobre `subtotal_credito` (neto) y el servidor
    deriva el par (neto, bruto) con el IGV histórico de `fecha_registro`. Si no
    viene en `mantener`, el crédito persistido queda CONGELADO y solo se
    reprecia el valor completo de B.

    La NO-NEGATIVIDAD del crédito NO se valida aquí a propósito: es una regla de
    NEGOCIO y la resuelve el orquestador con un 400 explícito (mismo criterio
    que la creación de la IO).
    """

    modo: ModoContinuidadVisitas = Field(
        ...,
        description="Transición de la continuidad: 'activar', 'mantener' o 'desactivar'.",
    )
    liquidacion_previa_id: Optional[uuid.UUID] = Field(
        None,
        description="ID de la liquidación de IO previa (A). Si se referencia la previa "
                    "en CAM, el servidor deriva de ella el total de visitas. Si se omite "
                    "en modo 'mantener', se conserva la referencia vigente.",
    )
    visitas_previas_pendientes: Optional[int] = Field(
        None,
        ge=0,
        le=9999,
        description="Cantidad de visitas de la previa que se acreditan (0..9999).",
    )
    visitas_previas_totales: Optional[int] = Field(
        None,
        ge=0,
        le=9999,
        description="Cantidad total de visitas de la previa. Si se referencia la previa "
                    "en CAM, el servidor lo deriva de ella.",
    )
    categoria_previa: Optional[str] = Field(
        None,
        max_length=20,
        description="Categoría de la previa (informativo).",
    )
    subtotal_credito: Optional[Decimal] = Field(
        None,
        max_digits=12,
        decimal_places=2,
        description="Crédito NETO que se descuenta del valor completo de B. El servidor "
                    "valida que no sea negativo (400) y deriva `total_credito` con el "
                    "IGV histórico de `fecha_registro`. Se IGNORA si viene "
                    "`total_pagado_previa`.",
    )
    total_pagado_previa: Optional[Decimal] = Field(
        None,
        gt=Decimal("0"),
        max_digits=12,
        decimal_places=2,
        description="Monto BRUTO pagado en la IO previa, IGV incluido. Si viene, MANDA: "
                    "el servidor deriva el crédito NETO con el IGV histórico de "
                    "`fecha_registro` y `subtotal_credito` (neto) se ignora. Si no "
                    "viene, en modo 'mantener' el crédito persistido queda congelado.",
    )
    observacion: Optional[str] = Field(
        None,
        description="Observación sobre la continuidad.",
    )


class LiquidacionPatchVisitasTipoIn(BaseSchema):
    """
    liquidacion_tipo wrapper for Visitas PATCH — mirrors creation structure.

    All fields optional — omitted fields preserve current stored values.
    """
    datos: Optional[LiquidacionPatchVisitasDatosIn] = Field(
        None,
        description="Datos del cálculo (cantidad_visitas, categoria)",
    )
    tarifa: Optional[LiquidacionPatchVisitasTarifaIn] = Field(
        None,
        description="Tarifa de visitas a aplicar",
    )
    inspector_operacion_id: Optional[uuid.UUID] = Field(
        None,
        description="ID del InspectorOperacion a asociar (opcional, reemplaza el inspector existente)",
    )
    continuidad: Optional[LiquidacionPatchVisitasContinuidadIn] = Field(
        None,
        description="Bloque opcional de continuidad de visitas con su discriminador de "
                    "modo (activar / mantener / desactivar). Ausente = no hay operación "
                    "de continuidad: solo reprecio de B con el crédito congelado.",
    )


class LiquidacionPatchVisitasWrapperIn(BaseSchema):
    """
    Wrapper PATCH input for Visitas types (Inspeccion Obra).

    Supports two input formats:
    1. Wrapper (current/recommended): liquidacion_general + liquidacion_tipo
    2. Flat (legacy/backward compat): cantidad_visitas + categoria + tarifa_visitas_id directly

    Both wrappers are optional; only provided fields are updated.
    The state guard (PENDIENTE) applies to both general and tipo updates.
    PAGADA blocks the entire PATCH regardless of which wrapper is provided.

    When both wrapper and flat fields are provided, wrapper takes precedence.

    CONTINUIDAD: `liquidacion_tipo.continuidad` (con su discriminador `modo`)
    viaja por este mismo PATCH y por la misma transacción. Cuando está
    presente, el PATCH completo queda bloqueado con 409 si la IO tiene RH
    mensual, `DetalleHonorarioInspector` o `RegistroPagoInspector`.
    """
    # Wrapper format (recommended)
    liquidacion_general: Optional[LiquidacionPatchVisitasGeneralIn] = Field(
        None,
        description="Campos generales opcionales (expediente, proyecto, municipalidad, etc.)",
    )
    liquidacion_tipo: Optional[LiquidacionPatchVisitasTipoIn] = Field(
        None,
        description="Campos de cálculo tipo Visitas opcionales (datos, tarifa) — estilo creación",
    )
    # Flat format (legacy/backward compat)
    cantidad_visitas: Optional[int] = Field(
        None,
        ge=1,
        le=9999,
        description="Nueva cantidad de visitas (flat legacy format, opcional)",
    )
    categoria: Optional[str] = Field(
        None,
        description="Nueva categoria (flat legacy format, opcional)",
    )
    tarifa_visitas_id: Optional[uuid.UUID] = Field(
        None,
        description="ID de la tarifa de visitas (flat legacy format, opcional)",
    )
