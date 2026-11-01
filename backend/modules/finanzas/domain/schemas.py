"""
Domain schemas — DTOs internos para Finanzas.
"""
from datetime import date
from pydantic import BaseModel, Field
from typing import Optional


class VariablesVigentesResult(BaseModel):
    """
    DTO de resultado para el caso de uso de obtener variables vigentes.

    Incluye los valores de IGV y UIT junto con sus períodos de inicio.
    """
    igv_valor: float = Field(..., description="Tasa IGV (ej. 0.18)")
    igv_periodo_inicio: date = Field(..., description="Fecha inicio período IGV")
    uit_valor: float = Field(..., description="Valor UIT en soles")
    uit_periodo_inicio: date = Field(..., description="Fecha inicio período UIT")

    @classmethod
    def from_igv_uit(cls, igv, uit) -> "VariablesVigentesResult":
        """
        Factory para crear desde modelos IGV y UIT.

        Args:
            igv: Instancia del modelo IGV (o None)
            uit: Instancia del modelo UIT (o None)

        Returns:
            VariablesVigentesResult con valores o errores si no se encuentran
        """
        return cls(
            igv_valor=float(igv.valor) if igv else 0.0,
            igv_periodo_inicio=igv.periodo_inicio if igv else date.min,
            uit_valor=float(uit.valor) if uit else 0.0,
            uit_periodo_inicio=uit.periodo_inicio if uit else date.min,
        )

# ---------------------------------------------------------------------------
# RH Inspector Mensual — contratos de entrada (BaseSchema)
# ---------------------------------------------------------------------------
from core.types import BaseSchema as _BaseSchema


class RHInspectorCotizarItemIn(_BaseSchema):
    """
    Item individual para la cotización del RH mensual del inspector.

    Soporta dos flujos de entrada:
    1. Flujo manual (exp_liqui + cantidad_visitas): Para backward compatibility.
    2. Flujo por candidatas (liquidacion_categoria_visitas_id + cantidad_visitas):
       Permite pasar directamente el ID de la IO seleccionada desde candidates endpoint.

    Se requiere exactamente uno de: exp_liqui O liquidacion_categoria_visitas_id.
    """
    exp_liqui: Optional[str] = Field(None, description="Expediente de la liquidación (flujo manual)")
    liquidacion_categoria_visitas_id: Optional[str] = Field(
        None,
        description="ID de la LiquidacionPorCategoriaVisitas (flujo por candidatas)",
    )
    cantidad_visitas: int = Field(..., ge=1, description="Cantidad de inspecciones a liquidar")
    periodo: Optional[int] = Field(None, description="Año de la LiquidacionInspector")
    mes: Optional[int] = Field(None, ge=1, le=12, description="Mes de la LiquidacionInspector")


class RHInspectorCotizarIn(_BaseSchema):
    """Payload de entrada para cotizar/crear el RH mensual del inspector."""
    cip: str
    periodo: int = Field(..., ge=2000, le=2100, description="Año del periodo")
    mes: int = Field(..., ge=1, le=12, description="Mes del periodo (1-12)")
    items: list[RHInspectorCotizarItemIn]


# ---------------------------------------------------------------------------
# RH Delegado Mensual — contratos de entrada (BaseSchema)
# ---------------------------------------------------------------------------


