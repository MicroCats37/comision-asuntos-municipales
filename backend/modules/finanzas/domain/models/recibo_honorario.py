"""
Recibo de Honorarios del Delegado — modelo de dominio.

Generado desde una LiquidacionDelegado (asignación liquidación+delegado+especialidad).
Equivale a la tabla legacy CT46201.
"""

from decimal import Decimal, ROUND_HALF_UP

from django.db import models
from simple_history.models import HistoricalRecords

from core.models import BaseModel
from modules.finanzas.domain.results.recibo_honorario_result import CalculoHonorarioResult


# ── Fixed rate constants ────────────────────────────────────────────────────────

TASA_RENTA_CIP = Decimal("0.25")
TASA_APORTE_CODEMU = Decimal("0.05")
TASA_FONDO_COMUN = Decimal("0.10")


# ── Model ─────────────────────────────────────────────────────────────────────

class ReciboHonorarioDelegado(BaseModel):
    """
    Recibo de honorarios del delegado, generado desde una liquidación.

    Se apoya en LiquidacionDelegado (asignación liquidación+delegado+especialidad).
    El imp_bruto se toma del LiquidacionPorcentajeObraDetalle cuya especialidad
    coincide con la especialidad_revision de la asignación.
    """

    history = HistoricalRecords()

    liquidacion_delegado = models.OneToOneField(
        "liquidaciones.LiquidacionDelegado",
        on_delete=models.PROTECT,
        related_name="recibo_honorario",
        verbose_name="Asignación Delegado",
    )

    sub_total = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        verbose_name="Subtotal Liquidación",
    )

    imp_bruto = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        verbose_name="Importe Bruto",
    )

    renta_cip = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        verbose_name="Renta CIP",
    )

    aporte_codemu = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        verbose_name="Aporte CODEMU",
    )

    fondo_comun = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        verbose_name="Fondo Común",
    )

    neto_honorario = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        verbose_name="Neto Honorario",
    )

    honorario = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        verbose_name="Honorario",
    )

    class Meta:
        verbose_name = "Recibo de Honorarios del Delegado"
        verbose_name_plural = "Recibos de Honorarios del Delegado"
        ordering = ["-created_at"]

    def __str__(self):
        return f"ReciboHonorarioDelegado({self.liquidacion_delegado} - {self.honorario})"

    @staticmethod
    def _calcular_honorarios(imp_bruto: Decimal) -> CalculoHonorarioResult:
        """
        Helper privado que calcula los componentes del recibo de honorarios.

        Cumple con contrato 3B (helpers con prefijo _).

        Fixed rates:
            renta_cip     = imp_bruto × 0.25
            aporte_codemu = imp_bruto × 0.05
            fondo_comun   = imp_bruto × 0.10
            neto_honorario = imp_bruto − renta_cip − aporte_codemu − fondo_comun
            honorario     = neto_honorario

        Args:
            imp_bruto: Importe bruto (Decimal).

        Returns:
            CalculoHonorarioResult con todos los campos en Decimal (2 decimal places).
            Incluye imp_bruto para que el dict del wrapper no lo duplique.
        """
        TWO_PLACES = Decimal("0.01")

        renta_cip = (imp_bruto * TASA_RENTA_CIP).quantize(TWO_PLACES, rounding=ROUND_HALF_UP)
        aporte_codemu = (imp_bruto * TASA_APORTE_CODEMU).quantize(TWO_PLACES, rounding=ROUND_HALF_UP)
        fondo_comun = (imp_bruto * TASA_FONDO_COMUN).quantize(TWO_PLACES, rounding=ROUND_HALF_UP)
        neto_honorario = (imp_bruto - renta_cip - aporte_codemu - fondo_comun).quantize(
            TWO_PLACES, rounding=ROUND_HALF_UP
        )
        honorario = neto_honorario  # honorario equals neto_honorario per spec

        return CalculoHonorarioResult(
            imp_bruto=imp_bruto,
            renta_cip=renta_cip,
            aporte_codemu=aporte_codemu,
            fondo_comun=fondo_comun,
            neto_honorario=neto_honorario,
            honorario=honorario,
        )

    @staticmethod
    def calcular_honorarios(imp_bruto: Decimal) -> dict:
        """
        Wrapper público para backward compatibility con tests existentes.

        Returns un dict SIN imp_bruto (el caller lo pasa explícitamente
        para evitar keyword duplicate en objects.create).

        Returns:
            dict con keys: renta_cip, aporte_codemu, fondo_comun,
                           neto_honorario, honorario (all Decimal, 2 decimal places).
        """
        result = ReciboHonorarioDelegado._calcular_honorarios(imp_bruto)
        # Exclude imp_bruto from dict to avoid keyword duplicate in caller
        return {
            "renta_cip": result.renta_cip,
            "aporte_codemu": result.aporte_codemu,
            "fondo_comun": result.fondo_comun,
            "neto_honorario": result.neto_honorario,
            "honorario": result.honorario,
        }
