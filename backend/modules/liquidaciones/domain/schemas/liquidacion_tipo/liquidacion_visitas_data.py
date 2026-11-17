from decimal import Decimal
from typing import Any, Optional
import uuid

from pydantic import BaseModel, ConfigDict


class DatosVisitas(BaseModel):
    cantidad_visitas: int
    categoria: Optional[str] = None  # nullable for CATEGORIA=0 legacy records


class TarifaVisitas(BaseModel):
    # Nullable: normal path requires valid tarifa_visitas_id;
    # legacy/manual path (cotizacion_legacy with no tariff) passes None.
    tarifa_visitas_id: Optional[str] = None


class ContinuidadVisitasData(BaseModel):
    """
    Bloque opcional de CONTINUIDAD de visitas de Inspección de Obra.

    Viaja ya VALIDADO y NORMALIZADO por el orquestador: las referencias a la
    liquidación previa se resuelven a objetos ORM y los montos derivados por el
    servidor (total_credito) ya están calculados.

    Semántica:
    - `monto_acumulado` / `total_acumulado` NO se reciben: los calcula el
      servidor a partir de la tarifa de B (contrato del cambio).
    - `subtotal_credito` lo confirma el usuario (crédito de la previa por las
      visitas no realizadas) y `total_credito` lo deriva el servidor.
    - `total_pagado_previa` es el BRUTO pagado en la IO previa (IGV incluido)
      DECLARADO por el cliente. Si viene, MANDA: el servidor deriva el par
      (`subtotal_credito`, `total_credito`) con el IGV efectivo de la ruta y
      el neto declarado se ignora. Si no viene, se conserva el camino vigente
      por `subtotal_credito` (neto).

    `liquidacion_previa` es una instancia ORM (`LiquidacionGeneral`) resuelta
    por el orquestador: se declara como `Any` con `arbitrary_types_allowed`,
    igual que el contexto del registro legacy
    (`domain/schemas/liquidacion_legacy/legacy_registro_data.py`).
    """

    model_config = ConfigDict(arbitrary_types_allowed=True)

    liquidacion_previa: Optional[Any] = None
    liquidacion_previa_id: Optional[str] = None
    subtotal_credito: Decimal = Decimal("0")
    total_credito: Decimal = Decimal("0")
    total_pagado_previa: Optional[Decimal] = None
    visitas_previas_totales: Optional[int] = None
    visitas_previas_pendientes: Optional[int] = None
    categoria_previa: Optional[str] = None
    observacion: Optional[str] = None


class LiquidacionCategoriaVisitasData(BaseModel):
    datos: DatosVisitas
    tarifa: TarifaVisitas
    continuidad: Optional[ContinuidadVisitasData] = None


class ContinuidadVisitasPatchData(BaseModel):
    """
    Bloque de continuidad NORMALIZADO del PATCH de Inspección de Obra.

    Es el equivalente de `ContinuidadVisitasData` para el camino de EDICIÓN:
    todavía no está validado, solo lleva los campos que el cliente envió
    (los omitidos llegan en `None`).

    El orquestador lo fusiona con el estado persistido (modo `mantener`),
    lo valida con las mismas reglas de negocio de la creación y lo convierte
    en `ContinuidadVisitasData` antes de escribir.

    - `liquidacion_previa_id`: referencia a la liquidación previa (A). `None`
      significa "no informado" (no "quitar la referencia"): en modo `mantener`
      se conserva la referencia vigente.
    - `subtotal_credito`: crédito NETO. `None` significa "no informado": en
      modo `mantener` se conserva el crédito vigente; en modo `activar` vale 0.
    - `total_pagado_previa`: BRUTO pagado en la IO previa (IGV incluido)
      DECLARADO por el cliente. Si viene, MANDA sobre `subtotal_credito`: el
      servidor re-deriva el par (neto, bruto) con el IGV efectivo de la ruta.
      `None` significa "no informado": en modo `mantener` el crédito vigente
      queda CONGELADO (no se re-deriva).
    - `total_credito`: BRUTO del crédito CONGELADO. Lo lleva el orquestador
      desde la fila vigente en modo `mantener` para que el crédito no se
      re-derive con otro IGV. El cliente NUNCA lo envía (lo calcula el
      servidor).
    """

    liquidacion_previa_id: Optional[uuid.UUID] = None
    visitas_previas_totales: Optional[int] = None
    visitas_previas_pendientes: Optional[int] = None
    categoria_previa: Optional[str] = None
    subtotal_credito: Optional[Decimal] = None
    total_credito: Optional[Decimal] = None
    total_pagado_previa: Optional[Decimal] = None
    observacion: Optional[str] = None


class ContinuidadCreditoVisitas(BaseModel):
    """
    CRÉDITO de la continuidad que se entrega al MOTOR de Visitas.

    Es el INPUT del crédito del motor (`CotizacionVisitasContexto`) y aplica
    la REGLA ÚNICA de precedencia (DD-5/DD-6):

    1. `total_pagado_previa` (BRUTO declarado) → MANDA: el motor deriva el
       par (crédito NETO, crédito BRUTO) con el IGV efectivo de la ruta.
    2. `credito_neto` (NETO ya resuelto) → se usa tal cual; el bruto se toma
       de `credito_bruto` si viene (crédito CONGELADO) o se deriva.
    3. Sin crédito → (0, 0).

    Lo consumen el flujo de alta y el servicio de PATCH: los dos entregan al
    motor EXACTAMENTE el mismo crédito que resolvió el orquestador, de modo
    que lo cotizado y lo persistido coinciden al céntavo.
    """

    total_pagado_previa: Optional[Decimal] = None   # BRUTO declarado (prioridad 1)
    credito_neto: Optional[Decimal] = None           # NETO ya resuelto (prioridad 2)
    credito_bruto: Optional[Decimal] = None          # BRUTO del crédito congelado (prioridad 2)
