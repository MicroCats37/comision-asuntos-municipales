"""
Presentation schemas — Esquemas HTTP para Liquidaciones Edificaciones.

Usa BaseSchema del proyecto para heredar sanitize de strings vacíos.
"""
import uuid
from ninja import Field
from typing import Optional, Any, Dict
from pydantic import model_serializer, ConfigDict
from core.types import BaseSchema


class ProyectistaInlineIn(BaseSchema):
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


class ContactoInlineIn(BaseSchema):
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


class EntidadInlineIn(BaseSchema):
    """
    Entidad inline para crear proyecto inline.

    Se usa dentro de ProyectoInlineIn para crear o encontrar
    una Entidad por numero_documento (upsert).

    Validación:
    - tipo_documento: RUC o DNI
    - numero_documento: 11 dígitos para RUC, 8 dígitos para DNI
    - razon_social: requerida
    - NOTA: nombre_propietario NO pertenece a Entidad — pertenece a proyecto_inline
    """
    tipo_documento: str = Field(
        ...,
        description="Tipo de documento: RUC o DNI"
    )
    numero_documento: str = Field(
        ...,
        min_length=1,
        description="Número de documento (RUC 11 dígitos o DNI 8 dígitos)"
    )
    razon_social: str = Field(
        ...,
        min_length=1,
        max_length=255,
        description="Razón social para RUC o nombre completo para DNI"
    )


class ProyectoInlineIn(BaseSchema):
    """
    Proyecto inline para crear durante primera revisión de liquidación.

    Se usa cuando el proyecto no existe y se crea en línea.
    Mutuamente excluyente con proyecto_public_id.

    Validación XOR (exactamente uno) se hace en el orquestador.
    """
    denominacion: str = Field(..., min_length=1, max_length=255, description="Denominación del proyecto")
    direccion: Optional[str] = Field(None, max_length=512, description="Dirección del proyecto")
    distrito_id: Optional[uuid.UUID] = Field(None, description="ID del distrito (UUID)")
    nombre_propietario: str = Field(
        ...,
        max_length=255,
        description="Nombre del propietario o representante legal (requerido, no viene de SUNAT/RENIEC)"
    )
    entidad: EntidadInlineIn = Field(
        ...,
        description="Entidad inline con tipo_documento, numero_documento y razon_social. Se hace upsert por numero_documento."
    )


class PrimeraRevisionLiquidacionIn(BaseSchema):
    """Payload para crear primera revisión / nueva liquidación."""
    # Mutuamente excluyentes con proyecto_inline: exactamente uno debe estar presente
    proyecto_public_id: Optional[str] = Field(
        None,
        description="ID público del proyecto existente (ej. PROY-2026-00001). Mutuamente excluyente con proyecto_inline."
    )
    proyecto_inline: Optional[ProyectoInlineIn] = Field(
        None,
        description="Datos del proyecto inline a crear. Mutuamente excluyente con proyecto_public_id."
    )
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
    # NUEVO Fase 6: Tarifas IDs (array, exactamente 1 elemento para esta fase)
    # REQUERIDO: frontend siempre envía tarifas_ids, backend ya no hace auto-selección.
    # Validación: debe tener exactamente 1 elemento (min_length=1, max_length=1).
    tarifas_ids: list[uuid.UUID] = Field(
        ...,
        min_length=1,
        max_length=1,
        description="IDs de tarifas a aplicar en la liquidación. Para esta fase debe ser exactamente 1."
    )
    # NOTE: delegados_ids fue eliminado de PrimeraRevisionLiquidacionIn (Fase 4).
    # Los delegados se manejarán en un endpoint POST posterior separate.
    contactos: list[ContactoInlineIn] = Field(
        default=[],
        description="Contactos inline a crear y asociar a la liquidacion"
    )


class PrimeraRevisionLiquidacionWrapperIn(BaseSchema):
    """Wrapper para crear primera revisión — acepta { liquidacion: {...} }."""
    liquidacion: PrimeraRevisionLiquidacionIn


