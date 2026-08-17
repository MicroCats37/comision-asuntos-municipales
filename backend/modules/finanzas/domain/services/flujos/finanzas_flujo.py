"""
FinanzasFlujo — flujos de negocio para finanzas.

Cada método _proceso_* es un caso de uso completo.
"""
from decimal import Decimal

from injector import inject

from modules.finanzas.domain.services.finanzas_core_service import FinanzasCoreService
from modules.finanzas.domain.schemas import VariablesVigentesResult


class FinanzasFlujo:
    """
    Flujos para finanzas — _proceso_obtener_variables_vigentes.

    Inyecta FinanzasCoreService para operaciones ORM.
    """

    @inject
    def __init__(self, core: FinanzasCoreService):
        self.core = core

    def _proceso_obtener_variables_vigentes(self) -> VariablesVigentesResult:
        """
        Flujo para obtener las variables financieras vigentes (IGV y UIT).

        1. Consulta el IGV vigente vía CoreService.
        2. Consulta la UIT vigente vía CoreService.
        3. Construye el resultado agregado.

        Returns:
            VariablesVigentesResult con los valores vigentes
        """
        igv = self.core.get_igv_vigente()
        uit = self.core.get_uit_vigente()
        return VariablesVigentesResult.from_igv_uit(igv, uit)

    def _proceso_crear_recibo(
        self,
        liquidacion_delegado_id: int,
        sub_total: Decimal,
        imp_bruto: Decimal,
        renta_cip: Decimal,
        aporte_codemu: Decimal,
        fondo_comun: Decimal,
        neto_honorario: Decimal,
        honorario: Decimal,
    ):
        """
        Flujo para crear o actualizar un ReciboHonorarioDelegado.

        El @transaction.atomic vive en el ReciboHonorarioFlujo.

        Args:
            liquidacion_delegado_id: FK numérica a LiquidacionDelegado.
            sub_total: Snapshot del sub_total de LiquidacionGeneral.
            imp_bruto: Importe bruto del LiquidacionPorcentajeObraDetalle.
            renta_cip: imp_bruto × 0.25.
            aporte_codemu: imp_bruto × 0.05.
            fondo_comun: imp_bruto × 0.10.
            neto_honorario: imp_bruto − renta_cip − aporte_codemu − fondo_comun.
            honorario: Igual a neto_honorario.
        """
        from modules.finanzas.domain.services.recibo_honorario_flujo import (
            ReciboHonorarioFlujo,
        )

        flujo = ReciboHonorarioFlujo(core_service=self.core)
        return flujo.ejecutar_crear_recibo(
            liquidacion_delegado_id=liquidacion_delegado_id,
            sub_total=sub_total,
            imp_bruto=imp_bruto,
            renta_cip=renta_cip,
            aporte_codemu=aporte_codemu,
            fondo_comun=fondo_comun,
            neto_honorario=neto_honorario,
            honorario=honorario,
        )

    def _proceso_crear_recibo_inspector(
        self,
        liquidacion_inspector_id,
        inspecciones_mes: int,
    ):
        """
        Flujo para crear un ReciboHonorarioInspector.

        El @transaction.atomic vive en el ReciboHonorarioInspectorFlujo.

        Args:
            liquidacion_inspector_id: FK a LiquidacionInspector.
            inspecciones_mes: Inspecciones liquidadas en el mes.
        """
        from modules.finanzas.domain.services.recibo_honorario_flujo import (
            ReciboHonorarioInspectorFlujo,
        )

        flujo = ReciboHonorarioInspectorFlujo(core_service=self.core)
        return flujo.crear_recibo_inspector(
            liquidacion_inspector_id=liquidacion_inspector_id,
            inspecciones_mes=inspecciones_mes,
        )
