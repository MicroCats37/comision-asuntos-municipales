"""
Factory for IGV model — used in tests.
"""
from datetime import date
from decimal import Decimal

import factory
from factory.django import DjangoModelFactory

from modules.finanzas.models import IGV


class IGVFactory(DjangoModelFactory):
    class Meta:
        model = IGV

    valor = Decimal("0.18")
    periodo_inicio = date(2020, 1, 1)
    periodo_fin = None  # vigente
