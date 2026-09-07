"""
Modelos de cálculo para especialidades M2 y visitas.

Este archivo contiene los modelos de cálculo LiquidacionPorMetroCuadrado y
LiquidacionPorCategoriaVisitas que se conectan a LiquidacionGeneral.
"""

from decimal import Decimal

from django.db import models
from simple_history.models import HistoricalRecords
from core.models import BaseModel

from modules.liquidaciones.domain.models.liquidacion.liquidacion_general.liquidacion import LiquidacionGeneral
from modules.liquidaciones.domain.constants import (
    TipoTramiteEdificaciones,
    TramiteAccion,
)
from modules.usuarios.domain.models.perfil_ingeniero import EspecialidadRevision


class LiquidacionPorMetroCuadrado(BaseModel):
    """
    Cálculo por metro cuadrado de una liquidación.

    Separa los datos de cálculo de la liquidación: relación con LiquidacionGeneral,
    área solicitada, área base de cálculo (tras evaluar area_minima),
    derecho calculado con clamps aplicados, y referencia a la tarifa por m2 aplicada.
    """

    history = HistoricalRecords()

    liquidacion_general = models.ForeignKey(
        LiquidacionGeneral,
        on_delete=models.CASCADE,
        related_name="liquidacion_m2",
        verbose_name="Liquidación General",
    )

    area_m2 = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        verbose_name="Área Solicitada",
        help_text="Área total solicitada en metros cuadrados.",
    )

    costo_por_m2 = models.DecimalField(
        max_digits=10,
        decimal_places=4,
        verbose_name="Costo por M2",
        help_text="Costo por metro cuadrado en soles.",
    )

    derecho_minimo = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=Decimal("0"),
        verbose_name="Derecho Mínimo",
        help_text="Monto mínimo del derecho calculado según la tarifa.",
    )

    derecho_maximo = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=Decimal("0"),
        verbose_name="Derecho Máximo",
        help_text="Monto máximo del derecho calculado según la tarifa.",
        blank=True,
        null=True,
    )
    
    tarifa_aplicada = models.ForeignKey(
        "TarifaPorMetroCuadrado",
        on_delete=models.PROTECT,
        related_name="liquidaciones_m2",
        verbose_name="Tarifa Aplicada",
        help_text="Tarifa por metro cuadrado que se aplicó para calcular el derecho.",
    )
    
    derecho= models.ForeignKey(
        "DerechoPorMetroCuadrado",
        on_delete=models.PROTECT,
        related_name="liquidaciones_m2",
        verbose_name="Derecho Aplicado",
        help_text="Derecho calculado según la tarifa por metro cuadrado.",
    )

    class Meta:
        verbose_name = "Liquidación por Metro Cuadrado"
        verbose_name_plural = "Liquidaciones por Metro Cuadrado"
        ordering = ["liquidacion_general"]

    def __str__(self):
        return f"Liquidación M2 {self.liquidacion_general}"


class LiquidacionPorCategoriaVisitas(BaseModel):
    """
    Cálculo por categoría de visitas de una liquidación de inspección de obra.

    Separa los datos de cálculo de la liquidación: relación con LiquidacionGeneral,
    cantidad de visitas solicitada, visitas base de cálculo (tras evaluar visitas_minimas),
    derecho calculado, categoría de inspección y referencia a la tarifa por categoría aplicada.
    """

    history = HistoricalRecords()

    liquidacion_general = models.ForeignKey(
        LiquidacionGeneral,
        on_delete=models.CASCADE,
        related_name="liquidacion_visitas",
        verbose_name="Liquidación General",
    )

    cantidad_visitas = models.PositiveIntegerField(
        default=1,
        verbose_name="Cantidad de Visitas",
        help_text="Número de visitas de inspección solicitadas.",
    )

    porcentaje_uit = models.DecimalField(
        max_digits=5,
        decimal_places=4,
        default=Decimal("0"),
        verbose_name="Porcentaje UIT",
        help_text="Porcentaje de la UIT que se aplica para calcular el derecho.",
    )

    categoria = models.CharField(
        max_length=20,
        verbose_name="Categoría de Inspección",
        help_text="Categoría de inspección: A, B, C, etc.",
    )

    tarifa_aplicada = models.ForeignKey(
        "TarifaPorCategoriaVisitas",
        on_delete=models.PROTECT,
        related_name="liquidaciones_visitas",
        verbose_name="Tarifa Aplicada",
        help_text="Tarifa por categoría de visitas que se aplicó para calcular el derecho.",
    )
    
    class Meta:
        verbose_name = "Liquidación por Categoría de Visitas"
        verbose_name_plural = "Liquidaciones por Categoría de Visitas"
        ordering = ["liquidacion_general", "categoria"]

    def __str__(self):
        return f"Liquidación Visitas {self.liquidacion_general}"


