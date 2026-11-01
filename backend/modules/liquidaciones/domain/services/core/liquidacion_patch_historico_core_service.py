"""
Compatibility exports for the canonical historical liquidation resolver.

`LiquidacionPatchHistoricoCoreService` was the PATCH-specific historical
resolver. Its resolution logic now lives in the canonical resolver
(`LiquidacionHistoricoCoreService`), which also serves the `cotizar-edicion`
flows and the legacy import adapters.

This module keeps the old import path and the old class name working so that
existing consumers and test suites are not broken. New code must import
`LiquidacionHistoricoCoreService` from
`modules.liquidaciones.domain.services.core.liquidacion_historico_core_service`.
"""

from modules.liquidaciones.domain.services.core.liquidacion_historico_core_service import (
    LiquidacionHistoricoCoreService,
    NoDerechoVigenteError,
    NoIGVVigenteError,
    NoTarifaVigenteError,
    NoUITVigenteError,
)

# Backwards-compatible alias — same class, one canonical implementation.
LiquidacionPatchHistoricoCoreService = LiquidacionHistoricoCoreService

__all__ = [
    "LiquidacionPatchHistoricoCoreService",
    "NoDerechoVigenteError",
    "NoIGVVigenteError",
    "NoTarifaVigenteError",
    "NoUITVigenteError",
]
