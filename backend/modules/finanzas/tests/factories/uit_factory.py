"""
Factory for UIT model — used in tests.
"""
from datetime import date
from decimal import Decimal

import factory
from factory.django import DjangoModelFactory

from modules.finanzas.models import UIT


class UITFactory(DjangoModelFactory):
    class Meta:
        model = UIT

    valor = 4950
    periodo_inicio = date(2026, 1, 1)
    periodo_fin = None  # vigente