class LiquidacionPorcentajeObra(BaseModel):
    """
    Cálculo porcentual de una liquidación de obra.

    Separa los datos de cálculo de la liquidación: relación con LiquidacionGeneral,
    valores del proyecto, y referencia a la tarifa porcentual aplicada.
    """

    history = HistoricalRecords()

    liquidacion_general = models.OneToOneField(
        LiquidacionGeneral,
        on_delete=models.CASCADE,
        related_name="liquidacion_porcentaje_obra",
        verbose_name="Liquidación General",
    )

    tipo_tramite = models.CharField(
        max_length=30,
        choices=TipoTramiteEdificaciones.choices,
        verbose_name="Tipo de Trámite",
        null=True,
        blank=True,
        help_text="Tipo de trámite de edificación: obra nueva, ampliación, remodelación, demolición, etc.",
    )

    valor_declarado = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        verbose_name="Valor del Proyecto",
        help_text="Valor total del proyecto de edificación.",
    )
    
    porcentaje_liquidacion = models.DecimalField(
        max_digits=7,
        decimal_places=4,
        verbose_name="Porcentaje de Liquidación",
        help_text="Porcentaje aplicado para el cálculo del derecho (ej: 0.0015 para 0.15%).",
    )

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
        max_digits=5,
        decimal_places=4,
        verbose_name="Porcentaje Mínimo UIT",
        help_text="Mínimo como porcentaje de la UIT (protección para montos bajos).",
    )
    
    tarifas_aplicadas = models.ManyToManyField(
        "liquidaciones.TarifaPorcentajeObra",
        through="LiquidacionPorcentajeObraDetalle",
        related_name="liquidaciones_porcentuales",
        verbose_name="Tarifas Aplicadas",
        help_text="Tarifas porcentuales aplicadas para el cálculo del derecho por especialidad.",
    )
    
    derecho_aplicado = models.ForeignKey(
        "DerechoPorcentajeObra",
        on_delete=models.PROTECT,
        related_name="liquidaciones_porcentuales",
        verbose_name="Derecho Aplicado",
        help_text="Derecho calculado según la tarifa porcentual.",
    )
 
    class Meta:
        verbose_name = "Liquidación Porcentual de Obra"
        verbose_name_plural = "Liquidaciones Porcentuales de Obra"
        ordering = ["liquidacion_general"]

    def __str__(self):
        return f"Liquidación Porcentual {self.liquidacion_general}"


class LiquidacionPorcentajeObraDetalle(BaseModel):
    """
    Detalle del cálculo porcentual de una liquidación de obra por especialidad.

    Almacena el breakdown por especialidad: porcentaje aplicado y subtotal
    parcial correspondiente a cada especialidad involucrada.
    El IGV y el Total se calculan a nivel GLOBAL (en LiquidacionGeneral),
    NO por tarifa — por eso el detalle solo guarda el subtotal parcial.
    """

    history = HistoricalRecords()

    liquidacion_porcentaje = models.ForeignKey(
        "LiquidacionPorcentajeObra",
        on_delete=models.CASCADE,
        related_name="detalles",
        verbose_name="Liquidación Porcentual de Obra",
    )

    tarifa_aplicada = models.ForeignKey(
        "TarifaPorcentajeObra",
        on_delete=models.PROTECT,
        related_name="detalles_liquidacion",
        verbose_name="Tarifa Aplicada",
    )

    especialidad = models.ForeignKey(
        EspecialidadRevision,
        on_delete=models.PROTECT,
        related_name="detalles_porcentaje_obra",
        verbose_name="Especialidad de Revisión",
    )

    porcentaje_aplicado = models.DecimalField(
        max_digits=7,
        decimal_places=4,
        verbose_name="Porcentaje Aplicado",
        help_text="Porcentaje de la tarifa efectivamente aplicado a esta especialidad.",
    )

    subtotal = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        verbose_name="Subtotal Parcial",
        help_text="Monto subtotal parcial de esta especialidad (antes de IGV). "
        "El IGV y el total se calculan a nivel global en LiquidacionGeneral.",
    )

    importe_parcial = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        null=True,
        blank=True,
        verbose_name="Importe Parcial",
        help_text="Importe parcial calculado para esta especialidad.",
    )

    ajuste_redondeo = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        null=True,
        blank=True,
        verbose_name="Ajuste de Redondeo",
        help_text="Ajuste por redondeo aplicado a esta especialidad.",
    )

    class Meta:
        verbose_name = "Detalle de Liquidación Porcentual de Obra"
        verbose_name_plural = "Detalles de Liquidaciones Porcentuales de Obra"
        ordering = ["liquidacion_porcentaje", "especialidad"]
        constraints = [
            models.UniqueConstraint(
                fields=["liquidacion_porcentaje", "especialidad"],
                name="unique_liquidacion_porcentaje_detalle_especialidad",
            ),
        ]

    def __str__(self):
        return f"Detalle {self.especialidad} - {self.liquidacion_porcentaje}"
