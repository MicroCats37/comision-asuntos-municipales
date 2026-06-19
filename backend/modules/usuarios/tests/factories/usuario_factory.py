"""
Factory for Usuario model — used in tests.
"""
import factory
from factory.django import DjangoModelFactory

from modules.usuarios.domain.models.usuario import Usuario


class UsuarioFactory(DjangoModelFactory):
    class Meta:
        model = Usuario

    username = factory.Sequence(lambda n: f"{n:08d}")
    dni = factory.Sequence(lambda n: f"{n:08d}")
    email = factory.LazyAttribute(lambda obj: f"{obj.username}@example.com")
    nombres = factory.Faker("first_name")
    apellidos = factory.Faker("last_name")
    password = factory.PostGenerationMethodCall("set_password", "test1234")
