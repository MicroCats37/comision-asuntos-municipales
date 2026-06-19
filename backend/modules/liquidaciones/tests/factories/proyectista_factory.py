"""
Factory for Proyectista model — used in tests.
"""
import factory
from factory.django import DjangoModelFactory

from modules.liquidaciones.domain.models import Proyectista


class ProyectistaFactory(DjangoModelFactory):
    class Meta:
        model = Proyectista

    nombres = factory.Faker("first_name")
    apellidos = factory.Faker("last_name")
