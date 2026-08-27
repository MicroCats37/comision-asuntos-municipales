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

        for item in payload.items:
            # 3a. Resolver liquidacion_categoria_visitas_id
            # Soporta dos flujos de entrada: por exp_liqui (manual) o por liquidacion_categoria_visitas_id (candidatas)
            if item.liquidacion_categoria_visitas_id:
                # Flujo por candidatas: usar directamente el ID de la IO
                lcv = self.core.get_liquidacion_categoria_visitas_by_id(item.liquidacion_categoria_visitas_id)
                if not lcv:
                    raise HttpError(
                        404,
                        f"Liquidación por categoría de visitas '{item.liquidacion_categoria_visitas_id}' no encontrada",
                    )
                lg = self.core.get_liquidacion_general_by_id(lcv.liquidacion_general_id)
                if not lg:
                    raise HttpError(
                        404,
                        f"Liquidación general para IO '{item.liquidacion_categoria_visitas_id}' no encontrada",
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

            # 8. Saldo disponible (no pagar doble) — acumula todos los periodos
            #    hasta el periodo solicitado (periodo__lte) para no pagar doble.
            #    Usa periodo__lte para que si ya existe un RH para el mismo periodo,
            #    su RegistroPagoInspector se considere y no se exceda el saldo.
            from modules.finanzas.domain.models.registro_pago_inspector import (
                RegistroPagoInspector,
            )
            registros_previos = RegistroPagoInspector.objects.filter(
                liquidacion_por_categoria_visitas_id=lcv.id,
                periodo__lte=payload.periodo,
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

            saldo_restante = saldo_disponible - item.cantidad_visitas
            sub_total += monto_contribuido
            items.append(
                RHInspectorCotizarItemResult(
                    exp_liqui=exp_liqui,
                    liquidacion_inspector_id=str(li.id),
                    liquidacion_categoria_visitas_id=str(lcv.id),
                    nombre_propietario=nombre_propietario,
                    importe_bruto=float(importe_bruto),
                    inspecciones_programadas=programas,
                    inspecciones_liquidadas=item.cantidad_visitas,
                    inspecciones_pagadas_hasta_mes_anterior=pagadas_hasta_mes_anterior,
                    costo_por_inspeccion=float(costo_por_inspeccion),
                    monto_contribuido=float(monto_contribuido),
                    saldo_disponible=saldo_disponible,
                    saldo_restante=saldo_restante,
                )
            )

        # 8. Descuento sobre el TOTAL (según decisión del usuario)
        rango = self.core.get_rango_para_monto(escala, sub_total)
        tasa = Decimal(str(rango.porcentaje_descuento)) if rango else Decimal("0")
        descuento = (sub_total * tasa).quantize(TWO_PLACES, rounding=ROUND_HALF_UP)
        honorarios = (sub_total - descuento).quantize(TWO_PLACES, rounding=ROUND_HALF_UP)

        from modules.finanzas.domain.results.rh_inspector_mensual_result import InspectorRHMinimalResult

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
            periodo=payload.periodo,
            items=items,
            totales=RHInspectorTotalesResult(
                sub_total=float(sub_total),
                descuento=float(descuento),
                honorarios=float(honorarios),
                tasa_descuento_aplicada=float(tasa),
            ),
            escala_descuento_id=str(escala.id),
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

        # 2. Crear/obtener la maestra mensual (idempotente por inspector+periodo)
        # inspector_id y escala_id son UUIDs (BaseModel = UUIDModel) - se pasan como strings
        rh, _ = self.core.crear_rh_inspector_mensual(
            inspector_id=resultado.inspector.id,
            periodo=resultado.periodo,
            escala_id=resultado.escala_descuento_id,
            sub_total=Decimal(str(resultado.totales.sub_total)),
            descuento=Decimal(str(resultado.totales.descuento)),
            honorarios=Decimal(str(resultado.totales.honorarios)),
        )

        # 3. Crear detalles (uno por liquidación) y actualizar registro de pago
        # liquidacion_categoria_visitas_id es un UUID string — se pasa directo a Django FK
        for item in resultado.items:
            self.core.crear_detalle_honorario(
                recibo_mensual_id=rh.id,
                liquidacion_categoria_visitas_id=item.liquidacion_categoria_visitas_id,
                inspecciones_liquidadas=item.inspecciones_liquidadas,
                costo_por_inspeccion=Decimal(str(item.costo_por_inspeccion)),
                monto_contribuido=Decimal(str(item.monto_contribuido)),
            )
            self.core.upsert_registro_pago(
                liquidacion_categoria_visitas_id=item.liquidacion_categoria_visitas_id,
                periodo=resultado.periodo,
                inspecciones_pagadas=item.inspecciones_liquidadas,
            )

        return resultado
