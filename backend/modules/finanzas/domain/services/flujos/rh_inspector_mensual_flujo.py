"""
RH Inspector Mensual Flujos — cotización y creación del RH mensual del inspector.

- RHInspectorMensualCotizarFlujo: cálculo puro, sin escritura a BD.
- RHInspectorMensualCrearFlujo: persiste con @transaction.atomic.

Único lugar con @transaction.atomic para la creación (contrato 4).
"""
from decimal import Decimal, ROUND_HALF_UP
from typing import Any

from django.db import transaction
from django.db.models import Prefetch
from injector import inject
from ninja.errors import HttpError

from modules.finanzas.domain.services.finanzas_core_service import FinanzasCoreService
from modules.finanzas.domain.schemas import (
    RHInspectorActualizarIn,
    RHInspectorCotizarIn,
    RHInspectorCotizarItemIn,
)
from modules.finanzas.domain.results.rh_inspector_mensual_result import (
    RHInspectorCotizarItemResult,
    RHInspectorTotalesResult,
    RHInspectorCotizarResult,
)
from modules.finanzas.domain.services.flujos.rh_delegado_mensual_flujo import (
    _resolve_liquidacion_especifica_numero,
    _resolve_comprobante_activo,
)
from modules.liquidaciones.domain.models.liquidacion.liquidacion_general.liquidacion import (
    LiquidacionGeneral,
)
from modules.liquidaciones.domain.models.liquidacion.liquidacion_general.comprobante import (
    LiquidacionComprobante,
)

TWO_PLACES = Decimal("0.01")

# Reverse one-to-one accessors of LiquidacionGeneral that hold the specific
# liquidation `numero`. Mirrors RELATED_NAME_BY_TIPO of the RH Delegado helpers so
# the resolution never falls back to a lazy per-row query (N+1).
_RELATED_NAME_ESPECIFICAS = (
    "edificaciones",
    "taludes",
    "habilitacion_urbana",
    "mecanica_suelos",
    "inspeccion_obra",
    "impacto_vial",
)


def _enriquecer_candidatas_inspector(candidatos_data: list[dict]) -> list[dict]:
    """
    Agrega a cada candidata los datos de la liquidación que el listado mensual del
    inspector ya expone: `liquidacion_especifica_numero` y `comprobante_activo`.

    El core service devuelve dicts planos (descarta el modelo LiquidacionGeneral),
    así que el flujo resuelve ambos datos con UNA consulta batch (select_related de
    las liquidaciones específicas) + un prefetch del comprobante activo, sin N+1.
    Reutiliza los mismos helpers del RH Delegado para no duplicar reglas.

    Modifica los dicts in-place y los devuelve.
    """
    if not candidatos_data:
        return candidatos_data

    comprobantes_activos = LiquidacionComprobante.objects.filter(activo=True).order_by(
        "-fecha_emision", "-id"
    )
    liquidaciones = {
        str(lg.id): lg
        for lg in LiquidacionGeneral.objects.filter(
            id__in=[data["liquidacion_general_id"] for data in candidatos_data]
        )
        .select_related("tipo_liquidacion", *_RELATED_NAME_ESPECIFICAS)
        .prefetch_related(
            Prefetch("comprobantes", queryset=comprobantes_activos, to_attr="comprobantes_activos")
        )
    }

    for data in candidatos_data:
        lg = liquidaciones.get(data["liquidacion_general_id"])
        data["liquidacion_especifica_numero"] = (
            _resolve_liquidacion_especifica_numero(lg) if lg is not None else None
        )
        data["comprobante_activo"] = (
            _resolve_comprobante_activo(lg) if lg is not None else None
        )

    return candidatos_data


