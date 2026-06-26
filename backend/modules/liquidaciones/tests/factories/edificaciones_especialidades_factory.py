"""
Factory for EdificacionesEspecialidades model — used in tests.

This model defines the group of vigentes especialidades for Liquidaciones de Edificaciones.
"""
from datetime import date

import factory
from factory.django import DjangoModelFactory

from modules.liquidaciones.domain.models.liquidacion.liquidacion_edificaciones import EdificacionesEspecialidades


class EdificacionesEspecialidadesFactory(DjangoModelFactory):
    class Meta:
        model = EdificacionesEspecialidades

    periodo_inicio = date(2020, 1, 1)
    periodo_fin = None  # vigente (habilitada)

    @factory.post_generation
    def especialidades(self, create, extracted, **kwargs):
        """Add especialidades M2M after creation.

        Usage:
            # No especialidades (empty set)
            factory = EdificacionesEspecialidadesFactory()

            # With especialidades
            esp1 = EspecialidadFactory()
            esp2 = EspecialidadFactory()
            factory = EdificacionesEspecialidadesFactory(especialidades=[esp1, esp2])
        """
        if extracted:
            for esp in extracted:
                self.especialidades.add(esp)
