"""
ReciboHonorarioFlujo — flujo transaccional para crear/actualizar recibos de honorarios.

Único lugar con @transaction.atomic para esta operación (contrato 4).
"""
from decimal import Decimal, ROUND_HALF_UP

from django.db import transaction

from ninja.errors import HttpError

from modules.finanzas.domain.models.recibo_honorario import ReciboHonorarioDelegado
from modules.finanzas.domain.models.recibo_honorario_inspector import (
    ReciboHonorarioInspector,
)
from modules.finanzas.domain.services.finanzas_core_service import FinanzasCoreService


TWO_PLACES = Decimal("0.01")


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


class ReciboHonorarioInspectorFlujo:
    """
    Flujo transaccional para crear un ReciboHonorarioInspector.

    El @transaction.atomic garantiza consistencia total de la operación.
    """

    def __init__(self, core_service: FinanzasCoreService):
        self.core_service = core_service

    @transaction.atomic
    def crear_recibo_inspector(
        self,
        liquidacion_inspector_id,
        inspecciones_mes: int,
    ) -> ReciboHonorarioInspector:
        """
        Crea un ReciboHonorarioInspector a partir de una LiquidacionInspector.

        Cálculos:
            a) LiquidacionInspector con su LiquidacionPorCategoriaVisitas
               (cantidad_visitas) y la LiquidacionGeneral (sub_total).
            b) importe_bruto            = liquidacion_general.sub_total
            c) inspecciones_programadas = liquidacion_visitas.cantidad_visitas
            d) costo_por_inspeccion     = importe_bruto / inspecciones_programadas
            e) inspecciones_mes         = input
            f) monto_bruto              = costo_por_inspeccion * inspecciones_mes
            g) inspecciones_pagadas     = 0
            h) saldo_inspecciones       = programadas - mes - pagadas
            i) sub_total                = monto_bruto
            j) tasa_descuento_aplicada  = rango vigente según sub_total
            k) descuento                = sub_total * tasa_descuento_aplicada
            l) honorarios               = sub_total - descuento

        Args:
            liquidacion_inspector_id: FK a LiquidacionInspector.
            inspecciones_mes: Inspecciones liquidadas en el mes.

        Returns:
            ReciboHonorarioInspector instance.

        Raises:
            HttpError(404): LiquidacionInspector no encontrada.
            HttpError(400): Liquidación sin visitas programadas, sin escala
                            vigente o sin rango aplicable.
        """
        liquidacion_inspector = self._get_liquidacion_inspector(
            liquidacion_inspector_id
        )
        if not liquidacion_inspector:
            raise HttpError(
                404,
                f"LiquidacionInspector '{liquidacion_inspector_id}' no encontrada",
            )

        liquidacion_visitas = liquidacion_inspector.liquidacion
        liquidacion_general = liquidacion_visitas.liquidacion_general

        inspecciones_programadas = liquidacion_visitas.cantidad_visitas
        if not inspecciones_programadas or inspecciones_programadas <= 0:
            raise HttpError(
                400,
                "La liquidación no tiene visitas programadas válidas para "
                "calcular el costo por inspección",
            )

        importe_bruto = Decimal(str(liquidacion_general.sub_total))
        costo_por_inspeccion = (
            importe_bruto / Decimal(inspecciones_programadas)
        ).quantize(TWO_PLACES, rounding=ROUND_HALF_UP)
        monto_bruto = (
            costo_por_inspeccion * Decimal(inspecciones_mes)
        ).quantize(TWO_PLACES, rounding=ROUND_HALF_UP)
        inspecciones_pagadas = 0
        saldo_inspecciones = (
            inspecciones_programadas - inspecciones_mes - inspecciones_pagadas
        )
        sub_total = monto_bruto

        escala = self.core_service.get_escala_descuento_vigente()
        if not escala:
            raise HttpError(
                400,
                "No hay una escala de descuento vigente para inspectores",
            )

        rango = self.core_service.get_rango_para_monto(escala, sub_total)
        if not rango:
            raise HttpError(
                400,
                f"No se encontró rango de descuento para el monto {sub_total}",
            )

        tasa_descuento_aplicada = Decimal(str(rango.porcentaje_descuento))
        descuento = (sub_total * tasa_descuento_aplicada).quantize(
            TWO_PLACES, rounding=ROUND_HALF_UP
        )
        honorarios = (sub_total - descuento).quantize(
            TWO_PLACES, rounding=ROUND_HALF_UP
        )

        return self.core_service.crear_recibo_inspector(
            liquidacion_inspector_id=liquidacion_inspector_id,
            escala_descuento=escala,
            inspecciones_programadas=inspecciones_programadas,
            costo_por_inspeccion=costo_por_inspeccion,
            inspecciones_mes=inspecciones_mes,
            monto_bruto=monto_bruto,
            inspecciones_pagadas=inspecciones_pagadas,
            saldo_inspecciones=saldo_inspecciones,
            sub_total=sub_total,
            tasa_descuento_aplicada=tasa_descuento_aplicada,
            descuento=descuento,
            honorarios=honorarios,
        )

    @staticmethod
    def _get_liquidacion_inspector(liquidacion_inspector_id):
        """
        Fetch LiquidacionInspector by PK with its tipo (visitas) and general loaded.
        """
        from modules.liquidaciones.domain.models.inspector import LiquidacionInspector

        return LiquidacionInspector.objects.select_related(
            "liquidacion__liquidacion_general",
        ).filter(id=liquidacion_inspector_id).first()
