"""
RH Delegado Mensual Flujos — cotización y creación del RH mensual del delegado.

- RHDelegadoMensualCotizarFlujo: cálculo puro, sin escritura a BD.
- RHDelegadoMensualCrearFlujo: persiste con @transaction.atomic.

Mirrors RHInspectorMensualCotizarFlujo / RHInspectorMensualCrearFlujo
but uses DB-backed tasas (TasaDelegado) instead of hardcoded constants.
"""
from decimal import Decimal, ROUND_HALF_UP

from django.db import transaction
from injector import inject
from ninja.errors import HttpError

from modules.finanzas.domain.services.finanzas_core_service import FinanzasCoreService
from modules.finanzas.domain.schemas import RHDelegadoCotizarIn
from modules.finanzas.domain.results.rh_delegado_mensual_result import (
    RHDelegadoCotizarItemResult,
    RHDelegadoTotalesResult,
    RHDelegadoCotizarResult,
)

TWO_PLACES = Decimal("0.01")


class RHDelegadoMensualCotizarFlujo:
    """
    Cálculo del RH mensual del delegado SIN persistencia (cotización).

    Solo consultas a través del core. No escribe en la base de datos.

    Algoritmo:
    1. Resolve Delegado by CIP.
    2. For each exp_liqui:
       a. Find LiquidacionGeneral by expediente.
       b. Extract imp_bruto from LiquidacionPorcentajeObraDetalle using especialidad_revision.
       c. Calculate per-item deductions: renta_cip, aporte_codemu, fondo_comun, neto_honorario.
       d. Accumulate sub_total += imp_bruto.
    3. Totals are sum of per-item deductions.
    4. Return result with per-item breakdown.
    """

    @inject
    def __init__(self, core: FinanzasCoreService):
        self.core = core

    def cotizar(self, payload: RHDelegadoCotizarIn) -> RHDelegadoCotizarResult:
        """
        Valida y calcula el RH mensual sin guardar nada.

        Args:
            payload: Datos de cotización con CIP, periodo e items
                     (liquidacion_general_id + especialidad_revision_id).

        Returns:
            RHDelegadoCotizarResult con el detalle de cálculos.

        Raises:
            HttpError(404): Delegado o liquidación no encontrada.
            HttpError(400): Liquidación no tiene detalle porcentual para la especialidad.
        """
        # 1. Delegado por CIP
        delegado = self.core.get_delegado_by_cip(payload.cip)
        if not delegado:
            raise HttpError(404, f"Delegado con CIP '{payload.cip}' no encontrado")

        items: list[RHDelegadoCotizarItemResult] = []
        sub_total = Decimal("0")
        total_renta_cip = Decimal("0")
        total_aporte_codemu = Decimal("0")
        total_fondo_comun = Decimal("0")
        total_neto_honorario = Decimal("0")

        for item in payload.items:
            # 2. LiquidacionGeneral por ID (candidata — aún no tiene LiquidacionDelegado)
            lg = self.core.get_liquidacion_general_by_id(item.liquidacion_general_id)
            if not lg:
                raise HttpError(
                    404,
                    f"Liquidación con ID '{item.liquidacion_general_id}' no encontrada",
                )

            # 3. Extraer imp_bruto del LiquidacionPorcentajeObraDetalle
            #    que coincide con liquidacion_general_id + especialidad_revision_id.
            #    No se requiere LiquidacionDelegado — trabaja directamente sobre
            #    LiquidacionPorcentajeObraDetalle.
            imp_bruto = self.core.get_imp_bruto_delegado(
                item.liquidacion_general_id, item.especialidad_revision_id
            )
            if imp_bruto is None:
                raise HttpError(
                    400,
                    f"La liquidación '{lg.expediente or item.liquidacion_general_id}' "
                    f"no tiene detalle porcentual para la especialidad "
                    f"{item.especialidad_revision_id}",
                )

            # 4. Resolver tasas vigentes desde la BD
            tasas = self.core.get_tasa_delegado_vigente()
            if not tasas:
                raise HttpError(400, "No hay tasas de delegado vigentes")

            # 5. Calcular descuentos POR ITEM
            item_renta_cip = (imp_bruto * tasas.renta_cip).quantize(TWO_PLACES, rounding=ROUND_HALF_UP)
            item_aporte_codemu = (imp_bruto * tasas.aporte_codemu).quantize(TWO_PLACES, rounding=ROUND_HALF_UP)
            item_fondo_comun = (imp_bruto * tasas.fondo_comun).quantize(TWO_PLACES, rounding=ROUND_HALF_UP)
            item_neto_honorario = (
                imp_bruto - item_renta_cip - item_aporte_codemu - item_fondo_comun
            ).quantize(TWO_PLACES, rounding=ROUND_HALF_UP)

            # Acumular totales
            sub_total += imp_bruto
            total_renta_cip += item_renta_cip
            total_aporte_codemu += item_aporte_codemu
            total_fondo_comun += item_fondo_comun
            total_neto_honorario += item_neto_honorario

            items.append(
                RHDelegadoCotizarItemResult(
                    exp_liqui=lg.expediente or "",
                    liquidacion_general_id=item.liquidacion_general_id,
                    especialidad_revision_id=item.especialidad_revision_id,
                    liquidacion_delegado_id=None,  # creado en crear()
                    imp_bruto=float(imp_bruto),
                    fecha_revision=str(item.fecha_revision) if item.fecha_revision else None,
                    numero_revision=lg.numero_revision if hasattr(lg, 'numero_revision') else None,
                    total_liquidacion=float(lg.total) if lg.total else None,
                    sub_total_liquidacion=float(lg.sub_total) if lg.sub_total else None,
                    renta_cip=float(item_renta_cip),
                    aporte_codemu=float(item_aporte_codemu),
                    fondo_comun=float(item_fondo_comun),
                    neto_honorario=float(item_neto_honorario),
                    numero_rh=item.numero_rh,
                    periodo=item.periodo,
                    mes=item.mes,
                    dictamen_revision=item.dictamen_revision,
                    fecha_presentacion=str(item.fecha_presentacion) if item.fecha_presentacion else None,
                )
            )

        # 5. Totales son la suma de los cálculos por item
        neto_honorario = total_neto_honorario

        perfil = getattr(delegado, "perfil_ingeniero", None)

        from modules.finanzas.domain.results.rh_delegado_mensual_result import DelegadoRHMinimalResult

        return RHDelegadoCotizarResult(
            delegado=DelegadoRHMinimalResult(
                id=str(delegado.id),
                nombre_completo=perfil.nombre_completo if perfil else "",
                cip=perfil.cip if perfil else "",
                dni=perfil.dni if perfil else "",
            ),
            periodo=payload.periodo,
            items=items,
            totales=RHDelegadoTotalesResult(
                sub_total=float(sub_total),
                renta_cip=float(total_renta_cip),
                aporte_codemu=float(total_aporte_codemu),
                fondo_comun=float(total_fondo_comun),
                neto_honorario=float(neto_honorario),
            ),
        )