class RHDelegadoCotizarItemIn(_BaseSchema):
    """
    Item individual para la cotización del RH mensual del delegado.

    usa liquidacion_general_id + especialidad_revision_id (de la candidata)
    para calcular imp_bruto directamente desde LiquidacionPorcentajeObraDetalle,
    sin requerir que LiquidacionDelegado exista aún.

    Los campos periodo, mes, dictamen_revision, fecha_presentacion y fecha_revision
    se usan en crear() para persistir en LiquidacionDelegado.
    """
    liquidacion_general_id: str  # UUID string de CandidataOut.id
    especialidad_revision_id: str  # UUID string de CandidataOut.especialidad_candidata.id
    delegado_operacion_id: Optional[str] = None  # UUID string de DelegadoOperacion — deducido de top-level en cotizar
    numero_rh: Optional[str] = None  # Número de Orden/RH — se usa en LiquidacionDelegado.numero_rh
    periodo: Optional[int] = None  # Año — se usa en LiquidacionDelegado.periodo
    mes: Optional[int] = None  # Mes (1-12) — se usa en LiquidacionDelegado.mes
    dictamen_revision: Optional[str] = None  # se usa en LiquidacionDelegado.dictamen_revision
    fecha_presentacion: Optional[date] = None  # se usa en LiquidacionDelegado.fecha_presentacion
    fecha_revision: Optional[date] = None  # se usa en LiquidacionDelegado.fecha_revision


class RHDelegadoCotizarIn(_BaseSchema):
    """Payload de entrada para cotizar/crear el RH mensual del delegado."""
    cip: str
    periodo: int = Field(..., ge=2000, le=2100, description="Año del periodo")
    mes: int = Field(..., ge=1, le=12, description="Mes del periodo (1-12)")
    delegado_operacion_id: str = Field(
        ...,
        description="UUID string de la DelegadoOperacion (periodo vigente) que define la tasa a aplicar",
    )
    items: list[RHDelegadoCotizarItemIn]


# ---------------------------------------------------------------------------
# RH Delegado Mensual — PATCH (sincronización del conjunto final)
# ---------------------------------------------------------------------------


class RHDelegadoActualizarItemIn(_BaseSchema):
    """
    Item del conjunto final de detalles (PATCH) del RH mensual del delegado.

    Reproduce la forma de selección de la cotización y agrega el identificador
    estable del detalle (``detalle_id``) que permite conservar la fila ya
    persistida:

    - ``detalle_id`` presente → la fila se CONSERVA (se recalcula con la tasa
      congelada del recibo).
    - ``detalle_id`` ausente → la fila se AGREGA (se crea la asignación RH si
      no existía).

    Los campos de metadata de la asignación (``numero_rh``, ``periodo``,
    ``mes``, ``dictamen_revision``, ``fecha_presentacion``,
    ``fecha_revision``) NUNCA modifican una asignación ya existente: si el
    payload intenta cambiarlos sobre un detalle retenido, el flujo responde
    409 y no altera ningún recibo.
    """
    liquidacion_general_id: str  # UUID string de la liquidación seleccionada
    especialidad_revision_id: str  # UUID string de la especialidad de revisión
    detalle_id: Optional[str] = Field(
        None,
        description=(
            "ID del DetalleHonorarioDelegado persistido. Si viene, la fila se "
            "conserva; si no, la fila se agrega al conjunto final."
        ),
    )
    numero_rh: Optional[str] = Field(None, description="Número de Orden/RH de la asignación")
    periodo: Optional[int] = Field(None, description="Año de la asignación")
    mes: Optional[int] = Field(None, ge=1, le=12, description="Mes de la asignación (1-12)")
    dictamen_revision: Optional[str] = Field(None, description="Dictamen de revisión de la asignación")
    fecha_presentacion: Optional[date] = Field(None, description="Fecha de presentación de la asignación")
    fecha_revision: Optional[date] = Field(None, description="Fecha de revisión de la asignación")


class RHDelegadoActualizarIn(_BaseSchema):
    """
    Payload de entrada para sincronizar (PATCH) el RH mensual del delegado.

    El conjunto de ``items`` es el conjunto FINAL de detalles del recibo: los
    detalles persistidos que no aparecen en el payload se retiran.
    """
    cip: str = Field(..., description="CIP del delegado dueño del recibo")
    periodo: int = Field(..., ge=2000, le=2100, description="Año del periodo")
    mes: int = Field(..., ge=1, le=12, description="Mes del periodo (1-12)")
    delegado_operacion_id: str = Field(
        ...,
        description="UUID string de la DelegadoOperacion que define la tasa a aplicar",
    )
    items: list[RHDelegadoActualizarItemIn]


