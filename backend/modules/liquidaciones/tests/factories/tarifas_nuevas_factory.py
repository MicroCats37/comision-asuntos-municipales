"""
Factories for new tariff and rule models — used in tests.

Models:
- TarifaPorMetroCuadrado: links to TarifaLiquidacionBase
- TarifaPorCategoriaVisitas: links to TarifaLiquidacionBase
- ReglaTarifaLiquidacion: links TarifaLiquidacionBase to tramite_accion
- ReglaTarifaInspeccionObra: links TarifaLiquidacionBase to categoria + tramite_accion

Usage:
    # Create tarifa M2 with base and regla for HABILITACION_URBANA + PRIMERA_REVISION
    base = TarifaLiquidacionBaseFactory(tipo_liquidacion=TipoLiquidacion.HABILITACION_URBANA)
    tarifa_m2 = TarifaPorMetroCuadradoFactory(tarifa_base=base)
    ReglaTarifaLiquidacionFactory(
        tarifa_base=base,
        tramite_accion=TramiteAccion.PRIMERA_REVISION,
    )

    # Create tarifa visitas with regla for INSPECCION_OBRA + categoria A
    base_io = TarifaLiquidacionBaseFactory(tipo_liquidacion=TipoLiquidacion.INSPECCION_OBRA)
    tarifa_visitas = TarifaPorCategoriaVisitasFactory(tarifa_base=base_io)
    ReglaTarifaInspeccionObraFactory(
        tarifa_base=base_io,
        categoria='A',
        tramite_accion=TramiteAccion.PRIMERA_REVISION,
    )
"""
from datetime import date
from decimal import Decimal

import factory
from factory.django import DjangoModelFactory

from modules.liquidaciones.domain.models.liquidacion.liquidacion import (
    TarifaLiquidacionBase,
)
from modules.liquidaciones.domain.models.liquidacion.tarifas_reglas import (
    TarifaPorMetroCuadrado as TarifaPorMetroCuadradoModel,
    TarifaPorCategoriaVisitas as TarifaPorCategoriaVisitasModel,
    ReglaTarifaLiquidacion as ReglaTarifaLiquidacionModel,
    ReglaTarifaInspeccionObra as ReglaTarifaInspeccionObraModel,
)
from modules.liquidaciones.domain.constants import TipoLiquidacion, TramiteAccion


class TarifaLiquidacionBaseM2Factory(DjangoModelFactory):
    """
    Factory for TarifaLiquidacionBase configured for M2 calculations.

    Usage:
        base = TarifaLiquidacionBaseM2Factory(tipo_liquidacion=TipoLiquidacion.HABILITACION_URBANA)
        # Creates base + TarifaPorMetroCuadrado automatically
    """

    class Meta:
        model = TarifaLiquidacionBase

    tipo_liquidacion = TipoLiquidacion.HABILITACION_URBANA
    periodo_inicio = date(2020, 1, 1)
    periodo_fin = None  # vigente

    @factory.post_generation
    def detalle_m2(self, create, extracted, **kwargs):
        """Crea automáticamente TarifaPorMetroCuadrado vinculada a esta TarifaLiquidacionBase."""
        if not create:
            return
        if extracted:
            # Use provided detalle
            for det in extracted:
                det.tarifa_base = self
                det.save()
        else:
            TarifaPorMetroCuadradoFactory(tarifa_base=self)


class TarifaLiquidacionBaseVisitasFactory(DjangoModelFactory):
    """
    Factory for TarifaLiquidacionBase configured for Visitas calculations.

    Usage:
        base = TarifaLiquidacionBaseVisitasFactory(tipo_liquidacion=TipoLiquidacion.INSPECCION_OBRA)
        # Creates base + TarifaPorCategoriaVisitas automatically
    """

    class Meta:
        model = TarifaLiquidacionBase

    tipo_liquidacion = TipoLiquidacion.INSPECCION_OBRA
    periodo_inicio = date(2020, 1, 1)
    periodo_fin = None  # vigente

    @factory.post_generation
    def detalle_visitas(self, create, extracted, **kwargs):
        """Crea automáticamente TarifaPorCategoriaVisitas vinculada a esta TarifaLiquidacionBase."""
        if not create:
            return
        if extracted:
            for det in extracted:
                det.tarifa_base = self
                det.save()
        else:
            TarifaPorCategoriaVisitasFactory(tarifa_base=self)


class TarifaPorMetroCuadradoFactory(DjangoModelFactory):
    """
    Factory for TarifaPorMetroCuadrado model.

    Relación: tarifa_base = OneToOneField -> TarifaLiquidacionBase.
    """

    class Meta:
        model = TarifaPorMetroCuadradoModel

    costo_por_m2 = Decimal("50.0000")  # S/ 50 por m2
    area_minima = Decimal("100.00")  # 100 m2 mínimo
    derecho_minimo = Decimal("500.00")  # S/ 500 mínimo
    derecho_maximo = Decimal("5000.00")  # S/ 5000 máximo


class TarifaPorCategoriaVisitasFactory(DjangoModelFactory):
    """
    Factory for TarifaPorCategoriaVisitas model.

    Relación: tarifa_base = OneToOneField -> TarifaLiquidacionBase.
    """

    class Meta:
        model = TarifaPorCategoriaVisitasModel

    costo_por_visita = Decimal("150.00")  # S/ 150 por visita
    visitas_minimas = 1  # Mínimo 1 visita


class ReglaTarifaLiquidacionFactory(DjangoModelFactory):
    """
    Factory for ReglaTarifaLiquidacion model.

    Usage:
        base = TarifaLiquidacionBaseFactory()
        regla = ReglaTarifaLiquidacionFactory(
            tarifa_base=base,
            tramite_accion=TramiteAccion.PRIMERA_REVISION,
        )
    """

    class Meta:
        model = ReglaTarifaLiquidacionModel

    tramite_accion = TramiteAccion.PRIMERA_REVISION

    @factory.lazy_attribute
    def tarifa_base(self):
        """Crea una tarifa base con detalle M2 si no se provee."""
        if not hasattr(self, 'tarifa_base_id') or not self.tarifa_base_id:
            base = TarifaLiquidacionBaseM2Factory()
            TarifaPorMetroCuadradoFactory(tarifa_base=base)
            return base
        return self.tarifa_base


class ReglaTarifaInspeccionObraFactory(DjangoModelFactory):
    """
    Factory for ReglaTarifaInspeccionObra model.

    Usage:
        base = TarifaLiquidacionBaseVisitasFactory()
        regla = ReglaTarifaInspeccionObraFactory(
            tarifa_base=base,
            categoria='A',
            tramite_accion=TramiteAccion.PRIMERA_REVISION,
        )
    """

    class Meta:
        model = ReglaTarifaInspeccionObraModel

    categoria = 'A'
    tramite_accion = TramiteAccion.PRIMERA_REVISION

    @factory.lazy_attribute
    def tarifa_base(self):
        """Crea una tarifa base con detalle visitas si no se provee."""
        if not hasattr(self, 'tarifa_base_id') or not self.tarifa_base_id:
            base = TarifaLiquidacionBaseVisitasFactory()
            TarifaPorCategoriaVisitasFactory(tarifa_base=base)
            return base
        return self.tarifa_base