class RHDelegadoMensualCrearFlujo:
    """
    Crea el RH mensual del delegado con persistencia (transaction.atomic).

    Reutiliza RHDelegadoMensualCotizarFlujo para validar y calcular,
    luego persiste la maestra y los detalles.
    """

    @inject
    def __init__(
        self,
        core: FinanzasCoreService,
        cotizar_flujo: RHDelegadoMensualCotizarFlujo,
    ):
        self.core = core
        self.cotizar_flujo = cotizar_flujo

    @transaction.atomic
    def crear(self, payload: RHDelegadoCotizarIn) -> RHDelegadoCotizarResult:
        """
        Cotiza, crea la maestra + detalles.

        Única operación con @transaction.atomic en este dominio.

        Para cada item de candidata:
        1. Crear LiquidacionDelegado (asignación que no existía aún).
        2. Crear DetalleHonorarioDelegado apuntando a ese LiquidacionDelegado.

        Args:
            payload: Datos de cotización con CIP, periodo e items.

        Returns:
            RHDelegadoCotizarResult con los datos persistidos.

        Raises:
            HttpError(404/400): Cualquier error de validación propagado
                               desde cotizar_flujo.cotizar().
        """
        # 1. Calcular (reutiliza la lógica de cotizar, que valida todo)
        resultado = self.cotizar_flujo.cotizar(payload)

        # 2. Crear/obtener la maestra mensual (idempotente por delegado+periodo)
        rh, _ = self.core.crear_rh_delegado_mensual(
            delegado_id=resultado.delegado.id,
            periodo=resultado.periodo,
            sub_total=Decimal(str(resultado.totales.sub_total)),
            renta_cip=Decimal(str(resultado.totales.renta_cip)),
            aporte_codemu=Decimal(str(resultado.totales.aporte_codemu)),
            fondo_comun=Decimal(str(resultado.totales.fondo_comun)),
            neto_honorario=Decimal(str(resultado.totales.neto_honorario)),
        )

        # 3. Eliminar detalles existentes (para soportar re-cálculo)
        self.core.delete_detalles_honorario_delegado(rh.id)

        # 4. Para cada item: crear LiquidacionDelegado primero,
        #    luego DetalleHonorarioDelegado con el ID recién creado.
        #    Usa per-item periodo/mes/dictamen/fechas si están presentes,
        #    si no recurre al nivel RH.
        for item in resultado.items:
            # Extraer año y mes del periodo YYYY-MM del RH header
            item_periodo = item.periodo
            item_mes = item.mes
            if item_periodo is None:
                # Fallback: parsear YYYY-MM del nivel RH
                rh_periodo = resultado.periodo  # YYYY-MM
                if rh_periodo and len(rh_periodo) >= 4:
                    item_periodo = int(rh_periodo[:4])
                    if len(rh_periodo) >= 7:
                        try:
                            item_mes = int(rh_periodo[5:7])
                        except (ValueError, TypeError):
                            item_mes = None
            liq_delegado, _ = self.core.crear_liquidacion_delegado(
                liquidacion_id=item.liquidacion_general_id,
                delegado_id=resultado.delegado.id,
                especialidad_revision_id=item.especialidad_revision_id,
                numero_rh=item.numero_rh,
                periodo=item_periodo,
                mes=item_mes,
                dictamen_revision=item.dictamen_revision,
                fecha_presentacion=item.fecha_presentacion,
                fecha_revision=item.fecha_revision,
            )
            self.core.crear_detalle_honorario_delegado(
                recibo_mensual_id=rh.id,
                liquidacion_delegado_id=liq_delegado.id,
                imp_bruto=Decimal(str(item.imp_bruto)),
            )

        return resultado