# ---------------------------------------------------------------------------
# RH Inspector Mensual — PATCH (sincronización del conjunto final)
# ---------------------------------------------------------------------------


class RHInspectorActualizarItemIn(_BaseSchema):
    """
    Item del conjunto final de detalles (PATCH) del RH mensual del inspector.

    - ``detalle_id`` presente → la fila se CONSERVA (se re-cotiza con el saldo
      del recibo excluido de su propio balance).
    - ``detalle_id`` ausente → la fila se AGREGA.

    Las fechas de revisión y presentación se validan como rango: una revisión
    posterior a la presentación es un rango invertido (422).
    """
    exp_liqui: Optional[str] = Field(None, description="Expediente de la liquidación")
    liquidacion_categoria_visitas_id: Optional[str] = Field(
        None,
        description="ID de la LiquidacionPorCategoriaVisitas (IO) seleccionada",
    )
    cantidad_visitas: int = Field(..., ge=1, description="Cantidad de inspecciones a liquidar")
    periodo: Optional[int] = Field(None, description="Año del periodo del item")
    mes: Optional[int] = Field(None, ge=1, le=12, description="Mes del periodo del item")
    detalle_id: Optional[str] = Field(
        None,
        description=(
            "ID del DetalleHonorarioInspector persistido. Si viene, la fila se "
            "conserva; si no, la fila se agrega al conjunto final."
        ),
    )
    fecha_revision: Optional[date] = Field(None, description="Fecha de revisión (ISO)")
    fecha_presentacion: Optional[date] = Field(None, description="Fecha de presentación (ISO)")


class RHInspectorActualizarIn(_BaseSchema):
    """
    Payload de entrada para sincronizar (PATCH) el RH mensual del inspector.

    El conjunto de ``items`` es el conjunto FINAL de detalles del recibo: los
    detalles persistidos que no aparecen en el payload se retiran.
    """
    cip: str = Field(..., description="CIP del inspector dueño del recibo")
    periodo: int = Field(..., ge=2000, le=2100, description="Año del periodo")
    mes: int = Field(..., ge=1, le=12, description="Mes del periodo (1-12)")
    items: list[RHInspectorActualizarItemIn]


# ---------------------------------------------------------------------------
# RH Reparticion Estacional — contratos de entrada
# ---------------------------------------------------------------------------


class RHReparticionEstacionalGeneralIn(_BaseSchema):
    """
    Bloque general de entrada de la RH Repartición Estacional.

    Fields shared by the three operations (cotizar / crear / actualizar).
    Defined once and composed by each operation schema so the three
    endpoints can never drift apart (contract/SCHEMA_DRY_INTENTION.md).
    """

    especialidad_revision_id: str = Field(
        ..., description="UUID string de EspecialidadRevision"
    )
    periodo: int = Field(..., ge=2000, le=2100, description="Año de la repartición")
    mes_desde: int = Field(..., ge=1, le=12, description="Mes inicial del rango")
    mes_hasta: int = Field(..., ge=1, le=12, description="Mes final del rango")
    delegado_ids: list[str] = Field(
        ..., description="Lista de UUIDs de Delegado seleccionados"
    )


class RHReparticionEstacionalCotizarIn(RHReparticionEstacionalGeneralIn):
    """
    Payload para cotizar una repartición estacional.

    No persiste nada — solo calcula y retorna preview.
    """


class RHReparticionEstacionalCrearIn(RHReparticionEstacionalGeneralIn):
    """
    Payload para crear una repartición estacional (cotizar + persistir).
    """


class RHReparticionEstacionalActualizarIn(RHReparticionEstacionalGeneralIn):
    """
    Payload para editar una repartición estacional persistida (PATCH).

    Mismo bloque general que cotizar/crear: la edición recalcula la
    distribución completa con la misma lógica de cálculo y reemplaza el
    conjunto final de detalles.
    """
