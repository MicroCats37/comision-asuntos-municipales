"""
LiquidacionComprobante — comprobantes de liquidación.

Una liquidación puede tener muchos comprobantes en historial, pero solo uno activo.
Si se reemplaza en futuro: anterior activo=False, nuevo activo=True.
"""

from django.db import models
from core.models import BaseModel


class TipoComprobante(models.TextChoices):
    """Tipos de comprobante de liquidación."""

    FACTURA = "FACTURA", "Factura"
    BOLETA = "BOLETA", "Boleta"
    NOTA_CREDITO = "NOTA_CREDITO", "Nota de Crédito"
    NOTA_DEBITO = "NOTA_DEBITO", "Nota de Débito"


class LiquidacionComprobante(BaseModel):
    """
    Comprobante de liquidación (factura/boleta) asociado a una LiquidacionGeneral.

    Regla de negocio: una liquidación puede tener muchos comprobantes en historial,
    pero solo uno activo. Si se reemplaza en el futuro: anterior activo=False,
    nuevo activo=True.
    """

    liquidacion_general = models.ForeignKey(
        "LiquidacionGeneral",
        on_delete=models.CASCADE,
        related_name="comprobantes",
        verbose_name="Liquidación General",
    )

    tipo_comprobante = models.CharField(
        max_length=20,
        choices=TipoComprobante.choices,
        blank=True,
        null=True,
        verbose_name="Tipo de Comprobante",
    )

    serie = models.CharField(
        max_length=20,
        blank=True,
        null=True,
        verbose_name="Serie",
    )

    numero = models.CharField(
        max_length=50,
        blank=True,
        null=True,
        verbose_name="Número",
    )

    fecha_emision = models.DateField(
        blank=True,
        null=True,
        verbose_name="Fecha de Emisión",
    )

    monto = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        blank=True,
        null=True,
        verbose_name="Monto",
    )

    activo = models.BooleanField(
        default=True,
        verbose_name="¿Activo?",
        help_text="Indica si este es el comprobante activo de la liquidación.",
    )

    motivo_reemplazo = models.CharField(
        max_length=500,
        blank=True,
        null=True,
        verbose_name="Motivo de Reemplazo",
        help_text="Motivo por el cual este comprobante reemplazó a uno anterior.",
    )

    class Meta:
        verbose_name = "Comprobante"
        verbose_name_plural = "Comprobantes"
        ordering = ["liquidacion_general", "-created_at"]
        constraints = [
            models.UniqueConstraint(
                fields=["liquidacion_general"],
                condition=models.Q(activo=True),
                name="unique_liquidacion_comprobante_activo",
            ),
        ]

    def __str__(self):
        tipo = self.tipo_comprobante or "Sin tipo"
        numero = self.numero or "S/N"
        return f"{tipo} {self.serie or ''}-{numero} @ {self.liquidacion_general}"
