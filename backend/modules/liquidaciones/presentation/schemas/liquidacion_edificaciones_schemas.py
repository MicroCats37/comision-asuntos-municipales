"""
Presentation schemas — Esquemas HTTP para Liquidaciones Edificaciones.

Usa Ninja Schema para request/response.
"""
import uuid
from ninja import Schema, Field
from typing import Optional, Any, Dict
from pydantic import model_serializer, ConfigDict


class PrimeraRevisionLiquidacionIn(Schema):
    """Payload para crear primera revisión / nueva liquidación."""
    proyecto_public_id: str = Field(..., description="ID público del proyecto (ej. PROY-2026-00001)")
    municipalidad_id: uuid.UUID = Field(..., description="ID de la municipalidad (UUID)")
    tipo_tramite: str = Field(..., description="Tipo de trámite: OBRA_NUEVA, DEMOLICION, AMPLIACION, REMODELACION, MODIFICACION_LICENCIA")
    valor_proyecto: float = Field(..., gt=0, description="Valor del proyecto/obra")
    # expediente fue removido del dominio
    observacion: Optional[str] = Field(None, description="Observación opcional")
    revisiones_ids: list[str] = Field(default=[], description="IDs de revisiones de edificación a asociar (UUID)")
    proyectistas_ids: list[uuid.UUID] = Field(
        default=[],
        description="IDs de proyectistas a asociar a la liquidación de edificaciones (UUID)"
    )


class PrimeraRevisionLiquidacionWrapperIn(Schema):
    """Wrapper para crear primera revisión — acepta { liquidacion: {...} }."""
    liquidacion: PrimeraRevisionLiquidacionIn


class NuevaRevisionLiquidacionIn(Schema):
    """Payload para crear nueva revisión."""
    liquidacion_previa_id: uuid.UUID = Field(..., description="ID de la liquidación previa (UUID)")
    revisiones_ids: list[uuid.UUID] = Field(..., min_length=1, description="IDs de revisiones de edificación a asociar (UUID), no puede estar vacío")
    observacion: Optional[str] = Field(None, description="Observación opcional")
    proyectistas_ids: list[uuid.UUID] = Field(
        default=[],
        description="IDs de proyectistas a asociar. Si se omite o está vacía, se heredan de la liquidación previa."
    )
    # valor_proyecto: se obtiene de la liquidación previa
    # expediente: fue removido del dominio


class TarifaOut(Schema):
    """Tarifa dentro de revisión."""
    id: uuid.UUID
    derecho_minimo: float
    derecho_maximo: Optional[float]
    porcentaje_minimo_uit: float


class EspecialidadOut(Schema):
    """Especialidad dentro de revisión."""
    id: uuid.UUID
    nombre: str


class RevisionOut(Schema):
    """Revisión dentro de edificaciones."""
    id: uuid.UUID
    especialidad: str
    tarifa: TarifaOut
    monto_base: float
    cobra: bool


class TotalesOut(Schema):
    """Totales de la liquidación."""
    subtotal: float
    igv: float
    total: float
    liquidacion_total: float
    total_a_pagar: float


class EntidadOut(Schema):
    """Entidad anidada en proyecto."""
    id: Optional[uuid.UUID]
    tipo: Optional[str]
    nombre: Optional[str]
    ruc: Optional[str]


class ProyectistaOut(Schema):
    """Proyectista anidado en edificaciones."""
    id: uuid.UUID
    cip: Optional[str]
    dni: Optional[str]
    cap: Optional[str]
    nombres: str
    apellidos: str


class ProyectoOut(Schema):
    """Proyecto anidado en liquidación."""
    id: uuid.UUID
    public_id: str
    nombre: str
    direccion: Optional[str]
    valor_proyecto: float
    entidad: Optional[EntidadOut] = None
    # NOTE: proyectista ya no está en proyecto — ahora vive en LiquidacionEdificaciones.proyectistas


class ProvinciaBasicSnapshotOut(Schema):
    """Provincia básica para anidamiento."""
    id: uuid.UUID
    nombre: str


class DistritoBasicSnapshotOut(Schema):
    """Distrito básico para anidamiento."""
    id: uuid.UUID
    nombre: str
    provincia: Optional[ProvinciaBasicSnapshotOut] = None


