"""
Tarifas y Reglas — tarifas y reglas de resolución por especialidad.

Este archivo contiene:
- TarifaPorMetroCuadrado: tarifa por metro cuadrado con límites
- TarifaPorCategoriaVisitas: tarifa por categoría de visitas
- ReglaTarifaInspeccionObra: regla específica para inspección de obra por categoria
"""

from django.db import models
from simple_history.models import HistoricalRecords
from core.models import BaseModel
from decimal import Decimal
from core_application.models import VigenciaModel

from modules.liquidaciones.domain.constants import TramiteAccion, TipoLiquidacion
from modules.usuarios.domain.models.perfil_ingeniero import EspecialidadRevision


class TarifaLiquidacionBase(BaseModel, VigenciaModel):
    
    tipo_liquidacion = models.ForeignKey(
        'liquidaciones.TipoLiquidacion',
        on_delete=models.PROTECT,
        related_name='tarifas_base',
        verbose_name="Tipo de Liquidación",
        help_text="Tipo de liquidación/formulario.",
    )
        
    class Meta:
        verbose_name = "Tarifa Base de Liquidación"
        verbose_name_plural = "Tarifas Base de Liquidaciones"
        ordering = ["tipo_liquidacion"]

    def __str__(self):
        return f"Tarifa base {self.tipo_liquidacion}"


class TarifaPorMetroCuadrado(BaseModel):
    """
    Tarifa por metro cuadrado para liquidaciones de habilitación urbana,
    mecánica de suelos, impacto vial y taludes.

    Contiene el costo por m2, área mínima y los límites de derecho mínimo/máximo.

    Relación: Tiene OneToOneField hacia TarifaLiquidacionBase.
    Una TarifaPorMetroCuadrado pertenece a exactamente una TarifaLiquidacionBase.
    """

    history = HistoricalRecords()

    tarifa_base = models.OneToOneField(
        TarifaLiquidacionBase,
        on_delete=models.CASCADE,
        related_name="detalle_m2",
        verbose_name="Tarifa Base",
        help_text="Tarifa base asociada a esta tarifa por metro cuadrado.",
    )

    costo_por_m2 = models.DecimalField(
        max_digits=10,
        decimal_places=4,
        verbose_name="Costo por M2",
        help_text="Costo por metro cuadrado en soles.",
    )



    class Meta:
        verbose_name = "Tarifa por Metro Cuadrado"
        verbose_name_plural = "Tarifas por Metro Cuadrado"
        ordering = ["tarifa_base__tipo_liquidacion", "costo_por_m2"]

    def __str__(self):
        return f"Tarifa M2 {self.costo_por_m2}/m2 (area min: {self.area_m2})"


class TarifaPorCategoriaVisitas(BaseModel):
    """
    Tarifa por categoría de visitas para liquidaciones de inspección de obra.

    Contiene el porcentaje de UIT aplicable y la categoría.

    Relación: Tiene ForeignKey hacia TarifaLiquidacionBase.
    Una TarifaLiquidacionBase puede tener múltiples TarifaPorCategoriaVisitas.
    """

    history = HistoricalRecords()

    tarifa_base = models.ForeignKey(
        TarifaLiquidacionBase,
        on_delete=models.CASCADE,
        related_name="detalle_visitas",
        verbose_name="Tarifa Base",
        help_text="Tarifa base asociada a esta tarifa por categoría de visitas.",
    )

    porcentaje_uit = models.DecimalField(
        max_digits=10,
        decimal_places=4,
        verbose_name="% de UIT",
        help_text="Porcentaje de la UIT aplicable para esta categoría.",
        default=Decimal("0.0"),
    )

    categoria_visitas = models.CharField(
        max_length=50,
        choices=TramiteAccion.choices,
        verbose_name="Categoría de Visitas",
        help_text="Categoría de visitas según el tipo de trámite/acción.",
    )
    
    class Meta:
        verbose_name = "Tarifa por Categoría de Visitas"
        verbose_name_plural = "Tarifas por Categoría de Visitas"
        ordering = ["tarifa_base__tipo_liquidacion", "porcentaje_uit"]

    def __str__(self):
        return f"Tarifa Visitas {self.porcentaje_uit * 100}% UIT/visita"


