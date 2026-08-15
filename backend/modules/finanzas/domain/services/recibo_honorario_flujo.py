"""
ReciboHonorarioFlujo — flujo transaccional para crear/actualizar recibos de honorarios.

Único lugar con @transaction.atomic para esta operación (contrato 4).
"""
from decimal import Decimal

from django.db import transaction

from modules.finanzas.domain.models.recibo_honorario import ReciboHonorarioDelegado
from modules.finanzas.domain.services.finanzas_core_service import FinanzasCoreService


class ReciboHonorarioFlujo:
    """
    Flujo para crear o actualizar un ReciboHonorarioDelegado.

    El @transaction.atomic garantiza consistencia even if the record already exists
    and needs to be updated.
    """

    def __init__(self, core_service: FinanzasCoreService):
        self.core_service = core_service

    @transaction.atomic
    def ejecutar_crear_recibo(
        self,
        liquidacion_delegado_id: int,
        sub_total: Decimal,
        imp_bruto: Decimal,
        renta_cip: Decimal,
        aporte_codemu: Decimal,
        fondo_comun: Decimal,
        neto_honorario: Decimal,
        honorario: Decimal,
    ) -> ReciboHonorarioDelegado:
        """
        Crea o actualiza un ReciboHonorarioDelegado.

        Uses get_or_create for idempotency. Si el registro ya existe,
        actualiza todos los montos (no los ignora).

        Args:
            liquidacion_delegado_id: FK a LiquidacionDelegado.
            sub_total: Snapshot del sub_total de LiquidacionGeneral.
            imp_bruto: Importe bruto (subtotal del LiquidacionPorcentajeObraDetalle).
            renta_cip: imp_bruto × 0.25.
            aporte_codemu: imp_bruto × 0.05.
            fondo_comun: imp_bruto × 0.10.
            neto_honorario: imp_bruto − renta_cip − aporte_codemu − fondo_comun.
            honorario: Igual a neto_honorario.

        Returns:
            ReciboHonorarioDelegado instance.
        """
        recibo, created = self.core_service.crear_recibo(
            liquidacion_delegado_id=liquidacion_delegado_id,
            sub_total=sub_total,
            imp_bruto=imp_bruto,
            renta_cip=renta_cip,
            aporte_codemu=aporte_codemu,
            fondo_comun=fondo_comun,
            neto_honorario=neto_honorario,
            honorario=honorario,
        )

        if not created:
            # Update existing record's montos instead of skipping
            recibo.sub_total = sub_total
            recibo.imp_bruto = imp_bruto
            recibo.renta_cip = renta_cip
            recibo.aporte_codemu = aporte_codemu
            recibo.fondo_comun = fondo_comun
            recibo.neto_honorario = neto_honorario
            recibo.honorario = honorario
            recibo.save()

        return recibo
