"""
Presentation schemas — Esquemas HTTP para Liquidaciones Edificaciones.

Usa Ninja Schema para request/response.
"""
import uuid
from ninja import Schema, Field
from typing import Optional, Any, Dict
from pydantic import model_serializer, ConfigDict


class ProyectistaInlineIn(Schema):
    """
    Proyectista inline para crear liquidación de edificaciones.

    Reemplaza proyectistas_ids (lista de UUIDs) por una lista de objetos
    con cip, especialidad_id y descripción opcional.

    Validación:
    - Para cada item se llama al servicio CIP externo
    - Si cualquier CIP falla o no está habilitado (condicion != '1'), se rechaza TODA la operación
    """
    cip: str = Field(..., description="Número de CIP del ingeniero (6 dígitos)")
    especialidad_id: uuid.UUID = Field(..., description="ID de la especialidad (UUID)")
    descripcion: Optional[str] = Field(None, description="Descripción opcional del proyectista")


class ContactoInlineIn(Schema):
    """Contacto inline para crear y asociar a una liquidacion."""

    nombres: str = Field(..., min_length=1, description="Nombres del contacto")
    apellidos: str = Field(..., min_length=1, description="Apellidos del contacto")
    dni: Optional[str] = Field(None, description="DNI del contacto")
    cargo: Optional[str] = Field(None, description="Cargo del contacto")
    telefono: Optional[str] = Field(None, description="Telefono del contacto")
    celular: Optional[str] = Field(None, description="Celular del contacto")
    email: Optional[str] = Field(None, description="Email del contacto")
    direccion: Optional[str] = Field(None, description="Direccion del contacto")
    principal: bool = Field(False, description="Marca este contacto como principal en la liquidacion")
    descripcion: Optional[str] = Field(None, description="Notas de la relacion liquidacion-contacto")


class PrimeraRevisionLiquidacionIn(Schema):
    """Payload para crear primera revisión / nueva liquidación."""
    proyecto_public_id: str = Field(..., description="ID público del proyecto (ej. PROY-2026-00001)")
    municipalidad_id: uuid.UUID = Field(..., description="ID de la municipalidad (UUID)")
    tipo_tramite: str = Field(..., description="Tipo de trámite: OBRA_NUEVA, DEMOLICION, AMPLIACION, REMODELACION, MODIFICACION_LICENCIA, REINTEGRO, PROYECTO_CON_PLANTAS_TIPICAS")
    valor_proyecto: float = Field(..., gt=0, description="Valor del proyecto/obra")
    expediente: Optional[str] = Field(None, description="Número de expediente (opcional)")
    valor_base_calculo: float = Field(..., gt=0, description="Valor base de cálculo. Para tipos normales debe ser igual a valor_proyecto. Para PROYECTO_CON_PLANTAS_TIPICAS puede ser diferente.")
    observacion: Optional[str] = Field(None, description="Observación opcional")
    revisiones_ids: list[str] = Field(default=[], description="IDs de revisiones de edificación a asociar (UUID)")
    # NUEVO: Proyectistas inline con validación CIP
    proyectistas: list[ProyectistaInlineIn] = Field(
        default=[],
        description="Lista de proyectistas inline con CIP. Si se provee, reemplaza completamente a proyectistas_ids."
    )
    # Para backwards compatibility暂时的 - mantener proyectistas_ids pero ya no se usa
    proyectistas_ids: list[uuid.UUID] = Field(
        default=[],
        description="[DEPRECATED] Usar proyectistas (inline con CIP) en su lugar"
    )
    # NUEVO: Delegados IDs
    delegados_ids: list[uuid.UUID] = Field(
        default=[],
        description="IDs de delegados a asociar a la liquidación de edificaciones (UUID)"
    )
    contactos: list[ContactoInlineIn] = Field(
        default=[],
        description="Contactos inline a crear y asociar a la liquidacion"
    )


class PrimeraRevisionLiquidacionWrapperIn(Schema):
    """Wrapper para crear primera revisión — acepta { liquidacion: {...} }."""
    liquidacion: PrimeraRevisionLiquidacionIn


