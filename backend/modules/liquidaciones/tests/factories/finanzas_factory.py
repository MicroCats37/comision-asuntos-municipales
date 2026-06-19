"""
Factory for IGV and UIT — used in liquidaciones tests.
"""
from datetime import date
from decimal import Decimal

import factory
from factory.django import DjangoModelFactory

from modules.finanzas.models import IGV, UIT


class IGVFactory(DjangoModelFactory):
    class Meta:
        model = IGV

    valor = Decimal("0.18")
    periodo_inicio = date(2020, 1, 1)
    periodo_fin = None


class UITFactory(DjangoModelFactory):
    class Meta:
        model = UIT

    valor = 4950
    periodo_inicio = date(2026, 1, 1)
    periodo_fin = None
