"""
Factory for ReglaTarifaEdificacion model — used in tests.
"""
from datetime import date

import factory
from factory.django import DjangoModelFactory

from modules.liquidaciones.domain.models.liquidacion.liquidacion import ReglaTarifaEdificacion
from modules.liquidaciones.domain.constants import TipoTramiteEdificaciones, TramiteAccion
from .tarifa_liquidacion_factory import TarifaLiquidacionBaseFactory


class ReglaTarifaEdificacionFactory(DjangoModelFactory):
    """
    Factory for ReglaTarifaEdificacion model.

    Uso:
        # Crear regla para OBRA_NUEVA + PRIMERA_REVISION con una tarifa específica
        tarifa = TarifaLiquidacionBaseFactory()
        regla = ReglaTarifaEdificacionFactory(
            tipo_tramite=TipoTramiteEdificaciones.OBRA_NUEVA,
            tramite_accion=TramiteAccion.PRIMERA_REVISION,
            tarifa_base=tarifa,
        )
    """

    class Meta:
        model = ReglaTarifaEdificacion

    tipo_tramite = TipoTramiteEdificaciones.OBRA_NUEVA
    tramite_accion = TramiteAccion.PRIMERA_REVISION

    @factory.lazy_attribute
    def tarifa_base(self):
        """Crea una tarifa base con detalle si no se provee."""
        if not self.tarifa_base_id:
            return TarifaLiquidacionBaseFactory()
        return self.tarifa_base
