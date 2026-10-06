"""
RH Inspector Mensual Flujos — cotización y creación del RH mensual del inspector.

- RHInspectorMensualCotizarFlujo: cálculo puro, sin escritura a BD.
- RHInspectorMensualCrearFlujo: persiste con @transaction.atomic.

Único lugar con @transaction.atomic para la creación (contrato 4).
"""
from decimal import Decimal, ROUND_HALF_UP

from django.db import transaction
from injector import inject
from ninja.errors import HttpError

from modules.finanzas.domain.services.finanzas_core_service import FinanzasCoreService
from modules.finanzas.domain.schemas import RHInspectorCotizarIn
from modules.finanzas.domain.results.rh_inspector_mensual_result import (
    RHInspectorCotizarItemResult,
    RHInspectorTotalesResult,
    RHInspectorCotizarResult,
)
from modules.finanzas.domain.services.flujos.rh_delegado_mensual_flujo import (
    _resolve_liquidacion_especifica_numero,
    _resolve_comprobante_activo,
)

TWO_PLACES = Decimal("0.01")


class RHInspectorMensualCotizarFlujo:
    """
    Cálculo del RH mensual del inspector SIN persistencia (cotización).

    Solo consultas a través del core. No escribe en la base de datos.
    """

    @inject
    def __init__(self, core: FinanzasCoreService):
        self.core = core

    def cotizar(self, payload: RHInspectorCotizarIn) -> RHInspectorCotizarResult:
        """
        Valida y calcula el RH mensual sin guardar nada.

        Args:
            payload: Datos de cotización con CIP, periodo e items.

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

        # 2. Escala vigente
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
                exp_liqui = lg.expediente or ""
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
                    descuento=Decimal("0"),  # computed after total descuento is known
                    honorarios=Decimal("0"),  # computed after total descuento is known
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
                    inspector.perfil_ingeniero.dni if inspector.perfil_ingeniero else ""
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
            self.core.crear_detalle_honorario(
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
            self.core.upsert_registro_pago(
                liquidacion_categoria_visitas_id=item.liquidacion_categoria_visitas_id,
                periodo=resultado.periodo,
                mes=resultado.mes,
                inspecciones_pagadas=item.inspecciones_liquidadas,
            )
            self.core.update_liquidacion_inspector_periodo_mes(
                liquidacion_inspector_id=item.liquidacion_inspector_id,
                periodo=item.periodo,
                mes=item.mes,
            )

        # 5. Enriquecer el resultado con inspector_operacion_id para el caller
        resultado.inspector_operacion_id = inspector_operacion_id

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
    ) -> tuple[list, int]:
        """
        Lista RecibosHonorariosInspectorMensuales con paginación.

        Args:
            page: Número de página (1-indexed).
            page_size: Elementos por página.
            inspector_id: Filter by inspector_id (already int, not UUID here).

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
                dni=inspector_perfil.dni or "",
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

        perfil = inspector.perfil_ingeniero
        candidatos = [
            InspectorCandidataItemResult(**data) for data in candidatos_data
        ]

        return InspectorCandidatosResult(
            inspector_id=str(inspector.id),
            inspector_nombre=perfil.nombre_completo if perfil else "",
            inspector_cip=perfil.cip if perfil else "",
            inspector_dni=perfil.dni if perfil else "",
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

        perfil = inspector.perfil_ingeniero
        items = [
            InspectorCandidataItemResult(**data) for data in candidatos_data
        ]

        total_pages = math.ceil(total / page_size) if page_size > 0 else 0

        return InspectorCandidatosPaginatedResult(
            inspector_id=str(inspector.id),
            inspector_nombre=perfil.nombre_completo if perfil else "",
            inspector_cip=perfil.cip if perfil else "",
            inspector_dni=perfil.dni if perfil else "",
            periodo=periodo or "",
            items=items,
            total=total,
            page=page,
            page_size=page_size,
            total_pages=total_pages,
        )
