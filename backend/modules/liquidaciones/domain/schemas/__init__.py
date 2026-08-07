"""
Domain schemas package.

Estructura:
- shared: DTOs puros no ligados a tipo de liquidación específico
- wrappers: Wrapper que combinan resultado con cálculo
- habilitacion_urbana, mecanica_suelos, impacto_vial, taludes, inspeccion_obra:
  Result schemas por tipo de liquidación
"""

import importlib.util

# Explicitly load the legacy domain/schemas.py module (file, not package)
# to avoid circular import when re-exporting its types.
# Using spec_from_file_location because 'schemas' is also a package/directory,
# so import_module would load the __init__.py instead of the .py file.
_schemas_spec = importlib.util.spec_from_file_location(
    "liquidaciones_domain_schemas_file",
    "modules/liquidaciones/domain/schemas.py"
)
_schemas_module = importlib.util.module_from_spec(_schemas_spec)
_schemas_spec.loader.exec_module(_schemas_module)

from modules.liquidaciones.domain.schemas.shared import (
    # Inline DTOs (EntidadInlineData, ProyectoInlineData only - ContactoInlineData is Edificación-specific)
    EntidadInlineData,
    ProyectoInlineData,
    # Variables financieras
    VariablesFinancierasResult,
    # Cálculo M2
    TarifaM2CalculoData,
    LiquidacionM2CalculoData,
    # Cálculo visitas
    TarifaVisitasCalculoData,
    LiquidacionVisitasCalculoData,
    # Cotización (M2/Visitas versions only - Edificación uses schemas.py versions)
    CotizacionM2RevisionData,
    CotizacionVisitasRevisionData,
    CotizacionM2QuoteData,
    CotizacionVisitasQuoteData,
)

# `habilitacion_urbana.py` is intentionally empty (the concrete result class lives elsewhere).
# Re-exporting from here would crash Django on import.

from modules.liquidaciones.domain.schemas.mecanica_suelos import (
    LiquidacionMecanicaSuelosResult,
)

from modules.liquidaciones.domain.schemas.impacto_vial import (
    LiquidacionImpactoVialResult,
)

from modules.liquidaciones.domain.schemas.taludes import (
    LiquidacionTaludesResult,
)

from modules.liquidaciones.domain.schemas.inspeccion_obra import (
    LiquidacionInspeccionObraResult,
)

from modules.liquidaciones.domain.schemas.wrappers import (
    LiquidacionM2ResultConCalculo,
    LiquidacionInspeccionObraResultConCalculo,
    LiquidacionHabilitacionUrbanaResultConCalculo,
    LiquidacionMecanicaSuelosResultConCalculo,
    LiquidacionImpactoVialResultConCalculo,
    LiquidacionTaludesResultConCalculo,
)