class RHInspectorMensualCotizarFlujo:
    """
    Cálculo del RH mensual del inspector SIN persistencia (cotización).

    Solo consultas a través del core. No escribe en la base de datos.
    """

    @inject
    def __init__(self, core: FinanzasCoreService):
        self.core = core

    def cotizar(
        self,
        payload: RHInspectorCotizarIn,
        exclude_recibo_mensual_id=None,
        escala_override=None,
    ) -> RHInspectorCotizarResult:
        """
        Valida y calcula el RH mensual sin guardar nada.

        Args:
            payload: Datos de cotización con CIP, periodo e items.
            exclude_recibo_mensual_id: Recibo mensual a EXCLUIR del cálculo de
                saldo. Lo usa la reconciliación (PATCH) para que el RH no se
                descuente a sí mismo de su propio balance.
            escala_override: EscalaDescuentoInspector opcional. Cuando se
                entrega, la cotización usa esa escala congelada en lugar de la
                escala vigente.

        Returns:
            RHInspectorCotizarResult con el detalle de cálculos.

        Raises:
            HttpError(404): Inspector o liquidación no encontrada.
            HttpError(400): Validación de negocio fallida (escala inexistente,
                           liquidación sin visitas, IO no asociada al inspector,
                           saldo insuficiente).
        """
        # 1. Inspector por CIP
        inspector = self.core.get_inspector_by_cip(payload.cip)
        if not inspector:
            raise HttpError(404, f"Inspector con CIP '{payload.cip}' no encontrado")

        # 2. Escala vigente (o la escala congelada del recibo en la reconciliación)
        if escala_override is not None:
            escala = escala_override
        else:
            escala = self.core.get_escala_descuento_vigente()
        if not escala:
            raise HttpError(400, "No hay escala de descuento vigente")

        items: list[RHInspectorCotizarItemResult] = []
        sub_total = Decimal("0")
        header_periodo = payload.periodo
        header_mes = payload.mes

        for item in payload.items:
            # 3a. Resolver liquidacion_categoria_visitas_id
            # Soporta dos flujos de entrada: por exp_liqui (manual) o por liquidacion_categoria_visitas_id (candidatas)
            if item.liquidacion_categoria_visitas_id:
                # Flujo por candidatas: usar directamente el ID de la IO
                lcv = self.core.get_liquidacion_categoria_visitas_by_id(item.liquidacion_categoria_visitas_id)
                if not lcv:
                    raise HttpError(
                        404,
                        "Liquidación por categoría de visitas no encontrada.",
                    )
                lg = self.core.get_liquidacion_general_by_id(lcv.liquidacion_general_id)
                if not lg:
                    raise HttpError(
                        404,
                        "Liquidación general para IO no encontrada.",
                    )
                exp_liqui = str(lg.expediente or "")
            else:
                # Flujo manual: buscar por expediente
                if not item.exp_liqui:
                    raise HttpError(
                        400,
                        "Se requiere exp_liqui o liquidacion_categoria_visitas_id",
                    )
                lg = self.core.get_liquidacion_por_expediente(item.exp_liqui)
                if not lg:
                    raise HttpError(404, f"Liquidación con expediente '{item.exp_liqui}' no encontrada")

                # 4. LiquidacionPorCategoriaVisitas (IO)
                lcv = self.core.get_liquidacion_categoria_visitas(lg.id)
                if not lcv:
                    raise HttpError(
                        404,
                        f"La liquidación '{item.exp_liqui}' no es de inspección de obra",
                    )
                exp_liqui = item.exp_liqui

            # 5. Validar que la IO pertenece al inspector
            li = self.core.get_liquidacion_inspector(lcv.id, inspector.id)
            if not li:
                raise HttpError(
                    400,
                    f"La liquidación '{exp_liqui}' no está asociada al inspector",
                )

            # 6. Cálculo
            importe_bruto = Decimal(str(lg.sub_total or "0"))
            programas = lcv.cantidad_visitas or 0
            if programas <= 0:
                raise HttpError(
                    400,
                    f"La liquidación '{exp_liqui}' no tiene visitas programadas",
                )

            # 7. Validar cantidad_visitas > 0
            if item.cantidad_visitas <= 0:
                raise HttpError(
                    400,
                    f"La cantidad de visitas debe ser mayor a 0 para '{exp_liqui}'",
                )

            # 8. Saldo disponible (no pagar doble) — incluye registros del periodo
            #    actual (mes__lte) para prevenir sobre-cotizar cuando ya existe un
            #    RegistroPagoInspector para ese periodo (creado por un RH previo).
            from django.db.models import Q
            from modules.finanzas.domain.models.registro_pago_inspector import (
                RegistroPagoInspector,
            )
            registros_previos = RegistroPagoInspector.objects.filter(
                liquidacion_por_categoria_visitas_id=lcv.id,
            ).filter(
                Q(periodo__lt=header_periodo)
                | Q(periodo=header_periodo, mes__lte=header_mes)
            )
            if exclude_recibo_mensual_id is not None:
                # El RH que se está editando no se descuenta de su propio saldo.
                registros_previos = registros_previos.exclude(
                    recibo_mensual_id=exclude_recibo_mensual_id,
                )
            pagadas_hasta_mes_anterior = sum(
                r.inspecciones_pagadas for r in registros_previos
            )
            saldo_disponible = programas - pagadas_hasta_mes_anterior
            if item.cantidad_visitas > saldo_disponible:
                raise HttpError(
                    400,
                    f"La cantidad de visitas ({item.cantidad_visitas}) excede el saldo "
                    f"disponible ({saldo_disponible}) para '{exp_liqui}'",
                )

            # Also validate it never exceeds the programmed amount
            if item.cantidad_visitas > programas:
                raise HttpError(
                    400,
                    f"La cantidad de visitas ({item.cantidad_visitas}) excede las "
                    f"inspecciones programadas ({programas}) para '{exp_liqui}'",
                )

            costo_por_inspeccion = (
                importe_bruto / Decimal(programas)
            ).quantize(TWO_PLACES, rounding=ROUND_HALF_UP)
            monto_contribuido = (
                costo_por_inspeccion * Decimal(item.cantidad_visitas)
            ).quantize(TWO_PLACES, rounding=ROUND_HALF_UP)

            # Get nombre_propietario from LiquidacionGeneral.proyecto
            nombre_propietario = ""
            if lg.proyecto:
                nombre_propietario = lg.proyecto.nombre_propietario or ""

            # Resolve liquidacion_especifica_numero and comprobante_activo from LiquidacionGeneral
            liquidacion_especifica_numero = _resolve_liquidacion_especifica_numero(lg)
            comprobante_activo = _resolve_comprobante_activo(lg)

            saldo_restante = saldo_disponible - item.cantidad_visitas
            # sub_total at item level = monto_contribuido (frozen per-item subtotal)
            item_sub_total = monto_contribuido
            sub_total += item_sub_total
            items.append(
                RHInspectorCotizarItemResult(
                    exp_liqui=exp_liqui,
                    liquidacion_inspector_id=str(li.id),
                    liquidacion_categoria_visitas_id=str(lcv.id),
                    nombre_propietario=nombre_propietario,
                    importe_bruto=importe_bruto,
                    inspecciones_programadas=programas,
                    inspecciones_liquidadas=item.cantidad_visitas,
                    inspecciones_pagadas_hasta_mes_anterior=pagadas_hasta_mes_anterior,
                    costo_por_inspeccion=costo_por_inspeccion,
                    monto_contribuido=monto_contribuido,
                    saldo_disponible=saldo_disponible,
                    saldo_restante=saldo_restante,
                    escala_descuento_id=str(escala.id),
                    sub_total=item_sub_total,
                    descuento=Decimal("0"),  # computed after total discount is known
                    honorarios=Decimal("0"),  # computed after total discount is known
                    # Placeholder: la tasa depende del sub total del mes.
                    tasa_descuento_aplicada=Decimal("0"),
                    periodo=item.periodo or header_periodo,
                    mes=item.mes or header_mes,
                    liquidacion_especifica_numero=liquidacion_especifica_numero,
                    comprobante_activo=comprobante_activo,
                )
            )

        # 8. Descuento sobre el TOTAL (según decisión del usuario)
        rango = self.core.get_rango_para_monto(escala, sub_total)
        tasa = Decimal(str(rango.porcentaje_descuento)) if rango else Decimal("0")
        total_descuento = (sub_total * tasa).quantize(TWO_PLACES, rounding=ROUND_HALF_UP)
        total_honorarios = (sub_total - total_descuento).quantize(TWO_PLACES, rounding=ROUND_HALF_UP)

        # 9. Compute per-item descuento and honorarios (proportional to each item's sub_total)
        # Subtraction Rule (remainder absorption): every item except the last gets the
        # proportional quantized discount; the last item absorbs the remainder by subtraction
        # so that sum(item_descuentos) == total_descuento exactly.
        running_descuento = Decimal("0")
        for i, item in enumerate(items):
            if i < len(items) - 1:
                # Not the last item: use proportional quantized discount
                if sub_total > Decimal("0"):
                    item_proporcion = item.sub_total / sub_total
                    item_descuento = (
                        total_descuento * item_proporcion
                    ).quantize(TWO_PLACES, rounding=ROUND_HALF_UP)
                else:
                    item_descuento = Decimal("0")
            else:
                # Last item: absorb remainder via strict subtraction
                item_descuento = total_descuento - running_descuento
            item_honorarios = (item.sub_total - item_descuento).quantize(
                TWO_PLACES, rounding=ROUND_HALF_UP
            )
            # Update in-place (items list was built above with placeholder values)
            item.descuento = item_descuento
            item.honorarios = item_honorarios
            item.tasa_descuento_aplicada = tasa
            running_descuento += item_descuento

        from modules.finanzas.domain.results.rh_inspector_mensual_result import (
            InspectorRHMinimalResult,
            RHInspectorVariablesCalculoResult,
            RangoDescuentoResult,
        )

        rango_aplicado_result = None
        if rango:
            rango_aplicado_result = RangoDescuentoResult(
                monto_minimo=rango.monto_minimo,
                monto_maximo=rango.monto_maximo,
                porcentaje_descuento=rango.porcentaje_descuento,
            )

        return RHInspectorCotizarResult(
            inspector=InspectorRHMinimalResult(
                id=str(inspector.id),
                nombre_completo=(
                    inspector.perfil_ingeniero.nombre_completo
                    if inspector.perfil_ingeniero
                    else ""
                ),
                cip=(
                    inspector.perfil_ingeniero.cip if inspector.perfil_ingeniero else ""
                ),
                dni=(
                    inspector.perfil_ingeniero.dni if inspector.perfil_ingeniero else None
                ),
            ),
            periodo=header_periodo,
            mes=header_mes,
            items=items,
            totales=RHInspectorTotalesResult(
                sub_total=sub_total,
                descuento=total_descuento,
                honorarios=total_honorarios,
                tasa_descuento_aplicada=tasa,
            ),
            escala_descuento_id=str(escala.id),
            variables_calculo=RHInspectorVariablesCalculoResult(
                escala_id=str(escala.id),
                escala_nombre=escala.nombre or "",
                rango_aplicado=rango_aplicado_result,
            ),
        )