class MunicipalidadesSnapshotOut(Schema):
    """Municipalidad anidada."""
    id: uuid.UUID
    nombre: str
    codigo: Optional[str] = None
    provincia: Optional[ProvinciaBasicSnapshotOut] = None
    distrito: Optional[DistritoBasicSnapshotOut] = None


class LiquidacionOut(Schema):
    """Liquidación en respuesta snapshot."""
    id: uuid.UUID
    public_id: str
    estado: str
    fecha_creacion: str
    proyecto: ProyectoOut
    municipalidad: MunicipalidadesSnapshotOut
    # expediente fue removido del dominio
    observacion: Optional[str]


class EdificacionesOut(Schema):
    """Edificaciones en respuesta snapshot."""
    public_id: str
    numero_revision: int
    tipo_tramite: str
    tramite_accion: str
    proyectistas: list[ProyectistaOut] = Field(default_factory=list)
    revisiones: list[RevisionOut]


class LiquidacionSnapshotOut(Schema):
    """Respuesta completa de snapshot de liquidación."""
    liquidacion: LiquidacionOut
    edificaciones: EdificacionesOut
    totales: TotalesOut


class LiquidacionSnapshotDataOut(Schema):
    """
    Schema flexible que permite cualquier campo JSON arbitrario.
    Se usa en GET /{liquidacion_id} para retornar el JSON completo
    almacenado en LiquidacionSnapshot.data sin proyección.
    """
    model_config = ConfigDict(extra='allow')


class VariablesFinancierasOut(Schema):
    """Variables financieras para mostrar en formulario."""
    igv_valor: float = Field(..., description="Tasa IGV (ej. 0.18)")
    igv_periodo_inicio: str = Field(..., description="Fecha inicio período IGV")
    uit_valor: float = Field(..., description="Valor UIT en soles")
    uit_periodo_inicio: str = Field(..., description="Fecha inicio período UIT")


class RevisionVigenteOut(Schema):
    """Revisión vigente para formulario de primera/new revision."""
    id: uuid.UUID
    especialidad_id: uuid.UUID
    especialidad_nombre: str
    tarifa_id: uuid.UUID
    porcentaje_liquidacion: float
    derecho_minimo: float
    derecho_maximo: Optional[float]
    porcentaje_minimo_uit: float
    habilitada: bool


class RevisionesVigentesOut(Schema):
    """Lista de revisiones vigentes para formulario."""
    revisiones: list[RevisionVigenteOut]


class LiquidacionEdificacionesListItemOut(Schema):
    """Item de lista en respuesta paginada."""
    id: uuid.UUID
    numero_revision: int
    estado: str
    valor_proyecto: float
    proyecto_public_id: str
    proyecto_denominacion: str
    fecha_registro: str
    total: float
    # expediente fue removido del dominio


class NuevaRevisionFormularioOut(Schema):
    """Respuesta de preparación de formulario para nueva revisión."""
    liquidacion_previa_id: uuid.UUID
    numero_revision: int
    cobra: bool
    proyecto_id: uuid.UUID
    proyecto_public_id: str
    proyecto_nombre: str
    valor_proyecto: float
    revisiones_vigentes: list[RevisionVigenteOut]
    proyectistas_actuales: list[ProyectistaOut] = Field(
        default_factory=list,
        description="Proyectistas heredados de la liquidación previa para prefijado en formulario"
    )


# ── Snapshot List Schemas (para endpoint GET /snapshots) ────────────────────────────────────


class TarifaSnapshotOut(Schema):
    """Tarifa anidada en revisión snapshot."""
    id: uuid.UUID
    derecho_minimo: float
    derecho_maximo: Optional[float]
    porcentaje_minimo_uit: float


class RevisionSnapshotOut(Schema):
    """Revisión anidada en edificación snapshot.
    
    NOTE: numero_revision fue removido de cada revisión — solo existe en nivel edificaciones.
    """
    id: uuid.UUID
    especialidad: str
    tarifa: TarifaSnapshotOut
    monto_base: float
    cobra: bool


class EntidadSnapshotOut(Schema):
    """Entidad anidada en proyecto snapshot."""
    id: Optional[uuid.UUID]
    tipo: Optional[str]
    nombre: Optional[str]
    ruc: Optional[str]


class ProyectistaSnapshotOut(Schema):
    """Proyectista anidado en edificaciones snapshot."""
    id: uuid.UUID
    cip: Optional[str]
    dni: Optional[str]
    cap: Optional[str]
    nombres: str
    apellidos: str