# Edificación-specific domain schemas (from legacy domain/schemas.py file)
# Re-exported here so that imports from the package (domain.schemas) resolve correctly
# Using importlib to load the file module and assign to local namespace
EdificacionRevisionData = _schemas_module.EdificacionRevisionData
TarifaEdificacionData = _schemas_module.TarifaEdificacionData
EspecialidadData = _schemas_module.EspecialidadData
LiquidacionEdificacionesResult = _schemas_module.LiquidacionEdificacionesResult
NuevaRevisionFormularioResult = _schemas_module.NuevaRevisionFormularioResult
LiquidacionEdificacionesListItem = _schemas_module.LiquidacionEdificacionesListItem
LiquidacionEdificacionesPaginatedResult = _schemas_module.LiquidacionEdificacionesPaginatedResult
ProyectistaEdificacionData = _schemas_module.ProyectistaEdificacionData
DelegadoEdificacionData = _schemas_module.DelegadoEdificacionData
ContactoData = _schemas_module.ContactoData
RevisionVigenteResult = _schemas_module.RevisionVigenteResult
EspecialidadBasicaResult = _schemas_module.EspecialidadBasicaResult
RevisionConTarifaData = _schemas_module.RevisionConTarifaData
RevisionCalculoData = _schemas_module.RevisionCalculoData
CotizacionRevisionData = _schemas_module.CotizacionRevisionData
TarifaCalculoData = _schemas_module.TarifaCalculoData
CotizacionQuoteData = _schemas_module.CotizacionQuoteData
CotizacionTotalesData = _schemas_module.CotizacionTotalesData
CotizacionMetadataData = _schemas_module.CotizacionMetadataData
DelegadosVigentesResult = _schemas_module.DelegadosVigentesResult
DelegadoVigenteResult = _schemas_module.DelegadoVigenteResult
LiquidacionGeneralListItem = _schemas_module.LiquidacionGeneralListItem
LiquidacionGeneralPaginatedResult = _schemas_module.LiquidacionGeneralPaginatedResult
LiquidacionGeneralResult = _schemas_module.LiquidacionGeneralResult
# General liquidation rich DTOs (Phase 5)
ProyectoListItemInfo = _schemas_module.ProyectoListItemInfo
EntidadListItemInfo = _schemas_module.EntidadListItemInfo
MunicipalidadInfo = _schemas_module.MunicipalidadInfo
ValoresListItemInfo = _schemas_module.ValoresListItemInfo
ProyectistaListItemData = _schemas_module.ProyectistaListItemData
DelegadoListItemData = _schemas_module.DelegadoListItemData
ContactoListItemData = _schemas_module.ContactoListItemData
TarifaRevisionData = _schemas_module.TarifaRevisionData
EspecialidadRevisionData = _schemas_module.EspecialidadRevisionData
RevisionListItemData = _schemas_module.RevisionListItemData
# Edificación-specific inline DTOs
ProyectistaInlineData = _schemas_module.ProyectistaInlineData
ContactoInlineData = _schemas_module.ContactoInlineData

__all__ = [
    # Shared DTOs
    "EntidadInlineData",
    "ProyectoInlineData",
    "VariablesFinancierasResult",
    "TarifaM2CalculoData",
    "LiquidacionM2CalculoData",
    "TarifaVisitasCalculoData",
    "LiquidacionVisitasCalculoData",
    "CotizacionM2RevisionData",
    "CotizacionVisitasRevisionData",
    "CotizacionM2QuoteData",
    "CotizacionVisitasQuoteData",
    # Per-type results
    "LiquidacionHabilitacionUrbanaResult",
    "LiquidacionMecanicaSuelosResult",
    "LiquidacionImpactoVialResult",
    "LiquidacionTaludesResult",
    "LiquidacionInspeccionObraResult",
    # Wrappers
    "LiquidacionM2ResultConCalculo",
    "LiquidacionInspeccionObraResultConCalculo",
    "LiquidacionHabilitacionUrbanaResultConCalculo",
    "LiquidacionMecanicaSuelosResultConCalculo",
    "LiquidacionImpactoVialResultConCalculo",
    "LiquidacionTaludesResultConCalculo",
    # Edificación-specific DTOs (from domain/schemas.py)
    "EdificacionRevisionData",
    "TarifaEdificacionData",
    "EspecialidadData",
    "LiquidacionEdificacionesResult",
    "NuevaRevisionFormularioResult",
    "LiquidacionEdificacionesListItem",
    "LiquidacionEdificacionesPaginatedResult",
    "ProyectistaEdificacionData",
    "DelegadoEdificacionData",
    "ContactoData",
    "RevisionVigenteResult",
    "EspecialidadBasicaResult",
    "RevisionConTarifaData",
    "RevisionCalculoData",
    "CotizacionRevisionData",
    "TarifaCalculoData",
    "CotizacionQuoteData",
    "CotizacionTotalesData",
    "CotizacionMetadataData",
    "DelegadosVigentesResult",
    "DelegadoVigenteResult",
    # General liquidation DTOs
    "LiquidacionGeneralListItem",
    "LiquidacionGeneralPaginatedResult",
    "LiquidacionGeneralResult",
    # General liquidation rich DTOs (Phase 5)
    "ProyectoListItemInfo",
    "EntidadListItemInfo",
    "MunicipalidadInfo",
    "ValoresListItemInfo",
    "ProyectistaListItemData",
    "DelegadoListItemData",
    "ContactoListItemData",
    "TarifaRevisionData",
    "EspecialidadRevisionData",
    "RevisionListItemData",
    # Edificación-specific inline DTOs
    "ProyectistaInlineData",
    "ContactoInlineData",
]