class TarifaPorcentajeObra(BaseModel):
    """
    Tarifa porcentual para liquidaciones de obra.

    Contiene el porcentaje de liquidación y los límites de derecho mínimo/máximo
    y el mínimo como porcentaje de UIT.

    Relación: Tiene OneToOneField hacia TarifaLiquidacionBase.
    Una TarifaPorcentajeObra pertenece a exactamente una TarifaLiquidacionBase.
    """

    history = HistoricalRecords()

    # FK/OneToOne hacia TarifaLiquidacionBase — la cabecera de esta tarifa.
    # Cada TarifaPorcentajeObra tiene una única TarifaLiquidacionBase.
    # NOTA: null=True/blank=True temporalmente para permitir migración sin datos existentes.
    # La BD de desarrollo se reseteará, así que todas las filas tendrán el valor correcto.
    tarifa_base = models.ForeignKey(
        "TarifaLiquidacionBase",
        on_delete=models.CASCADE,
        related_name="detalle_porcentual",
        verbose_name="Tarifa Base",
        help_text="Tarifa base asociada a esta tarifa porcentual.",
        null=True,
        blank=True,
    )
    
    porcentaje_liquidacion = models.DecimalField(
        max_digits=7,
        decimal_places=4,
        verbose_name="Porcentaje de Liquidación",
        help_text="Porcentaje aplicado para el cálculo del derecho (ej: 0.0015 para 0.15%).",
    )


    class Meta:
        verbose_name = "Tarifa Porcentual de Obra"
        verbose_name_plural = "Tarifas Porcentuales de Obra"
        ordering = ["tarifa_base__tipo_liquidacion", "porcentaje_liquidacion"]

    def __str__(self):
        return (
            f"Tarifa {self.porcentaje_liquidacion * 100}% (min: {self.derecho_minimo})"
        )


class DerechoPorcentajeObra(BaseModel, VigenciaModel):
    """
    Derecho mínimo porcentual para liquidaciones de obra.

    Contiene el porcentaje de derecho mínimo y los límites de derecho mínimo/máximo
    y el mínimo como porcentaje de UIT.

    These records are intentionally global vigency/value tables for now.
    """

    history = HistoricalRecords()

    derecho_minimo = models.DecimalField(
        max_digits=10,
        decimal_places=4,
        null=True,
        blank=True,
        verbose_name="Derecho Mínimo",
        help_text="Monto mínimo absoluto del derecho en soles.",
    )
    
    derecho_maximo = models.DecimalField(
        max_digits=10,
        decimal_places=4,
        null=True,
        blank=True,
        verbose_name="Derecho Máximo",
        help_text="Monto máximo absoluto del derecho en soles (nulo = sin tope).",
    )

    porcentaje_minimo_uit = models.DecimalField(
        max_digits=7,
        decimal_places=4,
        verbose_name="Porcentaje de Derecho Mínimo",
        help_text="Porcentaje aplicado para el cálculo del derecho mínimo (ej: 0.0015 para 0.15%).",
    )

    class Meta:
        verbose_name = "Derecho Mínimo Porcentual de Obra"
        verbose_name_plural = "Derechos Mínimos Porcentuales de Obra"

    def __str__(self):
        return f"Derecho mínimo porcentual {self.derecho_minimo}"


class DerechoPorMetroCuadrado(BaseModel, VigenciaModel):
    """
    Derecho mínimo por metro cuadrado para liquidaciones de obra.

    Contiene el derecho mínimo absoluto y el derecho mínimo por metro cuadrado.

    These records are intentionally global vigency/value tables for now.
    """

    history = HistoricalRecords()

    derecho_minimo = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        verbose_name="Derecho Mínimo",
        help_text="Monto mínimo absoluto del derecho en soles.",
    )

    derecho_maximo = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        verbose_name="Derecho Máximo",
        help_text="Monto máximo absoluto del derecho en soles.",
    )

    class Meta:
        verbose_name = "Derecho Mínimo por Metro Cuadrado"
        verbose_name_plural = "Derechos Mínimos por Metro Cuadrado"

    def __str__(self):
        return f"Derecho mínimo M2 {self.derecho_minimo}"


#----