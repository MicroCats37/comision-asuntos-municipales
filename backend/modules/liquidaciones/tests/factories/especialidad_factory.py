"""
Factory for Especialidad model — used in tests.
"""
import factory
from factory.django import DjangoModelFactory

from modules.liquidaciones.domain.models.especialidades import Especialidad


class EspecialidadFactory(DjangoModelFactory):
    class Meta:
        model = Especialidad

    nombre = factory.Sequence(lambda n: f"Especialidad {n}")
