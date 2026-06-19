"""
Finanzas Core Service — operaciones sync para finanzas.
"""
from decimal import Decimal

from injector import inject
from asgiref.sync import sync_to_async

from modules.finanzas.models import IGV, UIT


class FinanzasCoreService:
    """
    Servicio core sync para operaciones de finanzas.
    """

    def _obtener_igv_vigente(self) -> IGV | None:
        """Obtiene el IGV vigente (sin periodo_fin)."""
        return IGV.objects.filter(periodo_fin__isnull=True).order_by('-periodo_inicio').first()

    def _obtener_uit_vigente(self) -> UIT | None:
        """Obtiene la UIT vigente (sin periodo_fin)."""
        return UIT.objects.filter(periodo_fin__isnull=True).order_by('-periodo_inicio').first()

    async def obtener_variables_financieras_vigentes(self) -> dict:
        """Async: obtiene IGV y UIT vigentes para mostrar en formulario."""
        igv = await sync_to_async(self._obtener_igv_vigente)()
        uit = await sync_to_async(self._obtener_uit_vigente)()

        if not igv or not uit:
            return {
                'igv_valor': 0.18,
                'igv_periodo_inicio': '',
                'uit_valor': 0,
                'uit_periodo_inicio': '',
            }

        return {
            'igv_valor': float(igv.valor),
            'igv_periodo_inicio': igv.periodo_inicio.isoformat(),
            'uit_valor': float(uit.valor),
            'uit_periodo_inicio': uit.periodo_inicio.isoformat(),
        }