class ProyectoSnapshotOut(Schema):
    """Proyecto anidado en liquidación snapshot list."""
    id: uuid.UUID
    public_id: str
    nombre: str
    direccion: Optional[str]
    valor_proyecto: float
    entidad: Optional[EntidadSnapshotOut] = None
    # NOTE: proyectista ya no está en proyecto — ahora vive en LiquidacionEdificaciones.proyectistas


class TotalesSnapshotOut(Schema):
    """Totales anidados en snapshot list."""
    subtotal: float
    igv: float
    total: float
    liquidacion_total: float
    total_a_pagar: float


class EdificacionesSnapshotListOut(Schema):
    """Edificaciones anidado en snapshot list item."""
    public_id: str
    numero_revision: int
    tipo_tramite: str
    tramite_accion: str
    proyectistas: list[ProyectistaSnapshotOut] = Field(default_factory=list)
    revisiones: list[RevisionSnapshotOut]


class LiquidacionSnapshotListItemOut(Schema):
    """Item de lista en respuesta paginada de snapshots."""
    liquidacion_id: uuid.UUID
    public_id: str
    numero_liquidacion: str
    estado: str
    fecha_registro: str
    municipalidad: MunicipalidadesSnapshotOut
    # expediente fue removido del dominio
    observacion: Optional[str]
    proyecto: ProyectoSnapshotOut
    edificaciones: EdificacionesSnapshotListOut
    totales: TotalesSnapshotOut


# ── Cotización / Quote Schemas ──────────────────────────────────────────────────


class CotizacionPrimeraRevisionIn(Schema):
    """Payload para cotizar primera revisión (sin guardar en BD)."""
    proyecto_public_id: str = Field(..., description="ID público del proyecto (ej. PROY-2026-00001)")
    valor_proyecto: float = Field(..., gt=0, description="Valor del proyecto/obra")
    # No requiere municipalidad_id, tipo_tramite, ni revisiones_ids
    # municipalidad_id se infiere del proyecto
    # tipo_tramite se infiere del proyecto
    # revisiones_ids usa selección por defecto (vigentes) si no se envía


class CotizacionPrimeraRevisionWrapperIn(Schema):
    """Wrapper para cotizar primera revisión — acepta { liquidacion: {...} }."""
    liquidacion: CotizacionPrimeraRevisionIn


class CotizacionNuevaRevisionIn(Schema):
    """Payload para cotizar nueva revisión (sin guardar en BD)."""
    liquidacion_previa_id: uuid.UUID = Field(..., description="ID de la liquidación previa (UUID)")
    revisiones_ids: list[uuid.UUID] = Field(..., min_length=1, description="IDs de revisiones de edificación a asociar (UUID), no puede estar vacío")
    # No requiere valor_proyecto (se obtiene de la liquidación previa)


class CotizacionTarifaOut(Schema):
    """Tarifa dentro de revisión en respuesta de cotización."""
    id: uuid.UUID
    derecho_minimo: float
    derecho_maximo: Optional[float]
    porcentaje_minimo_uit: float


class CotizacionRevisionOut(Schema):
    """Revisión en respuesta de cotización (sin numero_revision duplicado)."""
    id: uuid.UUID
    especialidad: str
    tarifa: CotizacionTarifaOut
    monto_base: float
    cobra: bool


class CotizacionTotalesOut(Schema):
    """Totales en respuesta de cotización."""
    subtotal: float
    igv: float
    total: float
    liquidacion_total: float
    total_a_pagar: float


class CotizacionMetadataOut(Schema):
    """Metadata adicional en respuesta de cotización."""
    igv_valor: float
    uit_valor: float
    cobra: bool


class CotizacionQuoteOut(Schema):
    """Respuesta completa de cotización sin duplicación de numero_revision."""
    numero_revision: int = Field(..., description="Número de revisión calculado")
    revisiones: list[CotizacionRevisionOut] = Field(..., description="Lista de revisiones calculadas")
    totales: CotizacionTotalesOut
    metadata: CotizacionMetadataOut

    @model_serializer(mode='wrap')
    def serialize_model(self, handler):
        """Rename metadata to _metadata in JSON output per API contract."""
        data = handler(self)
        data['_metadata'] = data.pop('metadata')
        return data
