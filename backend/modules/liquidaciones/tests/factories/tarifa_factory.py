"""
Factory for EdificacionesTarifa model — used in tests.
"""
from datetime import date
from decimal import Decimal

import factory
from factory.django import DjangoModelFactory

from modules.liquidaciones.domain.models.liquidacion.liquidacion_edificaciones import EdificacionesTarifa


class EdificacionesTarifaFactory(DjangoModelFactory):
    class Meta:
        model = EdificacionesTarifa

    porcentaje_minimo_uit = Decimal("1.00")
    derecho_minimo = Decimal("500.00")
    derecho_maximo = Decimal("5000.00")
    periodo_inicio = date(2020, 1, 1)
    periodo_fin = None  # vigente
