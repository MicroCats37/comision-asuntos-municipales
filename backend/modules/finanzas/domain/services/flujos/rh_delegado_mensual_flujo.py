"""
RH Delegado Mensual Flujos — cotización y creación del RH mensual del delegado.

- RHDelegadoMensualCotizarFlujo: cálculo puro, sin escritura a BD.
- RHDelegadoMensualCrearFlujo: persiste con @transaction.atomic.

Mirrors RHInspectorMensualCotizarFlujo / RHInspectorMensualCrearFlujo
but uses DB-backed tasas (TasaDelegado) instead of hardcoded constants.
"""
import uuid
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
    LiquidacionComprobanteMinimalResult,
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
            HttpError(400): Liquidación no tiene detalle porcentual para la especialidad,
                           o delegado_operacion_id no pertenece al delegado.
        """
        # 1. Delegado por CIP
        delegado = self.core.get_delegado_by_cip(payload.cip)
        if not delegado:
            raise HttpError(404, f"Delegado con CIP '{payload.cip}' no encontrado")

        # 2. Validar delegado_operacion_id y que pertenece al delegado
        try:
            delegado_operacion_uuid = uuid.UUID(payload.delegado_operacion_id)
        except (ValueError, TypeError):
            raise HttpError(400, f"delegado_operacion_id '{payload.delegado_operacion_id}' no es un UUID válido")
        
        operatividad = self.core.get_delegado_operacion_by_id(delegado_operacion_uuid)
        if not operatividad:
            raise HttpError(404, f"DelegadoOperacion '{payload.delegado_operacion_id}' no encontrada")
        if str(operatividad.delegado_id) != str(delegado.id):
            raise HttpError(400, f"La operatividad '{payload.delegado_operacion_id}' no pertenece al delegado '{payload.cip}'")

        # Gate: la operatividad debe tener tipo de liquidación asignado.
        # Sin tipo no hay tasa por tipo — no se permite fallback a una tasa global.
        if operatividad.tipo_liquidacion is None:
            raise HttpError(
                400,
                f"La operatividad '{payload.delegado_operacion_id}' no tiene tipo de liquidación asignado",
            )

        items: list[RHDelegadoCotizarItemResult] = []
        sub_total = Decimal("0")
        total_renta_cip = Decimal("0")
        total_aporte_codemu = Decimal("0")
        total_fondo_comun = Decimal("0")
        total_neto_honorario = Decimal("0")

        for item in payload.items:
            # 2. LiquidacionGeneral por ID (candidata — aún no tiene LiquidacionDelegado)
            # Use the method that prefetches comprobantes to avoid N+1.
            lg = self.core.get_liquidacion_general_with_comprobantes(item.liquidacion_general_id)
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

            # 4. Resolver tasas vigentes desde la BD (scoped por tipo de liquidación)
            tasas = self.core.get_tasa_delegado_vigente(
                operatividad.tipo_liquidacion
            )
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

            # 6. Resolver liquidacion_especifica_numero y comprobante_activo
            liquidacion_especifica_numero = _resolve_liquidacion_especifica_numero(lg)
            comprobante_activo = _resolve_comprobante_activo(lg)

            items.append(
                RHDelegadoCotizarItemResult(
                    exp_liqui=lg.expediente or "",
                    liquidacion_general_id=item.liquidacion_general_id,
                    especialidad_revision_id=item.especialidad_revision_id,
                    liquidacion_delegado_id=None,  # creado en crear()
                    delegado_operacion_id=str(operatividad.id),
                    imp_bruto=imp_bruto,
                    fecha_revision=str(item.fecha_revision) if item.fecha_revision else None,
                    numero_revision=lg.numero_revision if hasattr(lg, 'numero_revision') else None,
                    total_liquidacion=lg.total,
                    sub_total_liquidacion=lg.sub_total,
                    renta_cip=item_renta_cip,
                    aporte_codemu=item_aporte_codemu,
                    fondo_comun=item_fondo_comun,
                    neto_honorario=item_neto_honorario,
                    numero_rh=item.numero_rh,
                    periodo=item.periodo,
                    mes=item.mes,
                    dictamen_revision=item.dictamen_revision,
                    fecha_presentacion=str(item.fecha_presentacion) if item.fecha_presentacion else None,
                    liquidacion_especifica_numero=liquidacion_especifica_numero,
                    comprobante_activo=comprobante_activo,
                )
            )

        # 5. Totales son la suma de los cálculos por item
        neto_honorario = total_neto_honorario

        perfil = getattr(delegado, "perfil_ingeniero", None)

        from modules.finanzas.domain.results.rh_delegado_mensual_result import (
            DelegadoRHMinimalResult,
            RHDelegadoVariablesCalculoResult,
        )

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
                sub_total=sub_total,
                renta_cip=total_renta_cip,
                aporte_codemu=total_aporte_codemu,
                fondo_comun=total_fondo_comun,
                neto_honorario=neto_honorario,
            ),
            variables_calculo=RHDelegadoVariablesCalculoResult(
                tasa_renta_cip=tasas.renta_cip,
                tasa_aporte_codemu=tasas.aporte_codemu,
                tasa_fondo_comun=tasas.fondo_comun,
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

        # Use delegado_operacion_id from first item (all items should have same operativity)
        operatividad_id = payload.delegado_operacion_id

        # 2. Crear la maestra mensual (siempre crea un nuevo RH header)
        rh = self.core.crear_rh_delegado_mensual(
            delegado_id=resultado.delegado.id,
            periodo=resultado.periodo,
            sub_total=resultado.totales.sub_total,
            renta_cip=resultado.totales.renta_cip,
            aporte_codemu=resultado.totales.aporte_codemu,
            fondo_comun=resultado.totales.fondo_comun,
            neto_honorario=resultado.totales.neto_honorario,
            delegado_operacion_id=operatividad_id,
        )

        # 3. Para cada item: crear LiquidacionDelegado primero,
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
                delegado_operacion_id=item.delegado_operacion_id,
            )
            # Populate liquidacion_delegado_id in the result item so the caller
            # receives the created IDs without needing a separate query.
            item.liquidacion_delegado_id = str(liq_delegado.id)
            self.core.crear_detalle_honorario_delegado(
                recibo_mensual_id=rh.id,
                liquidacion_delegado_id=liq_delegado.id,
                imp_bruto=item.imp_bruto,
            )

        return resultado


# ── Helper functions ────────────────────────────────────────────────────────────


def _resolve_liquidacion_especifica_numero(lg: "LiquidacionGeneral") -> int | None:
    """
    Resolve the specific liquidation numero from the LiquidacionGeneral.

    Accesses the one-to-one related specific model (Edificaciones, Taludes, etc.)
    based on tipo_liquidacion.codigo and returns its numero field.

    Returns None for legacy records that don't have a specific relation.
    """
    if not lg or not lg.tipo_liquidacion:
        return None

    codigo = lg.tipo_liquidacion.codigo

    # Map tipo_liquidacion.codigo to related_name for the OneToOne relation
    # that holds the AutoNumeroModel.numero field.
    RELATED_NAME_BY_TIPO = {
        "EDIFICACION": "edificaciones",
        "TALUDES": "taludes",
        "HABILITACION_URBANA": "habilitacion_urbana",
        "MECANICA_SUELOS": "mecanica_suelos",
        "INSPECCION_OBRA": "inspeccion_obra",
        "IMPACTO_VIAL": "impacto_vial",
    }

    related_name = RELATED_NAME_BY_TIPO.get(codigo)
    if not related_name:
        return None

    specific = getattr(lg, related_name, None)
    if not specific:
        return None

    return getattr(specific, "numero", None)


def _resolve_comprobante_activo(
    lg: "LiquidacionGeneral",
) -> "LiquidacionComprobanteMinimalResult | None":
    """
    Resolve the active comprobante from the LiquidacionGeneral.

    Uses the prefetched 'comprobantes_activos' attribute (set by
    get_liquidacion_general_with_comprobantes) to avoid N+1 queries.

    Returns None if no active comprobante exists.
    """
    if not lg:
        return None

    # The prefetch sets 'comprobantes_activos' as a list attribute
    comprobantes_activos = getattr(lg, "comprobantes_activos", None)
    if not comprobantes_activos:
        # Fallback: try accessing via the normal related manager
        # (shouldn't be needed if prefetch was used)
        try:
            activo = lg.comprobantes.filter(activo=True).first()
        except Exception:
            return None
    else:
        activo = comprobantes_activos[0] if comprobantes_activos else None

    if not activo:
        return None

    return LiquidacionComprobanteMinimalResult(
        tipo_comprobante=activo.tipo_comprobante,
        serie=activo.serie,
        numero=activo.numero,
        fecha_emision=str(activo.fecha_emision) if activo.fecha_emision else None,
    )