class RHInspectorMensualCrearFlujo:
    """
    Crea el RH mensual del inspector con persistencia (transaction.atomic).

    Reutiliza RHInspectorMensualCotizarFlujo para validar y calcular,
    luego persiste la maestra, los detalles y actualiza el registro de pago.
    """

    @inject
    def __init__(
        self,
        core: FinanzasCoreService,
        cotizar_flujo: RHInspectorMensualCotizarFlujo,
    ):
        self.core = core
        self.cotizar_flujo = cotizar_flujo

    @transaction.atomic
    def crear(self, payload: RHInspectorCotizarIn) -> RHInspectorCotizarResult:
        """
        Cotiza, crea la maestra + detalles, y actualiza el registro de pago.

        Única operación con @transaction.atomic en este dominio.

        Args:
            payload: Datos de cotización con CIP, periodo e items.

        Returns:
            RHInspectorCotizarResult con los datos persistidos.

        Raises:
            HttpError(404/400): Cualquier error de validación propagado
                               desde cotizar_flujo.cotizar().
        """
        # 1. Calcular (reutiliza la lógica de cotizar, que valida todo)
        resultado = self.cotizar_flujo.cotizar(payload)

        # 2. Derivar inspector_operacion_id de los items seleccionados.
        #    Si todos los LiquidacionInspector tienen el mismo inspector_operacion_id, usarlo.
        #    Si hay mezcla de operaciones diferentes, raise 409 (RH debe ser por operación).
        #    Si faltan (legacy), handle null safely.
        inspector_operacion_ids: set[str | None] = set()
        for item in resultado.items:
            li = self.core.get_liquidacion_inspector_by_id(item.liquidacion_inspector_id)
            if li:
                inspector_operacion_ids.add(
                    str(li.inspector_operacion_id) if li.inspector_operacion_id else None
                )
            else:
                inspector_operacion_ids.add(None)

        # Validación: sin mezcla de operaciones distintas
        non_null_ops = {op for op in inspector_operacion_ids if op is not None}
        if len(non_null_ops) > 1:
            raise HttpError(
                409,
                f"No se puede crear un RH mensual con operaciones diferentes: {non_null_ops}. "
                "Seleccione items de la misma operación o cree RH separados por operación.",
            )

        # Extraer el valor único (o None para todo-legacy)
        inspector_operacion_id: str | None = next(iter(non_null_ops)) if non_null_ops else None

        # 3. Crear la maestra mensual (siempre crea uno nuevo, nunca reutiliza)
        # inspector_id y escala_id son UUIDs (BaseModel = UUIDModel) - se pasan como strings
        rh = self.core.crear_rh_inspector_mensual(
            inspector_id=resultado.inspector.id,
            periodo=resultado.periodo,
            mes=resultado.mes,
            escala_id=resultado.escala_descuento_id,
            sub_total=Decimal(str(resultado.totales.sub_total)),
            descuento=Decimal(str(resultado.totales.descuento)),
            honorarios=Decimal(str(resultado.totales.honorarios)),
            tasa_descuento=Decimal(str(resultado.totales.tasa_descuento_aplicada)),
            inspector_operacion_id=inspector_operacion_id,
        )

        # 4. Crear detalles (uno por liquidación) y actualizar registro de pago
        # liquidacion_categoria_visitas_id es un UUID string — se pasa directo a Django FK
        for item in resultado.items:
            detalle = self.core.crear_detalle_honorario(
                recibo_mensual_id=rh.id,
                liquidacion_categoria_visitas_id=item.liquidacion_categoria_visitas_id,
                inspecciones_liquidadas=item.inspecciones_liquidadas,
                costo_por_inspeccion=Decimal(str(item.costo_por_inspeccion)),
                monto_contribuido=Decimal(str(item.monto_contribuido)),
                escala_descuento_id=item.escala_descuento_id,
                importe_bruto=Decimal(str(item.importe_bruto)),
                inspecciones_programadas=item.inspecciones_programadas,
                inspecciones_pagadas_hasta_mes_anterior=item.inspecciones_pagadas_hasta_mes_anterior,
                saldo_restante=Decimal(str(item.saldo_restante)),
                sub_total=Decimal(str(item.sub_total)),
                descuento=Decimal(str(item.descuento)),
                honorarios=Decimal(str(item.honorarios)),
                tasa_descuento=Decimal(str(resultado.totales.tasa_descuento_aplicada)),
            )
            # Identificador estable de la fila: permite que el PATCH de
            # sincronización conserve este detalle sin recrearlo.
            item.detalle_id = str(detalle.id)
            self.core.upsert_registro_pago(
                liquidacion_categoria_visitas_id=item.liquidacion_categoria_visitas_id,
                periodo=resultado.periodo,
                mes=resultado.mes,
                inspecciones_pagadas=item.inspecciones_liquidadas,
                recibo_mensual_id=rh.id,
            )
            self.core.update_liquidacion_inspector_periodo_mes(
                liquidacion_inspector_id=item.liquidacion_inspector_id,
                periodo=item.periodo,
                mes=item.mes,
            )

        # 5. Enriquecer el resultado con inspector_operacion_id para el caller
        resultado.inspector_operacion_id = inspector_operacion_id

        return resultado


