"""
Factory for EdificacionesRevision model — used in tests.
"""
from datetime import date
from decimal import Decimal

import factory
from factory.django import DjangoModelFactory

from modules.liquidaciones.domain.models.liquidacion.liquidacion_edificaciones import EdificacionesRevision
from .tarifa_factory import EdificacionesTarifaFactory
from .especialidad_factory import EspecialidadFactory


class EdificacionesRevisionFactory(DjangoModelFactory):
    class Meta:
        model = EdificacionesRevision

    tarifa = factory.SubFactory(EdificacionesTarifaFactory)
    porcentaje_liquidacion = Decimal("5.00")
    especialidad = factory.SubFactory(EspecialidadFactory)
    periodo_inicio = date(2020, 1, 1)
    periodo_fin = None  # vigente (habilitada)