class NuevaRevisionLiquidacionIn(BaseSchema):
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
    # NUEVO Fase 3: Tarifas IDs (para consistencia futura — por ahora no se usa en nueva revisión)
    tarifas_ids: list[uuid.UUID] = Field(
        default=[],
        description="IDs de tarifas a aplicar. Para esta fase debe ser exactamente 1 si se proporciona."
    )
    contactos: list[ContactoInlineIn] = Field(
        default=[],
        description="Contactos inline a crear y asociar a la nueva liquidacion"
    )
    # valor_proyecto: se obtiene de la liquidación previa
    # expediente: fue removido del dominio


class TarifaOut(BaseSchema):
    """Tarifa dentro de revisión."""
    id: uuid.UUID
    derecho_minimo: float
    derecho_maximo: Optional[float]
    porcentaje_minimo_uit: float


class EspecialidadOut(BaseSchema):
    """Especialidad dentro de revisión."""
    id: uuid.UUID
    nombre: str


class RevisionOut(BaseSchema):
    """Revisión dentro de edificaciones."""
    id: uuid.UUID
    especialidades: list[EspecialidadOut]
    tarifa: TarifaOut
    monto_base: float
    cobra: bool


class TotalesOut(BaseSchema):
    """Totales de la liquidación."""
    subtotal: float
    igv: float
    total: float
    liquidacion_total: float
    total_a_pagar: float


class EntidadOut(BaseSchema):
    """Entidad anidada en proyecto."""
    id: Optional[uuid.UUID]
    tipo: Optional[str]
    nombre: Optional[str]
    ruc: Optional[str]


class ProyectistaOut(BaseSchema):
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


class DelegadoOut(BaseSchema):
    """Delegado anidado en edificaciones."""
    id: uuid.UUID
    perfil_ingeniero_id: Optional[uuid.UUID] = None
    perfil_ingeniero_nombres: Optional[str] = None
    perfil_ingeniero_apellidos: Optional[str] = None
    perfil_ingeniero_cip: Optional[str] = None
    especialidad_id: Optional[uuid.UUID] = None
    especialidad_nombre: Optional[str] = None
    tipo: Optional[str] = None


class ProyectoOut(BaseSchema):
    """Proyecto anidado en liquidación."""
    id: uuid.UUID
    public_id: str
    nombre: str
    direccion: Optional[str]
    valor_proyecto: float
    entidad: Optional[EntidadOut] = None
    # NOTE: proyectista ya no está en proyecto — ahora vive en LiquidacionEdificaciones.proyectistas


# ── Flat Single-Object Output Schema (Phase 1) ──────────────────────────────────


class ProvinciaBasicOut(BaseSchema):
    """Provincia básica para anidamiento."""
    id: uuid.UUID
    nombre: str


class DistritoBasicOut(BaseSchema):
    """Distrito básico para anidamiento."""
    id: uuid.UUID
    nombre: str
    provincia: Optional[ProvinciaBasicOut] = None


class MunicipalidadOut(BaseSchema):
    """Municipalidad anidada en LiquidacionEdificacionOut."""
    id: uuid.UUID
    nombre: str
    codigo: Optional[str] = None
    provincia: Optional[ProvinciaBasicOut] = None
    distrito: Optional[DistritoBasicOut] = None


class ValoresOut(BaseSchema):
    """Valores financieros en LiquidacionEdificacionOut."""
    subtotal: float
    igv: float
    total: float
    total_a_pagar: float


class ContactoEdificacionOut(BaseSchema):
    """Contacto anidado en LiquidacionEdificacionOut."""
    id: uuid.UUID
    nombres: Optional[str] = None
    apellidos: Optional[str] = None
    dni: Optional[str] = None
    cargo: Optional[str] = None
    telefono: Optional[str] = None
    celular: Optional[str] = None
    email: Optional[str] = None
    direccion: Optional[str] = None
    principal: bool = False
    descripcion: Optional[str] = None