# ── RH Inspector Mensual Update (PATCH) Flujo ────────────────────────────────────


class RHInspectorMensualActualizarFlujo:
    """
    Sincroniza el conjunto final de detalles de un RH Inspector Mensual (PATCH).

    Reglas de negocio:
    - Cualquier RH del inspector es editable: no se exige que sea el más
      reciente.
    - El conjunto de items del payload es el conjunto FINAL de detalles: los
      detalles persistidos que no aparecen en el payload se retiran.
    - El conjunto final se re-cotiza COMPLETO usando la escala CONGELADA del
      recibo y excluyendo el propio RH del cálculo de saldo (el RH no se
      descuenta de su propio balance).
    - El ledger de pagos (RegistroPagoInspector) se reemplaza SOLO por las
      filas vinculadas a este RH; los registros de otros RH y los legacy con
      FK nula no se tocan.
    - Los marcadores de periodo (LiquidacionInspector.periodo / .mes) se
      recalculan desde el ledger resultante de cada IO afectada.
    - Todo el proceso ocurre dentro de un único ``transaction.atomic``.
    """

    @inject
    def __init__(
        self,
        core: FinanzasCoreService,
        cotizar_flujo: RHInspectorMensualCotizarFlujo,
    ):
        self.core = core
        self.cotizar_flujo = cotizar_flujo

    def _obtener_contexto_edicion(
        self,
        rh_id: int | str,
        payload: RHInspectorActualizarIn,
    ):
        rh = self.core.get_rh_inspector_mensual_by_id(rh_id)
        if not rh:
            raise HttpError(
                404,
                f"Recibo de honorario mensual de inspector con id '{rh_id}' no encontrado",
            )

        perfil = getattr(rh.inspector, "perfil_ingeniero", None)
        if not perfil or not payload.cip or payload.cip != perfil.cip:
            raise HttpError(
                409,
                "El recibo de honorario mensual no corresponde al inspector indicado (cip).",
            )
        # Cualquier RH del inspector es editable: no se exige que sea el más
        # reciente. El periodo/mes de la cabecera también es editable, igual
        # que en la creación.

        detalles_existentes = list(rh.detalles.all())
        por_id = {str(detalle.id): detalle for detalle in detalles_existentes}
        return rh, detalles_existentes, por_id

    def _cotizar_actualizacion(
        self,
        rh,
        payload: RHInspectorActualizarIn,
        por_id: dict[str, Any],
    ) -> RHInspectorCotizarResult:
        if not payload.items:
            raise HttpError(400, "La selección de liquidaciones no puede estar vacía.")

        detalle_ids = [item.detalle_id for item in payload.items if item.detalle_id]
        if len(set(detalle_ids)) != len(detalle_ids):
            raise HttpError(400, "La selección contiene detalles duplicados.")

        items_cotizacion: list[RHInspectorCotizarItemIn] = []
        seleccion: list[str] = []
        for item in payload.items:
            if (
                item.fecha_revision is not None
                and item.fecha_presentacion is not None
                and item.fecha_revision > item.fecha_presentacion
            ):
                raise HttpError(
                    422,
                    "Rango de fechas invertido: la fecha de revisión no puede ser "
                    "posterior a la fecha de presentación.",
                )

            liquidacion_categoria_visitas_id = item.liquidacion_categoria_visitas_id
            if item.detalle_id:
                detalle = por_id.get(str(item.detalle_id))
                if detalle is None:
                    raise HttpError(
                        400,
                        f"El detalle '{item.detalle_id}' no pertenece al recibo '{rh.id}'.",
                    )
                persisted_id = str(detalle.liquidacion_por_categoria_visitas_id)
                if (
                    liquidacion_categoria_visitas_id
                    and str(liquidacion_categoria_visitas_id) != persisted_id
                ):
                    raise HttpError(
                        400,
                        "La liquidación del detalle no coincide con la selección.",
                    )
                liquidacion_categoria_visitas_id = persisted_id

            selection_key = liquidacion_categoria_visitas_id or item.exp_liqui
            if not selection_key:
                raise HttpError(
                    400,
                    "Se requiere exp_liqui o liquidacion_categoria_visitas_id.",
                )
            seleccion.append(str(selection_key))
            items_cotizacion.append(
                RHInspectorCotizarItemIn(
                    exp_liqui=(
                        None if liquidacion_categoria_visitas_id else item.exp_liqui
                    ),
                    liquidacion_categoria_visitas_id=liquidacion_categoria_visitas_id,
                    cantidad_visitas=item.cantidad_visitas,
                    periodo=item.periodo,
                    mes=item.mes,
                )
            )

        if len(set(seleccion)) != len(seleccion):
            raise HttpError(400, "La selección contiene liquidaciones duplicadas.")

        return self.cotizar_flujo.cotizar(
            RHInspectorCotizarIn(
                cip=payload.cip,
                periodo=payload.periodo,
                mes=payload.mes,
                items=items_cotizacion,
            ),
            exclude_recibo_mensual_id=rh.id,
            escala_override=rh.escala_descuento,
        )

    def cotizar_actualizacion(
        self,
        rh_id: int | str,
        payload: RHInspectorActualizarIn,
    ) -> RHInspectorCotizarResult:
        """Cotiza una edición sin persistir ni descontar el propio RH."""
        rh, _, por_id = self._obtener_contexto_edicion(rh_id, payload)
        return self._cotizar_actualizacion(rh, payload, por_id)

    @transaction.atomic
    def actualizar(
        self,
        rh_id: int | str,
        payload: RHInspectorActualizarIn,
    ) -> RHInspectorCotizarResult:
        """
        Aplica el conjunto final de liquidaciones sobre un RH de inspector.

        Args:
            rh_id: PK del ReciboHonorarioInspectorMensual a sincronizar.
            payload: Conjunto final de items (agregar / conservar / retirar).

        Returns:
            RHInspectorCotizarResult con el estado final del recibo.

        Raises:
            HttpError(404): El RH no existe.
            HttpError(400): Selección malformada (detalle ajeno, duplicados, etc.).
            HttpError(422): Rango de fechas invertido en un item.
            HttpError(409): Conflicto (otro inspector u operaciones de
                            inspector mezcladas).
        """
        rh, detalles_existentes, por_id = self._obtener_contexto_edicion(
            rh_id, payload
        )
        resultado = self._cotizar_actualizacion(rh, payload, por_id)
        if len(resultado.items) != len(payload.items):
            raise HttpError(
                400,
                "La selección de liquidaciones no pudo ser cotizada.",
            )

        # 6. Operaciones de inspector mezcladas — 409 (misma regla que la creación)
        inspector_operacion_ids: set[str] = set()
        for item in resultado.items:
            li = self.core.get_liquidacion_inspector_by_id(item.liquidacion_inspector_id)
            if li and li.inspector_operacion_id:
                inspector_operacion_ids.add(str(li.inspector_operacion_id))
        if len(inspector_operacion_ids) > 1:
            raise HttpError(
                409,
                "No se puede actualizar un RH mensual con operaciones diferentes: "
                f"{sorted(inspector_operacion_ids)}. "
                "Seleccione items de la misma operación.",
            )
        inspector_operacion_id = (
            next(iter(inspector_operacion_ids)) if inspector_operacion_ids else None
        )

        # 7. Reconciliación de detalles
        ids_retenidos: set[str] = set()

        for item_in, item_cotizado in zip(payload.items, resultado.items):
            if item_in.detalle_id:
                # ── CONSERVAR fila existente ──────────────────────────────────
                detalle = por_id.get(str(item_in.detalle_id))
                if detalle is None:
                    raise HttpError(
                        400,
                        f"El detalle '{item_in.detalle_id}' no pertenece al recibo '{rh.id}'.",
                    )
                if str(detalle.liquidacion_por_categoria_visitas_id) != str(
                    item_cotizado.liquidacion_categoria_visitas_id
                ):
                    raise HttpError(
                        400,
                        "La liquidación del detalle no coincide con la selección.",
                    )
                detalle = self.core.actualizar_detalle_honorario_inspector(
                    detalle.id,
                    inspecciones_liquidadas=item_cotizado.inspecciones_liquidadas,
                    costo_por_inspeccion=Decimal(str(item_cotizado.costo_por_inspeccion)),
                    monto_contribuido=Decimal(str(item_cotizado.monto_contribuido)),
                    escala_descuento_id=item_cotizado.escala_descuento_id,
                    importe_bruto=Decimal(str(item_cotizado.importe_bruto)),
                    inspecciones_programadas=item_cotizado.inspecciones_programadas,
                    inspecciones_pagadas_hasta_mes_anterior=(
                        item_cotizado.inspecciones_pagadas_hasta_mes_anterior
                    ),
                    saldo_restante=Decimal(str(item_cotizado.saldo_restante)),
                    sub_total=Decimal(str(item_cotizado.sub_total)),
                    descuento=Decimal(str(item_cotizado.descuento)),
                    honorarios=Decimal(str(item_cotizado.honorarios)),
                    tasa_descuento=Decimal(
                        str(resultado.totales.tasa_descuento_aplicada)
                    ),
                )
                ids_retenidos.add(str(detalle.id))
            else:
                # ── AGREGAR fila nueva ────────────────────────────────────────
                detalle = self.core.crear_detalle_honorario(
                    recibo_mensual_id=rh.id,
                    liquidacion_categoria_visitas_id=item_cotizado.liquidacion_categoria_visitas_id,
                    inspecciones_liquidadas=item_cotizado.inspecciones_liquidadas,
                    costo_por_inspeccion=Decimal(str(item_cotizado.costo_por_inspeccion)),
                    monto_contribuido=Decimal(str(item_cotizado.monto_contribuido)),
                    escala_descuento_id=item_cotizado.escala_descuento_id,
                    importe_bruto=Decimal(str(item_cotizado.importe_bruto)),
                    inspecciones_programadas=item_cotizado.inspecciones_programadas,
                    inspecciones_pagadas_hasta_mes_anterior=(
                        item_cotizado.inspecciones_pagadas_hasta_mes_anterior
                    ),
                    saldo_restante=Decimal(str(item_cotizado.saldo_restante)),
                    sub_total=Decimal(str(item_cotizado.sub_total)),
                    descuento=Decimal(str(item_cotizado.descuento)),
                    honorarios=Decimal(str(item_cotizado.honorarios)),
                    tasa_descuento=Decimal(
                        str(resultado.totales.tasa_descuento_aplicada)
                    ),
                )
            item_cotizado.detalle_id = str(detalle.id)

        # 8. RETIRAR filas que no están en el conjunto final
        lcv_afectadas: set[str] = set()
        for detalle in detalles_existentes:
            lcv_afectadas.add(str(detalle.liquidacion_por_categoria_visitas_id))
            if str(detalle.id) in ids_retenidos:
                continue
            self.core.delete_detalle_honorario_inspector(detalle.id)

        # 9. Ledger: se reemplazan SOLO las filas de este RH
        lcv_afectadas.update(
            str(item.liquidacion_categoria_visitas_id) for item in resultado.items
        )
        self.core.delete_registros_pago_por_recibo_mensual(rh.id)
        for item in resultado.items:
            self.core.upsert_registro_pago(
                liquidacion_categoria_visitas_id=item.liquidacion_categoria_visitas_id,
                periodo=payload.periodo,
                mes=payload.mes,
                inspecciones_pagadas=item.inspecciones_liquidadas,
                recibo_mensual_id=rh.id,
            )

        # 9b. Cabecera del recibo: el periodo/mes es editable en el mismo flujo
        # que la creación, así que se persiste junto con el conjunto final.
        self.core.actualizar_periodo_rh_inspector_mensual(
            rh.id,
            periodo=payload.periodo,
            mes=payload.mes,
        )

        # 10. Marcadores de periodo: primero se recalculan desde el ledger
        #     resultante y luego se aplica el periodo/mes por fila, igual que
        #     en el flujo de creación (editar es el mismo flujo que crear).
        self.core.recalcular_marcadores_periodo_inspector(lcv_afectadas)
        for item in resultado.items:
            self.core.update_liquidacion_inspector_periodo_mes(
                liquidacion_inspector_id=item.liquidacion_inspector_id,
                periodo=item.periodo,
                mes=item.mes,
            )

        # 11. Totales del recibo = suma del conjunto final
        self.core.actualizar_totales_rh_inspector_mensual(
            rh.id,
            sub_total=Decimal(str(resultado.totales.sub_total)),
            descuento=Decimal(str(resultado.totales.descuento)),
            honorarios=Decimal(str(resultado.totales.honorarios)),
            tasa_descuento=Decimal(str(resultado.totales.tasa_descuento_aplicada)),
        )

        # 12. Backfill de la operatividad del inspector (solo si estaba vacía)
        if rh.inspector_operacion_id is None and inspector_operacion_id:
            self.core.actualizar_inspector_operacion_rh(
                rh.id,
                inspector_operacion_id,
            )

        resultado.inspector_operacion_id = inspector_operacion_id or (
            str(rh.inspector_operacion_id) if rh.inspector_operacion_id else None
        )

        return resultado


