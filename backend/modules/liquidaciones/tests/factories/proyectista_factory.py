"""
Factory for Proyectista model — used in tests.

NOTE: Simplificada para usar PerfilIngeniero y Especialidad referenciados.
"""
import factory
from factory.django import DjangoModelFactory

from modules.liquidaciones.domain.models import Proyectista
from .especialidad_factory import EspecialidadFactory


class ProyectistaFactory(DjangoModelFactory):
    class Meta:
        model = Proyectista

    perfil_ingeniero = factory.SubFactory("modules.usuarios.tests.factories.PerfilIngenieroFactory")
    especialidad = factory.SubFactory(EspecialidadFactory)
    descripcion = factory.Faker("sentence", nb_words=6)