class LiquidacionEdificacionOut(BaseSchema):
    """
    Schema HTTP de respuesta para endpoints de lectura y creación de liquidaciones
    de edificaciones (excepto cotizar).

    Estructura plana con objetos anidados para ``proyecto``, ``entidad``,
    ``municipalidad``, ``valores``, ``proyectistas``, ``delegados``, ``contactos``
    y ``revisiones``.

    Campos:
        id, public_id, estado, fecha_registro, expediente, observacion,
        numero_revision, tipo_tramite, tramite_accion,
        proyecto, entidad, municipalidad, valores,
        proyectistas, delegados, contactos, revisiones,
        subtotal, igv, total, total_a_pagar
    """
    # ── Campos scalar ────────────────────────────────────────────────────────
    id: uuid.UUID
    public_id: str
    estado: str
    fecha_registro: str
    expediente: Optional[str] = None
    observacion: Optional[str] = None
    numero_revision: int
    tipo_tramite: str
    tramite_accion: str
    # ── Campos anidados ─────────────────────────────────────────────────────
    proyecto: ProyectoOut
    entidad: Optional[EntidadOut] = None
    municipalidad: MunicipalidadOut
    valores: ValoresOut
    proyectistas: list[ProyectistaOut] = Field(default_factory=list)
    delegados: list[DelegadoOut] = Field(default_factory=list)
    contactos: list[ContactoEdificacionOut] = Field(default_factory=list)
    revisiones: list[RevisionOut] = Field(default_factory=list)
    # ── Campos financieros directos (duplicados de valores para conveniencia) ─
    subtotal: float
    igv: float
    total: float
    total_a_pagar: float


class VariablesFinancierasOut(BaseSchema):
    """Variables financieras para mostrar en formulario."""
    igv_valor: float = Field(..., description="Tasa IGV (ej. 0.18)")
    igv_periodo_inicio: str = Field(..., description="Fecha inicio período IGV")
    uit_valor: float = Field(..., description="Valor UIT en soles")
    uit_periodo_inicio: str = Field(..., description="Fecha inicio período UIT")


class EspecialidadBasicaOut(BaseSchema):
    """Especialidad básica para revisión vigente."""
    id: uuid.UUID
    nombre: str


class RevisionVigenteOut(BaseSchema):
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


class RevisionesVigentesOut(BaseSchema):
    """Lista de revisiones vigentes para formulario."""
    revisiones: list[RevisionVigenteOut]


class LiquidacionEdificacionesListItemOut(BaseSchema):
    """Item de lista en respuesta paginada."""
    id: uuid.UUID
    public_id: Optional[str] = None
    numero_revision: int
    estado: str
    valor_proyecto: float
    proyecto_public_id: str
    proyecto_denominacion: str
    fecha_registro: str
    total: float
    # Campos de municipalidad
    municipalidad_id: Optional[uuid.UUID] = None
    municipalidad_nombre: Optional[str] = None
    # Campos de edificaciones
    tipo_tramite: Optional[str] = None
    tramite_accion: Optional[str] = None
    # expediente fue removido del dominio


class NuevaRevisionFormularioOut(BaseSchema):
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
    tipo_tramite: str = Field(..., description="Tipo de trámite de la liquidación previa")


# ── Cotización / Quote Schemas ──────────────────────────────────────────────────


class CotizacionPrimeraRevisionIn(BaseSchema):
    """Payload para cotizar primera revisión (sin guardar en BD).
    
    La cotización es específica para Edificación — depende de TarifaLiquidacionBase
    filtrada por tipo_liquidacion=EDIFICACION, y usa los valores proporcionados.
    No requiere proyecto_public_id ya que el cálculo solo usa valores y tarifas.
    
    Fase 6: tarifas_ids es ahora requerido — auto-selección eliminada.
    tipo_tramite es requerido junto con tarifas_ids para validar ReglaTarifaEdificacion.
    """
    tipo_tramite: str = Field(
        ...,
        description="Tipo de trámite de edificación: OBRA_NUEVA, DEMOLICION, AMPLIACION, REMODELACION, MODIFICACION_LICENCIA, REINTEGRO, PROYECTO_CON_PLANTAS_TIPICAS. Requerido junto con tarifas_ids."
    )
    valor_proyecto: float = Field(..., gt=0, description="Valor del proyecto/obra")
    valor_base_calculo: float = Field(..., gt=0, description="Valor base de cálculo. Para tipos normales debe ser igual a valor_proyecto. Para PROYECTO_CON_PLANTAS_TIPICAS puede ser diferente.")
    # NUEVO Fase 3: Tarifas IDs (array, exactamente 1 elemento)
    # REQUERIDO: frontend siempre envía tarifas_ids, backend ya no hace auto-selección.
    # Validación: debe tener exactamente 1 elemento (min_length=1, max_length=1).
    tarifas_ids: list[uuid.UUID] = Field(
        ...,
        min_length=1,
        max_length=1,
        description="IDs de tarifas a usar en la cotización. Para esta fase debe ser exactamente 1."
    )