# ── RH Inspector Mensual List Flujo ─────────────────────────────────────────────


class RHInspectorMensualListFlujo:
    """
    Listado paginado de RecibosHonorariosInspectorMensuales y candidatos.

    Delega al FinanzasCoreService para queries ORM y construye resultados
    tipados (RHInspectorMensualListItemResult) para consumo por controllers.
    """

    @inject
    def __init__(self, core: FinanzasCoreService):
        self.core = core

    def listar_rh_mensuales_inspectores_proceso(
        self,
        page: int = 1,
        page_size: int = 10,
        inspector_id: int | None = None,
        inspector_cip: str | None = None,
        periodo: int | None = None,
        mes: int | None = None,
        sin_paginacion: bool = False,
    ) -> tuple[list, int]:
        """
        Lista RecibosHonorariosInspectorMensuales con paginación.

        Args:
            page: Número de página (1-indexed).
            page_size: Elementos por página.
            inspector_id: Filter by inspector_id (already int, not UUID here).
            inspector_cip: Filter by CIP del inspector.
            periodo: Filter por año del periodo.
            mes: Filter por mes (1-12).
            sin_paginacion: Devuelve el conjunto completo filtrado en una sola
                respuesta (sin paginación).

        Returns:
            Tuple (list of RHInspectorMensualListItemResult, total count).
        """
        from modules.finanzas.domain.results.rh_inspector_mensual_result import (
            RHInspectorMensualListItemResult,
        )

        page = max(1, page)
        page_size = max(1, min(page_size, 100))

        ORM_objects, total = self.core.list_rh_mensuales_inspectores_paginated(
            page=page,
            page_size=page_size,
            inspector_id=inspector_id,
            inspector_cip=inspector_cip,
            periodo=periodo,
            mes=mes,
        )

        results: list[RHInspectorMensualListItemResult] = [
            self._build_rh_mensual_inspector_result(r) for r in ORM_objects
        ]
        return results, total

    def _build_rh_mensual_inspector_result(self, recibo_mensual) -> "RHInspectorMensualListItemResult":
        """
        Build RHInspectorMensualListItemResult from ORM object.

        Maps: id, periodo, fecha_registro, inspector, totales, detalles, variables_calculo.
        Los detalles incluyen expediente, nombre_propietario, importe_bruto,
        inspecciones_programadas, inspecciones_liquidadas, inspecciones_pagadas_hasta_mes_anterior,
        costo_por_inspeccion, monto_contribuido, saldo_restante.
        """
        from modules.finanzas.domain.results.rh_inspector_mensual_result import (
            InspectorRHMinimalResult,
            RHInspectorMensualTotalesResult,
            RHInspectorMensualDetalleResult,
            RHInspectorVariablesCalculoResult,
            RangoDescuentoResult,
            RHInspectorMensualListItemResult,
        )
        from modules.finanzas.domain.services.flujos.rh_delegado_mensual_flujo import (
            _resolve_liquidacion_especifica_numero,
            _resolve_comprobante_activo,
        )

        inspector_perfil = recibo_mensual.inspector.perfil_ingeniero

        # Leer tasa de descuento directamente del campo congelado
        tasa_descuento = (
            Decimal(str(recibo_mensual.tasa_descuento))
            if recibo_mensual.tasa_descuento is not None
            else Decimal("0.0000")
        )

        detalles: list[RHInspectorMensualDetalleResult] = []
        total_inspecciones_programadas = 0
        total_inspecciones_liquidadas = 0
        total_inspecciones_pagadas_anterior = 0
        total_saldo_restante = 0

        for d in recibo_mensual.detalles.select_related(
            "liquidacion_por_categoria_visitas__liquidacion_general__proyecto__distrito"
        ).prefetch_related(
            "liquidacion_por_categoria_visitas__inspectores",
            "liquidacion_por_categoria_visitas__liquidacion_general__comprobantes",
        ):
            lcv = d.liquidacion_por_categoria_visitas
            lg = lcv.liquidacion_general

            # Pre-compute active comprobantes from prefetched queryset (avoids extra DB query)
            lg.comprobantes_activos = [
                c for c in lg.comprobantes.all() if c.activo
            ]

            # Read frozen fields directly from DetalleHonorarioInspector (no on-the-fly calculation)
            importe_bruto = d.importe_bruto if d.importe_bruto is not None else Decimal("0")
            inspecciones_programadas = d.inspecciones_programadas if d.inspecciones_programadas is not None else 0
            inspecciones_pagadas_hasta_mes_anterior = d.inspecciones_pagadas_hasta_mes_anterior if d.inspecciones_pagadas_hasta_mes_anterior is not None else 0
            saldo_restante = int(d.saldo_restante) if d.saldo_restante is not None else 0

            total_inspecciones_programadas += inspecciones_programadas
            total_inspecciones_liquidadas += d.inspecciones_liquidadas
            total_inspecciones_pagadas_anterior += inspecciones_pagadas_hasta_mes_anterior
            total_saldo_restante += saldo_restante

            nombre_propietario = ""
            if lg.proyecto:
                nombre_propietario = lg.proyecto.nombre_propietario or ""

            expediente = lg.expediente or ""

            distrito = None
            if lg.proyecto and lg.proyecto.distrito:
                distrito = lg.proyecto.distrito.nombre or None

            # Extract dates from LiquidacionInspector through table
            # Find the inspector matching recibo_mensual.inspector_id
            liquidacion_inspector = None
            for li in lcv.inspectores.all():
                if str(li.inspector_id) == str(recibo_mensual.inspector_id):
                    liquidacion_inspector = li
                    break

            fecha_revision = None
            fecha_presentacion = None
            dictamen_revision = None
            if liquidacion_inspector:
                if liquidacion_inspector.fecha_revision:
                    fecha_revision = str(liquidacion_inspector.fecha_revision.isoformat())
                if liquidacion_inspector.fecha_presentacion:
                    fecha_presentacion = str(liquidacion_inspector.fecha_presentacion.isoformat())
                dictamen_revision = liquidacion_inspector.dictamen_revision or None

            detalles.append(
                RHInspectorMensualDetalleResult(
                    detalle_id=str(d.id),
                    expediente=expediente,
                    nombre_propietario=nombre_propietario,
                    distrito=distrito,
                    importe_bruto=importe_bruto,
                    inspecciones_programadas=inspecciones_programadas,
                    inspecciones_liquidadas=d.inspecciones_liquidadas,
                    inspecciones_pagadas_hasta_mes_anterior=inspecciones_pagadas_hasta_mes_anterior,
                    costo_por_inspeccion=d.costo_por_inspeccion,
                    monto_contribuido=d.monto_contribuido,
                    saldo_restante=saldo_restante,
                    sub_total=d.sub_total,
                    descuento=d.descuento,
                    honorarios=d.honorarios,
                    liquidacion_especifica_numero=_resolve_liquidacion_especifica_numero(lg),
                    numero_revision=(
                        lg.numero_revision if hasattr(lg, "numero_revision") else None
                    ),
                    comprobante_activo=_resolve_comprobante_activo(lg),
                    fecha_revision=fecha_revision,
                    fecha_presentacion=fecha_presentacion,
                    dictamen_revision=dictamen_revision,
                )
            )

        # Build variables_calculo from escala_descuento relationship.
        # rango_aplicado is found by matching tasa_descuento against rango.porcentaje_descuento.
        escala = recibo_mensual.escala_descuento
        rangos_qs = escala.rangos.all()
        rango_aplicado = None
        for r in rangos_qs:
            if r.porcentaje_descuento == tasa_descuento:
                rango_aplicado = RangoDescuentoResult(
                    monto_minimo=r.monto_minimo,
                    monto_maximo=r.monto_maximo,
                    porcentaje_descuento=r.porcentaje_descuento,
                )
                break
        if rango_aplicado is None:
            # Fallback: use first rango if no exact match (should not happen with correct data)
            first = rangos_qs.first()
            rango_aplicado = RangoDescuentoResult(
                monto_minimo=first.monto_minimo if first else Decimal("0"),
                monto_maximo=first.monto_maximo if first else None,
                porcentaje_descuento=tasa_descuento,
            )
        variables_calculo = RHInspectorVariablesCalculoResult(
            escala_id=str(escala.id),
            escala_nombre=escala.nombre or "",
            rango_aplicado=rango_aplicado,
        )

        # Resolve periodo_year/mes — prefer stored ints, fallback to parsing periodo string
        periodo_year = recibo_mensual.periodo
        mes = recibo_mensual.mes
        if periodo_year is None or mes is None:
            from modules.finanzas.domain.services.finanzas_core_service import FinanzasCoreService
            cs = FinanzasCoreService()
            if periodo_year is None:
                periodo_year = cs._parse_periodo_year(recibo_mensual.periodo)
            if mes is None:
                mes = cs._parse_periodo_mes(recibo_mensual.periodo)

        return RHInspectorMensualListItemResult(
            id=str(recibo_mensual.id),
            numero=recibo_mensual.numero,
            periodo=periodo_year,
            mes=mes,
            fecha_registro=recibo_mensual.fecha_registro.isoformat() if recibo_mensual.fecha_registro else "",
            inspector=InspectorRHMinimalResult(
                id=str(recibo_mensual.inspector.id),
                nombre_completo=inspector_perfil.nombre_completo,
                cip=inspector_perfil.cip or "",
                dni=inspector_perfil.dni,
            ),
            totales=RHInspectorMensualTotalesResult(
                inspecciones_programadas=total_inspecciones_programadas,
                inspecciones_liquidadas=total_inspecciones_liquidadas,
                inspecciones_pagadas_hasta_mes_anterior=total_inspecciones_pagadas_anterior,
                saldo_restante=total_saldo_restante,
                sub_total=recibo_mensual.sub_total,
                descuento=recibo_mensual.descuento,
                honorarios=recibo_mensual.honorarios,
                tasa_descuento_aplicada=tasa_descuento,
            ),
            detalles=detalles,
            variables_calculo=variables_calculo,
        )

    def list_candidatos_inspector_proceso(
        self,
        cip: str,
        periodo: str | None = None,
        fecha_inicio: str | None = None,
        fecha_fin: str | None = None,
    ):
        """
        Lista las IOs candidatas (con saldo disponible) para el RH mensual del inspector.

        Args:
            cip: CIP del inspector.
            periodo: Optional periodo en formato YYYY-MM.
                Si se proporciona, calcula inspecciones pagadas acumuladas de todos
                los periodos STRICTLY anteriores a este. Si es None, suma todos
                los periodos históricamente.
            fecha_inicio: Optional filter — fecha_registro >= fecha_inicio (inclusive).
            fecha_fin: Optional filter — fecha_registro <= fecha_fin (inclusive).

        Returns:
            InspectorCandidatosResult con la lista de candidatas.

        Raises:
            HttpError(404): Inspector con CIP no encontrado.
        """
        from modules.finanzas.domain.results.rh_inspector_candidatos_result import (
            InspectorCandidatosResult,
            InspectorCandidataItemResult,
        )

        inspector = self.core.get_inspector_by_cip(cip)
        if not inspector:
            raise HttpError(404, f"Inspector con CIP '{cip}' no encontrado")

        # Parse periodo string YYYY-MM into (periodo_int, mes_int) for core service
        periodo_int: int | None = None
        mes_int: int | None = None
        if periodo:
            parts = periodo.split("-")
            if len(parts) >= 2:
                try:
                    periodo_int = int(parts[0])
                    mes_int = int(parts[1])
                except ValueError:
                    pass  # Keep None values if parsing fails

        candidatos_data = self.core.list_liquidaciones_inspector_candidatas(
            inspector_id=int(inspector.id),
            periodo=periodo_int,
            mes=mes_int,
            fecha_inicio=fecha_inicio,
            fecha_fin=fecha_fin,
        )
        _enriquecer_candidatas_inspector(candidatos_data)

        perfil = inspector.perfil_ingeniero
        candidatos = [
            InspectorCandidataItemResult(**data) for data in candidatos_data
        ]

        return InspectorCandidatosResult(
            inspector_id=str(inspector.id),
            inspector_nombre=perfil.nombre_completo if perfil else "",
            inspector_cip=perfil.cip if perfil else "",
            inspector_dni=perfil.dni if perfil else None,
            periodo=periodo or "",
            candidatos=candidatos,
            total=len(candidatos),
        )

    def list_candidatos_inspector_proceso_paginated(
        self,
        cip: str,
        page: int,
        page_size: int,
        expediente: str | None = None,
        numero: int | None = None,
        propietario: str | None = None,
        direccion: str | None = None,
        periodo: str | None = None,
        fecha_inicio: str | None = None,
        fecha_fin: str | None = None,
    ):
        """
        Lista las IOs candidatas (con saldo disponible) para el RH mensual del inspector
        con paginación y filtros adicionales.

        Args:
            cip: CIP del inspector.
            page: Número de página (1-indexed).
            page_size: Elementos por página (max 100).
            expediente: Filtro opcional — expediente icontains.
            numero: Filtro opcional — numero de liquidacion IO exact match.
            propietario: Filtro opcional — nombre_propietario icontains.
            direccion: Filtro opcional — direccion icontains.
            periodo: Optional periodo en formato YYYY-MM.
            fecha_inicio: Optional filter — fecha_registro >= fecha_inicio (inclusive).
            fecha_fin: Optional filter — fecha_registro <= fecha_fin (inclusive).

        Returns:
            InspectorCandidatosPaginatedResult con la lista de candidatas paginada.

        Raises:
            HttpError(404): Inspector con CIP no encontrado.
        """
        import math
        from modules.finanzas.domain.results.rh_inspector_candidatos_result import (
            InspectorCandidatosPaginatedResult,
            InspectorCandidataItemResult,
        )

        inspector = self.core.get_inspector_by_cip(cip)
        if not inspector:
            raise HttpError(404, f"Inspector con CIP '{cip}' no encontrado")

        # Normalize pagination params
        page = max(1, page)
        page_size = max(1, min(page_size, 100))

        # Parse periodo string YYYY-MM into (periodo_int, mes_int) for core service
        periodo_int: int | None = None
        mes_int: int | None = None
        if periodo:
            parts = periodo.split("-")
            if len(parts) >= 2:
                try:
                    periodo_int = int(parts[0])
                    mes_int = int(parts[1])
                except ValueError:
                    pass

        candidatos_data, total = self.core.list_liquidaciones_inspector_candidatas_paginated(
            inspector_id=int(inspector.id),
            page=page,
            page_size=page_size,
            expediente=expediente,
            numero=numero,
            propietario=propietario,
            direccion=direccion,
            periodo=periodo_int,
            mes=mes_int,
            fecha_inicio=fecha_inicio,
            fecha_fin=fecha_fin,
        )
        _enriquecer_candidatas_inspector(candidatos_data)

        perfil = inspector.perfil_ingeniero
        items = [
            InspectorCandidataItemResult(**data) for data in candidatos_data
        ]

        total_pages = math.ceil(total / page_size) if page_size > 0 else 0

        return InspectorCandidatosPaginatedResult(
            inspector_id=str(inspector.id),
            inspector_nombre=perfil.nombre_completo if perfil else "",
            inspector_cip=perfil.cip if perfil else "",
            inspector_dni=perfil.dni if perfil else None,
            periodo=periodo or "",
            items=items,
            total=total,
            page=page,
            page_size=page_size,
            total_pages=total_pages,
        )


