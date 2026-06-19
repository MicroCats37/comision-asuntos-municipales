"""
Factory for Proyecto model — used in tests.
"""
import factory
from factory.django import DjangoModelFactory
from django.utils import timezone

from modules.liquidaciones.domain.models.proyecto import Proyecto
from .entidad_factory import EntidadFactory


class ProyectoFactory(DjangoModelFactory):
    class Meta:
        model = Proyecto

    # NOTE: proyectista FK was removed from Proyecto (moved to LiquidacionEdificaciones.proyectistas M2M)
    entidad = factory.SubFactory(EntidadFactory)
    public_id = factory.LazyAttribute(
        lambda o: f"PROY-{timezone.now().year}-TEST-{Proyecto.objects.count() + 1:05d}"
    )
    nombre_propietario = factory.Faker("name")
    denominacion = factory.Faker("sentence", nb_words=4)
    direccion = factory.Faker("address")