class CotizacionPrimeraRevisionWrapperIn(BaseSchema):
    """Wrapper para cotizar primera revisión — acepta { liquidacion: {...} }."""
    liquidacion: CotizacionPrimeraRevisionIn


class CotizacionNuevaRevisionIn(BaseSchema):
    """Payload para cotizar nueva revisión (sin guardar en BD)."""
    liquidacion_previa_id: uuid.UUID = Field(..., description="ID de la liquidación previa (UUID)")
    revisiones_ids: list[uuid.UUID] = Field(..., min_length=1, description="IDs de revisiones de edificación a asociar (UUID), no puede estar vacío")
    # No requiere valor_proyecto (se obtiene de la liquidación previa)


class CotizacionTarifaOut(BaseSchema):
    """Tarifa dentro de revisión en respuesta de cotización."""
    id: uuid.UUID
    derecho_minimo: float
    derecho_maximo: Optional[float]
    porcentaje_minimo_uit: float


class CotizacionRevisionOut(BaseSchema):
    """Revisión en respuesta de cotización (sin numero_revision duplicado)."""
    id: uuid.UUID
    especialidades: list[EspecialidadBasicaOut]
    tarifa: CotizacionTarifaOut
    monto_base: float
    cobra: bool


class CotizacionTotalesOut(BaseSchema):
    """Totales en respuesta de cotización."""
    subtotal: float
    igv: float
    total: float
    liquidacion_total: float
    total_a_pagar: float


class CotizacionMetadataOut(BaseSchema):
    """Metadata adicional en respuesta de cotización."""
    igv_valor: float
    uit_valor: float
    cobra: bool
    valor_base_calculo: float


class CotizacionQuoteOut(BaseSchema):
    """Respuesta completa de cotización sin duplicación de numero_revision."""
    numero_revision: int = Field(..., description="Número de revisión calculado")
    revisiones: list[CotizacionRevisionOut] = Field(..., description="Lista de revisiones calculadas")
    totales: CotizacionTotalesOut
    metadata: CotizacionMetadataOut

    @model_serializer(mode='wrap')
    def serialize_model(self, handler):
        """Rename metadata to _metadata in JSON output per API contract."""
        data = handler(self)
        if hasattr(data, "model_dump"):
            # Convert nested models recursively to plain dicts (Pydantic v2)
            data = data.model_dump(mode="python")
        elif not isinstance(data, dict):
            data = dict(data)
        # Safely rename metadata to _metadata
        if "metadata" in data:
            data["_metadata"] = data.pop("metadata")
        return data


# ── Delegados Vigentes Schemas ─────────────────────────────────────────────────


class EspecialidadBasicaDelegadoOut(BaseSchema):
    """Especialidad anidada en delegado vigente."""
    id: uuid.UUID = Field(..., description="ID de la especialidad (UUID)")
    nombre: str = Field(..., description="Nombre de la especialidad")


class DelegadoVigenteOut(BaseSchema):
    """Delegado vigente para selección en formulario de liquidación."""
    id: uuid.UUID = Field(..., description="ID del delegado (UUID)")
    nombre_completo: str = Field(..., description="Nombre completo del ingeniero")
    cip: str = Field(..., description="Número de CIP del ingeniero")
    especialidad: EspecialidadBasicaDelegadoOut = Field(..., description="Especialidad del delegado")
    tipo: str = Field(..., description="Tipo de delegado: titular o alterno")


class DelegadosVigentesOut(BaseSchema):
    """Respuesta de delegados vigentes para una municipalidad."""
    delegados: list[DelegadoVigenteOut] = Field(
        default_factory=list,
        description="Lista de delegados vigentes para la municipalidad seleccionada"
    )


# ── Especialidades Vigentes Schemas ──────────────────────────────────────────


class EspecialidadesVigentesOut(BaseSchema):
    """Respuesta de especialidades vigentes para edificaciones."""
    especialidades: list[EspecialidadBasicaOut] = Field(
        default_factory=list,
        description="Lista de especialidades vigentes del grupo de edificaciones"
    )
