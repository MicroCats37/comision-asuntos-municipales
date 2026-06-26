"""
Factory for EdificacionesRevision model — used in tests.

NOTE: Actualizada para usar ManyToManyField especialidades en lugar de FK.
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
    periodo_inicio = date(2020, 1, 1)
    periodo_fin = None  # vigente (habilitada)

    @factory.lazy_attribute
    def especialidades(self):
        """Crea especialidades M2M después de la creación del objeto."""
        return []  # Se asignan en el test o con .create() y luego establecer especialidades
