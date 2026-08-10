"""
FinanzasCoreService — ORM queries for finanzas entities.

Pure ORM access. No business logic.
"""
from typing import Optional

from modules.finanzas.domain.models.impuestos import IGV, UIT


class FinanzasCoreService:
    """
    Core service for querying IGV and UIT records.
    """

    def get_igv_vigente(self) -> Optional[IGV]:
        """
        Get the currently active IGV record.

        Returns:
            IGV instance with no periodo_fin, or None if not found.
        """
        return IGV.objects.vigente()

    def get_uit_vigente(self) -> Optional[UIT]:
        """
        Get the currently active UIT record.

        Returns:
            UIT instance with no periodo_fin, or None if not found.
        """
        return UIT.objects.vigente()