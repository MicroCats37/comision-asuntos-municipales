"""
Factory for Delegado and related models — used in tests.
"""
from datetime import date
import factory
from factory.django import DjangoModelFactory

from modules.liquidaciones.domain.models.delegado import Delegado, PeriodoDelegado, MunicipalidadDelegado
from modules.liquidaciones.domain.constants import DelegadoStatus, TipoDelegado, CategoriaDelegado
from modules.usuarios.tests.factories.perfil_ingeniero_factory import PerfilIngenieroFactory
from modules.liquidaciones.tests.factories.especialidad_factory import EspecialidadFactory


class DelegadoFactory(DjangoModelFactory):
    """Factory for Delegado model."""

    class Meta:
        model = Delegado

    perfil_ingeniero = factory.SubFactory(PerfilIngenieroFactory)
    # tipo is now on MunicipalidadDelegado, not Delegado
    especialidad = factory.SubFactory(EspecialidadFactory)
    banco = None  # nullable
    status = DelegadoStatus.ACTIVO


class PeriodoDelegadoFactory(DjangoModelFactory):
    """Factory for PeriodoDelegado model."""

    class Meta:
        model = PeriodoDelegado

    delegado = factory.SubFactory(DelegadoFactory)
    periodo_inicio = date(2020, 1, 1)
    # periodo_fin = None means vigente (open-ended)


class MunicipalidadDelegadoFactory(DjangoModelFactory):
    """Factory for MunicipalidadDelegado model."""

    class Meta:
        model = MunicipalidadDelegado

    delegado = factory.SubFactory(DelegadoFactory)
    municipalidad = None  # Set in test via factory.build or after creation
    tipo = TipoDelegado.TITULAR
    categoria = CategoriaDelegado.EDIFICACIONES
    activo = True
