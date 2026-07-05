"""
Factory for EspecialidadesLiquidacion model — used in tests.

Replaces EdificacionesEspecialidadesFactory.
"""
from datetime import date

import factory
from factory.django import DjangoModelFactory

from modules.liquidaciones.domain.models.liquidacion.liquidacion import EspecialidadesLiquidacion
from modules.liquidaciones.domain.constants import TipoLiquidacion
from .especialidad_factory import EspecialidadFactory


class EspecialidadesLiquidacionFactory(DjangoModelFactory):
    """
    Factory for EspecialidadesLiquidacion model.

    Defines which specialties are enabled for each liquidacion type (EDIFICACION, etc.)
    in a given period.
    """

    class Meta:
        model = EspecialidadesLiquidacion

    tipo_liquidacion = TipoLiquidacion.EDIFICACION
    periodo_inicio = date(2020, 1, 1)
    periodo_fin = None  # vigente (habilitada)

    @factory.post_generation
    def especialidades(self, create, extracted, **kwargs):
        """Add especialidades M2M after creation.

        Usage:
            # No especialidades (empty set)
            factory = EspecialidadesLiquidacionFactory()

            # With especialidades
            esp1 = EspecialidadFactory()
            esp2 = EspecialidadFactory()
            factory = EspecialidadesLiquidacionFactory(especialidades=[esp1, esp2])
        """
        if extracted:
            for esp in extracted:
                self.especialidades.add(esp)
