"""
Legacy domain schemas — Edificacion-specific DTOs.

This file exists to satisfy imports from domain/schemas/__init__.py.
It re-exports Edificacion-specific schemas that were previously defined here.
"""
from pydantic import BaseModel
from typing import Optional, Any
import uuid


# ── Edificacion Revision Data ──────────────────────────────────────────────────


class EdificacionRevisionData(BaseModel):
    """Datos de revision para edificacion."""
    pass


class TarifaEdificacionData(BaseModel):
    """Datos de tarifa para edificacion."""
    pass


class EspecialidadData(BaseModel):
    """Datos de especialidad."""
    pass


class LiquidacionEdificacionesResult(BaseModel):
    """Resultado de liquidacion de edificaciones."""
    pass


class NuevaRevisionFormularioResult(BaseModel):
    """Resultado de nuevo formulario de revision."""
    pass


class LiquidacionEdificacionesListItem(BaseModel):
    """Item de lista para liquidaciones de edificaciones."""
    pass


class LiquidacionEdificacionesPaginatedResult(BaseModel):
    """Resultado paginado para liquidaciones de edificaciones."""
    pass


class ProyectistaEdificacionData(BaseModel):
    """Datos de proyectista para edificacion."""
    pass


class DelegadoEdificacionData(BaseModel):
    """Datos de delegado para edificacion."""
    pass


class ContactoData(BaseModel):
    """Datos de contacto."""
    pass


class RevisionVigenteResult(BaseModel):
    """Resultado de revision vigente."""
    pass


class EspecialidadBasicaResult(BaseModel):
    """Resultado basico de especialidad."""
    pass


class RevisionConTarifaData(BaseModel):
    """Datos de revision con tarifa."""
    pass


class RevisionCalculoData(BaseModel):
    """Datos de calculo de revision."""
    pass


class CotizacionRevisionData(BaseModel):
    """Datos de cotizacion de revision."""
    pass


class TarifaCalculoData(BaseModel):
    """Datos de calculo de tarifa."""
    pass


class CotizacionQuoteData(BaseModel):
    """Datos de cotizacion."""
    pass


class CotizacionTotalesData(BaseModel):
    """Datos de totales de cotizacion."""
    pass


class CotizacionMetadataData(BaseModel):
    """Metadatos de cotizacion."""
    pass


class DelegadosVigentesResult(BaseModel):
    """Resultado de delegados vigentes."""
    pass


class DelegadoVigenteResult(BaseModel):
    """Resultado de delegado vigente."""
    pass


class LiquidacionGeneralListItem(BaseModel):
    """Item de lista para liquidacion general."""
    pass


class LiquidacionGeneralPaginatedResult(BaseModel):
    """Resultado paginado para liquidacion general."""
    pass


class LiquidacionGeneralResult(BaseModel):
    """Resultado de liquidacion general."""
    pass


# ── Phase 5 General Liquidation Rich DTOs ─────────────────────────────────────


class ProyectoListItemInfo(BaseModel):
    """Informacion de item de lista de proyecto."""
    pass


class EntidadListItemInfo(BaseModel):
    """Informacion de item de lista de entidad."""
    pass


class MunicipalidadInfo(BaseModel):
    """Informacion de municipalidad."""
    pass


class ValoresListItemInfo(BaseModel):
    """Informacion de item de lista de valores."""
    pass


class ProyectistaListItemData(BaseModel):
    """Datos de item de lista de proyectista."""
    pass


class DelegadoListItemData(BaseModel):
    """Datos de item de lista de delegado."""
    pass


class ContactoListItemData(BaseModel):
    """Datos de item de lista de contacto."""
    pass


class TarifaRevisionData(BaseModel):
    """Datos de tarifa de revision."""
    pass


class EspecialidadRevisionData(BaseModel):
    """Datos de especialidad de revision."""
    pass


class RevisionListItemData(BaseModel):
    """Datos de item de revision."""
    pass


# ── Edificacion-specific inline DTOs ───────────────────────────────────────────


class ProyectistaInlineData(BaseModel):
    """Datos inline de proyectista."""
    pass


class ContactoInlineData(BaseModel):
    """Datos inline de contacto."""
    pass