class NuevaRevisionLiquidacionIn(Schema):
    """Payload para crear nueva revisión."""
    liquidacion_previa_id: uuid.UUID = Field(..., description="ID de la liquidación previa (UUID)")
    revisiones_ids: list[uuid.UUID] = Field(
        ...,
        min_length=1,
        max_length=1,
        description="IDs de revisiones de edificación a asociar (UUID). Actualmente se requiere exactamente UNA revisión."
    )
    observacion: Optional[str] = Field(None, description="Observación opcional")
    # NUEVO: Proyectistas inline con validación CIP
    proyectistas: list[ProyectistaInlineIn] = Field(
        default=[],
        description="Lista de proyectistas inline con CIP. Si se omite o está vacía, se heredan de la liquidación previa."
    )
    # Para backwards compatibility暂时的 - mantener proyectistas_ids pero ya no se usa
    proyectistas_ids: list[uuid.UUID] = Field(
        default=[],
        description="[DEPRECATED] Usar proyectistas (inline con CIP) en su lugar"
    )
    # NUEVO: Delegados IDs
    delegados_ids: list[uuid.UUID] = Field(
        default=[],
        description="IDs de delegados a asociar. Si se omite o está vacía, se heredan de la liquidación previa."
    )
    contactos: list[ContactoInlineIn] = Field(
        default=[],
        description="Contactos inline a crear y asociar a la nueva liquidacion"
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
    """Proyectista anidado en edificaciones.

    NOTE: Actualizado para usar PerfilIngeniero referenciado.
    Los campos cip/dni/cap/nombres/apellidos fueron reemplazados por
    perfil_ingeniero_* que se derivan del PerfilIngeniero FK.
    """
    id: uuid.UUID
    perfil_ingeniero_id: Optional[uuid.UUID] = None
    perfil_ingeniero_nombres: Optional[str] = None
    perfil_ingeniero_apellidos: Optional[str] = None
    perfil_ingeniero_cip: Optional[str] = None
    especialidad_id: Optional[uuid.UUID] = None
    especialidad_nombre: Optional[str] = None
    descripcion: Optional[str] = None


class DelegadoOut(Schema):
    """Delegado anidado en edificaciones."""
    id: uuid.UUID
    perfil_ingeniero_id: Optional[uuid.UUID] = None
    perfil_ingeniero_nombres: Optional[str] = None
    perfil_ingeniero_apellidos: Optional[str] = None
    perfil_ingeniero_cip: Optional[str] = None
    especialidad_id: Optional[uuid.UUID] = None
    especialidad_nombre: Optional[str] = None
    tipo: Optional[str] = None


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
    expediente: Optional[str] = None
    observacion: Optional[str]


class EdificacionesOut(Schema):
    """Edificaciones en respuesta snapshot."""
    public_id: str
    numero_revision: int
    tipo_tramite: str
    tramite_accion: str
    proyectistas: list[ProyectistaOut] = Field(default_factory=list)
    delegados: list[DelegadoOut] = Field(default_factory=list)
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


class EspecialidadBasicaOut(Schema):
    """Especialidad básica para revisión vigente."""
    id: uuid.UUID
    nombre: str


class RevisionVigenteOut(Schema):
    """
    Revisión vigente para formulario de primera/new revision.

    NOTE: especialidades es M2M — una revisión puede cubrir múltiples especialidades.
    """
    id: uuid.UUID
    especialidades: list[EspecialidadBasicaOut]
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
    valor_base_calculo: float = Field(..., description="Valor base de cálculo heredado de la liquidación previa")
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
    """Proyectista anidado en edificaciones snapshot.

    NOTE: Actualizado para usar PerfilIngeniero referenciado.
    """
    id: uuid.UUID
    perfil_ingeniero_id: Optional[uuid.UUID] = None
    perfil_ingeniero_nombres: Optional[str] = None
    perfil_ingeniero_apellidos: Optional[str] = None
    perfil_ingeniero_cip: Optional[str] = None
    especialidad_id: Optional[uuid.UUID] = None
    especialidad_nombre: Optional[str] = None
    descripcion: Optional[str] = None


class DelegadoSnapshotOut(Schema):
    """Delegado anidado en edificaciones snapshot."""
    id: uuid.UUID
    perfil_ingeniero_id: Optional[uuid.UUID] = None
    perfil_ingeniero_nombres: Optional[str] = None
    perfil_ingeniero_apellidos: Optional[str] = None
    perfil_ingeniero_cip: Optional[str] = None
    especialidad_id: Optional[uuid.UUID] = None
    especialidad_nombre: Optional[str] = None
    tipo: Optional[str] = None


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
    sub_total: Optional[float] = None
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
    delegados: list[DelegadoSnapshotOut] = Field(default_factory=list)
    revisiones: list[RevisionSnapshotOut]


class LiquidacionSnapshotListItemOut(Schema):
    """Item de lista en respuesta paginada de snapshots."""
    liquidacion_id: uuid.UUID
    public_id: str
    numero_liquidacion: str
    estado: str
    fecha_registro: str
    municipalidad: MunicipalidadesSnapshotOut
    expediente: Optional[str] = None
    observacion: Optional[str]
    proyecto: ProyectoSnapshotOut
    edificaciones: EdificacionesSnapshotListOut
    totales: TotalesSnapshotOut


# ── Cotización / Quote Schemas ──────────────────────────────────────────────────


class CotizacionPrimeraRevisionIn(Schema):
    """Payload para cotizar primera revisión (sin guardar en BD)."""
    proyecto_public_id: str = Field(..., description="ID público del proyecto (ej. PROY-2026-00001)")
    valor_proyecto: float = Field(..., gt=0, description="Valor del proyecto/obra")
    valor_base_calculo: float = Field(..., gt=0, description="Valor base de cálculo. Para tipos normales debe ser igual a valor_proyecto. Para PROYECTO_CON_PLANTAS_TIPICAS puede ser diferente.")
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


# ── Delegados Vigentes Schemas ─────────────────────────────────────────────────


class EspecialidadBasicaDelegadoOut(Schema):
    """Especialidad anidada en delegado vigente."""
    id: uuid.UUID = Field(..., description="ID de la especialidad (UUID)")
    nombre: str = Field(..., description="Nombre de la especialidad")


class DelegadoVigenteOut(Schema):
    """Delegado vigente para selección en formulario de liquidación."""
    id: uuid.UUID = Field(..., description="ID del delegado (UUID)")
    nombre_completo: str = Field(..., description="Nombre completo del ingeniero")
    cip: str = Field(..., description="Número de CIP del ingeniero")
    especialidad: EspecialidadBasicaDelegadoOut = Field(..., description="Especialidad del delegado")
    tipo: str = Field(..., description="Tipo de delegado: titular o alterno")


class DelegadosVigentesOut(Schema):
    """Respuesta de delegados vigentes para una municipalidad."""
    delegados: list[DelegadoVigenteOut] = Field(
        default_factory=list,
        description="Lista de delegados vigentes para la municipalidad seleccionada"
    )


# ── Especialidades Vigentes Schemas ──────────────────────────────────────────


class EspecialidadesVigentesOut(Schema):
    """Respuesta de especialidades vigentes para edificaciones."""
    especialidades: list[EspecialidadBasicaOut] = Field(
        default_factory=list,
        description="Lista de especialidades vigentes del grupo de edificaciones"
    )
