"""
Factory for Entidad (institución RUC) — used in tests.
"""
import factory
from factory.django import DjangoModelFactory

from modules.entidades.domain.models.entidad import Entidad


class EntidadFactory(DjangoModelFactory):
    class Meta:
        model = Entidad

    tipo_documento = "RUC"
    numero_documento = factory.Sequence(lambda n: f"{n:011d}")  # 11 dígitos
    razon_social = factory.Faker("company")
    tipo_contribuyente = "GENERICO"
    activo = True
