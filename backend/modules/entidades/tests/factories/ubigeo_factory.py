"""
Factories for Ubigeo models — used in tests.
"""
import factory
from factory.django import DjangoModelFactory

from modules.entidades.domain.models.ubigeo import UbigeoDepartamento, UbigeoProvincia, UbigeoDistrito


class UbigeoDepartamentoFactory(DjangoModelFactory):
    class Meta:
        model = UbigeoDepartamento

    nombre = factory.Sequence(lambda n: f"DEPARTAMENTO_{n:03d}")


class UbigeoProvinciaFactory(DjangoModelFactory):
    class Meta:
        model = UbigeoProvincia

    departamento = factory.SubFactory(UbigeoDepartamentoFactory)
    nombre = factory.Sequence(lambda n: f"PROVINCIA_{n:03d}")


class UbigeoDistritoFactory(DjangoModelFactory):
    class Meta:
        model = UbigeoDistrito

    provincia = factory.SubFactory(UbigeoProvinciaFactory)
    nombre = factory.Sequence(lambda n: f"DISTRITO_{n:03d}")
    ubigeo = factory.Sequence(lambda n: f"{n:06d}")
    inei = factory.Sequence(lambda n: f"{n:06d}")
