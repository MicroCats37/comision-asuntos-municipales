"""
Factory for TarifaPorcentajeObra and TarifaLiquidacionBase models — used in tests.

Relación: TarifaPorcentajeObra.tarifa_base = OneToOneField -> TarifaLiquidacionBase.
Una TarifaLiquidacionBase tiene un único detalle TarifaPorcentajeObra.

Uso:
    # Crear tarifa base con su detalle porcentual (automático):
    # TarifaLiquidacionBaseFactory() crea ambos registros automáticamente

    # Crear solo TarifaLiquidacionBase (sin detalle):
    # Usar build() en lugar de create(), o crear manualmente.
"""
from datetime import date
from decimal import Decimal

import factory
from factory.django import DjangoModelFactory

from modules.liquidaciones.domain.models.liquidacion.liquidacion import (
    TarifaPorcentajeObra,
    TarifaLiquidacionBase,
)
from modules.liquidaciones.domain.constants import TipoLiquidacion
from .especialidad_factory import EspecialidadFactory


class TarifaLiquidacionBaseFactory(DjangoModelFactory):
    """
    Factory for TarifaLiquidacionBase model.

    Define qué tarifa aplica a un conjunto de especialidades para un tipo
    de liquidación en un período. La relación con TarifaPorcentajeObra
    ahora va en dirección inversa: TarifaPorcentajeObra tiene FK a TarifaLiquidacionBase.

    Uso:
        # Crea TarifaLiquidacionBase + TarifaPorcentajeObra vinculada automáticamente
        base = TarifaLiquidacionBaseFactory()

        # Con especialidades específicas
        esp1 = EspecialidadFactory()
        esp2 = EspecialidadFactory()
        base = TarifaLiquidacionBaseFactory(especialidades=[esp1, esp2])

        # Solo crear la base sin el detalle porcentual (para casos de prueba específicos):
        # Usar build() en lugar de create(), o crear el TarifaPorcentajeObra manualmente después.
    """

    class Meta:
        model = TarifaLiquidacionBase
        skip_postgeneration_save = True

    tipo_liquidacion = TipoLiquidacion.EDIFICACION
    periodo_inicio = date(2020, 1, 1)
    periodo_fin = None  # vigente (habilitada)

    @factory.post_generation
    def especialidades(self, create, extracted, **kwargs):
        """Add especialidades M2M after creation.

        Usage:
            # No especialidades (empty set)
            factory = TarifaLiquidacionBaseFactory()

            # With especialidades
            esp1 = EspecialidadFactory()
            esp2 = EspecialidadFactory()
            factory = TarifaLiquidacionBaseFactory(especialidades=[esp1, esp2])
        """
        if extracted:
            for esp in extracted:
                self.especialidades.add(esp)

    @factory.post_generation
    def detalle_porcentual(self, create, extracted, **kwargs):
        """
        Crea automáticamente TarifaPorcentajeObra vinculada a esta TarifaLiquidacionBase.

        La relación es: TarifaPorcentajeObra.tarifa_base = OneToOne -> TarifaLiquidacionBase.
        Se usa RelatedFactory para que el detalle se cree en el mismo created() call.
        """
        if not create:
            # build() no necesita crear el detalle
            return
        # Crear el detalle porcentual asociado
        TarifaPorcentajeObraFactory(tarifa_base=self)


class TarifaPorcentajeObraFactory(DjangoModelFactory):
    """
    Factory for TarifaPorcentajeObra model.

    Contiene el porcentaje para el cálculo de liquidaciones y límites min/max.

    Relación: tarifa_base = OneToOneField -> TarifaLiquidacionBase.
    Cada TarifaPorcentajeObra pertenece a una única TarifaLiquidacionBase.
    """

    class Meta:
        model = TarifaPorcentajeObra

    porcentaje_liquidacion = Decimal("0.05")  # 5%
    derecho_minimo = Decimal("500.00")
    derecho_maximo = Decimal("5000.00")
    porcentaje_minimo_uit = Decimal("1.00")
