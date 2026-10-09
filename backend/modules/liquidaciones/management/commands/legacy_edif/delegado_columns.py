"""
EDIF legacy helpers — DELEGADO slot column index constants for EDIF_ALL.csv.

NOTE: All column index constants have been consolidated into columns.py.
This module re-exports non-column constants only.

Each slot (1..4) has these fields mapped from EDIF_ALL.csv columns:
    PERIODO, MES, FECHAPRES, FECHAREVI, NROORDEN, DICTAMEN

Slot -> EspecialidadRevision mapping (DB canonical names):
    1 -> Ingeniería Civil
    2 -> Ingeniería Sanitaria
    3 -> Ingeniería Eléctrica y Mecánica Eléctrica
    4 -> Ingeniería Electrónica
"""

# Re-export slot column tuples and specialty maps from columns.py
from .columns import (
    DELEGADO_SLOT_COLUMNS,
    SLOT_SPECIALTY_DB_MAP,
    _SLOT_SPECIALTY_MAP,
)

# Valid dictamen values for LiquidacionDelegado.dictamen_revision
VALID_DICTAMEN_VALUES = frozenset([
    "CONFORME",
    "NO_CONFORME",
    "PENDIENTE",
    "AP_OB",
])