# ── RH Inspector Mensual Delete Flujo ───────────────────────────────────────────


class RHInspectorMensualDeleteFlujo:
    """
    Elimina un ReciboHonorarioInspectorMensual de forma segura.

    Reglas de negocio:
    - Solo se puede eliminar el ÚLTIMO RH del inspector (por fecha_registro DESC).
      Si no es el último, levanta HttpError 409.
    - Los RegistroPagoInspector con recibo_mensual_id == rh.id son eliminados
      (revierte el efecto de pago acumulado).
    - Los marcadores de periodo (LiquidacionInspector.periodo / .mes) se
      recalculan desde el ledger restante de cada IO afectada.
    - Los DetalleHonorarioInspector se eliminan en CASCADE por Django.
    - Los RegistroPagoInspector legacy con recibo_mensual=null NO son tocados.
    - LiquidacionInspector NO es eliminada (el saldo se recalcula dinámicamente
      a partir de RegistroPagoInspector); solo se recalcula su marcador.
    """

    @inject
    def __init__(self, core: FinanzasCoreService):
        self.core = core

    @transaction.atomic
    def eliminar(self, rh_id: int | str) -> None:
        """
        Elimina un RH de inspector y revierte los RegistroPagoInspector asociados.

        Args:
            rh_id: PK del ReciboHonorarioInspectorMensual a eliminar.

        Raises:
            HttpError(404): RH no encontrado.
            HttpError(409): RH no es el último para ese inspector.
        """
        # 1. Obtener RH — 404 si no existe
        rh = self.core.get_rh_inspector_mensual_by_id(rh_id)
        if not rh:
            raise HttpError(404, f"Recibo de honorario mensual de inspector con id '{rh_id}' no encontrado")

        # 2. Obtener el último RH del inspector — 409 si no es el último
        latest_rh = self.core.get_latest_rh_inspector_for_inspector(rh.inspector_id)
        if latest_rh is None or str(latest_rh.id) != str(rh.id):
            raise HttpError(
                409,
                "Solo se puede eliminar el último recibo de honorario mensual del inspector. "
                f"El recibo con id '{rh_id}' no es el más reciente.",
            )

        # 3. Recolectar las IO afectadas (antes de eliminar: el CASCADE borra
        #    los DetalleHonorarioInspector).
        lcv_ids = list(
            rh.detalles.values_list("liquidacion_por_categoria_visitas_id", flat=True)
        )

        # 4. Eliminar RegistroPagoInspector vinculados (reversión de pago).
        #    Solo los que tienen recibo_mensual_id == rh.id — los null-FK quedan intactos.
        registros_pago = self.core.get_registros_pago_by_recibo_mensual(rh_id)
        for registro in registros_pago:
            self.core.delete_registro_pago_inspector(registro.id)

        # 5. Recalcular los marcadores de periodo afectados desde el ledger restante.
        self.core.recalcular_marcadores_periodo_inspector(lcv_ids)

        # 6. Eliminar el RH padre — CASCADE elimina DetalleHonorarioInspector
        self.core.delete_rh_inspector_mensual(rh_id)
