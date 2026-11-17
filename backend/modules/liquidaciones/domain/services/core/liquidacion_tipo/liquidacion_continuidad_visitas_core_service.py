"""
Core Service para la CONTINUIDAD de visitas de Inspección de Obra.

Responsabilidades:

1. Calcular el valor completo del trabajo de B (`monto_acumulado` / `total_acumulado`)
   reutilizando la aritmética de `LiquidacionPorCategoriaVisitasCoreService`.
2. Persistir la fila de continuidad (OneToOne sobre la LCV de B).
3. Exponer el RESOLVER CONDICIONAL DE BASE RH — la única regla que usan tanto
   la cotización del RH mensual como el listado de candidatas de inspector.

Regla única de base RH (contrato del cambio io-continuidad-visitas-impacto):

    base_rh = continuidad.monto_acumulado   # B tiene fila de continuidad
    base_rh = liquidacion_general.sub_total  # IO normal (sin fila)

Sin fila de continuidad la regla resuelve exactamente el valor vigente, por lo
que el comportamiento de una IO normal no cambia (bit a bit).
"""
from decimal import Decimal, ROUND_HALF_UP
from typing import Optional

from injector import inject

from core.exceptions import ConflictError
from modules.liquidaciones.domain.models.liquidacion.liquidacion_general.liquidacion import (
    LiquidacionGeneral,
)
from modules.liquidaciones.domain.models.liquidacion.liquidacion_tipo.liquidacion_tipo import (
    LiquidacionContinuidadVisitas,
    LiquidacionPorCategoriaVisitas,
)

#: Precisión monetaria del proyecto (2 decimales, ROUND_HALF_UP).
TWO_PLACES = Decimal("0.01")


def quantize_money(value: Decimal) -> Decimal:
    """Redondea a la precisión monetaria del proyecto (TWO_PLACES, ROUND_HALF_UP)."""
    return Decimal(str(value)).quantize(TWO_PLACES, rounding=ROUND_HALF_UP)


class LiquidacionContinuidadVisitasCoreService:
    """
    Core service (sync) de la continuidad de visitas.

    NO abre `transaction.atomic()`: el flujo (o el servicio de recálculo)
    provee la transacción.
    """

    @inject
    def __init__(self):
        pass

    # ── Resolver de base RH (regla única compartida) ────────────────────────────

    @staticmethod
    def resolver_base_rh(
        liquidacion_visitas: LiquidacionPorCategoriaVisitas,
        liquidacion_general=None,
    ) -> Decimal:
        """
        Resuelve la BASE monetary del RH mensual del inspector.

        Única fuente de verdad: la usan `RHInspectorMensualCotizarFlujo.cotizar`
        y `FinanzasCoreService.list_liquidaciones_inspector_candidatas`
        (variante paginada y no paginada).

        - Con fila de continuidad  → `continuidad.monto_acumulado` (valor completo
          del trabajo de B, que es lo que corresponde al inspector nuevo).
        - Sin fila de continuidad  → `liquidacion_general.sub_total`
          (comportamiento vigente, sin cambios).

        Args:
            liquidacion_visitas: LCV de la IO.
            liquidacion_general: cabecera ya cargada (opcional, evita una
                consulta adicional cuando el caller ya la tiene).

        Returns:
            Decimal con la base a usar para el cálculo de costo por inspección.
        """
        continuidad = LiquidacionContinuidadVisitasCoreService.get_continuidad(
            liquidacion_visitas
        )
        if continuidad is not None:
            return Decimal(str(continuidad.monto_acumulado or 0))

        if liquidacion_general is None:
            liquidacion_general = liquidacion_visitas.liquidacion_general
        return Decimal(str(liquidacion_general.sub_total or 0))

    @staticmethod
    def get_continuidad(
        liquidacion_visitas: LiquidacionPorCategoriaVisitas,
    ) -> Optional[LiquidacionContinuidadVisitas]:
        """
        Devuelve la fila de continuidad de la LCV o None si no tiene.

        Maneja el `RelatedObjectDoesNotExist` del OneToOne inverso: una IO sin
        continuidad NO es un error, es el caso normal (R7).
        """
        try:
            return liquidacion_visitas.continuidad
        except LiquidacionContinuidadVisitas.DoesNotExist:
            return None

    # ── Cálculo ────────────────────────────────────────────────────────────────

    @staticmethod
    def calcular_montos_acumulados(
        monto_neto_visitas: Decimal,
        igv_valor: Decimal,
    ) -> tuple[Decimal, Decimal]:
        """
        Calcula el par (neto, bruto) del valor completo del trabajo.

        Args:
            monto_neto_visitas: valor neto de las visitas de B (sin IGV).
            igv_valor: tasa de IGV vigente (fracción, ej. 0.18).

        Returns:
            (monto_acumulado, total_acumulado) con precisión monetaria.
        """
        monto_acumulado = quantize_money(monto_neto_visitas)
        total_acumulado = quantize_money(monto_acumulado * (Decimal("1") + Decimal(str(igv_valor))))
        return monto_acumulado, total_acumulado

    @staticmethod
    def calcular_diferencia(
        monto_acumulado: Decimal,
        total_acumulado: Decimal,
        subtotal_credito: Decimal,
        total_credito: Decimal,
    ) -> tuple[Decimal, Decimal]:
        """
        Calcula la DIFERENCIA a cobrar al cliente.

        La diferencia neta y la diferencia bruta quedan consistentes entre sí:
        `total_acumulado - total_credito` es exactamente la diferencia bruta, de
        modo que el documento (valor completo − crédito = a cobrar) cuadra al
        centavo.

        Returns:
            (sub_total_diferencia, total_diferencia)
        """
        sub_total_diferencia = quantize_money(
            Decimal(str(monto_acumulado)) - Decimal(str(subtotal_credito))
        )
        total_diferencia = quantize_money(
            Decimal(str(total_acumulado)) - Decimal(str(total_credito))
        )
        return sub_total_diferencia, total_diferencia

    # ── Persistencia ───────────────────────────────────────────────────────────

    def crear_continuidad(
        self,
        liquidacion_visitas: LiquidacionPorCategoriaVisitas,
        *,
        monto_acumulado: Decimal,
        total_acumulado: Decimal,
        subtotal_credito: Decimal,
        total_credito: Decimal,
        liquidacion_previa: Optional[LiquidacionGeneral] = None,
        visitas_previas_totales: Optional[int] = None,
        visitas_previas_pendientes: Optional[int] = None,
        categoria_previa: Optional[str] = None,
        observacion: Optional[str] = None,
    ) -> LiquidacionContinuidadVisitas:
        """
        Crea la fila de continuidad de B.

        Se invoca dentro de la misma `transaction.atomic` que la creación de B
        (contrato Django P5: la atomicidad la controla el flujo).
        """
        return LiquidacionContinuidadVisitas.objects.create(
            liquidacion_visitas=liquidacion_visitas,
            liquidacion_previa=liquidacion_previa,
            monto_acumulado=quantize_money(monto_acumulado),
            total_acumulado=quantize_money(total_acumulado),
            subtotal_credito=quantize_money(subtotal_credito),
            total_credito=quantize_money(total_credito),
            visitas_previas_totales=visitas_previas_totales,
            visitas_previas_pendientes=visitas_previas_pendientes,
            categoria_previa=categoria_previa,
            observacion=observacion,
        )

    @staticmethod
    def recalcular_continuidad(
        continuidad: LiquidacionContinuidadVisitas,
        *,
        monto_acumulado: Decimal,
        total_acumulado: Decimal,
    ) -> LiquidacionContinuidadVisitas:
        """
        Recalcula el valor completo del trabajo tras editar B.

        El CRÉDITO (`subtotal_credito` / `total_credito`) queda CONGELADO:
        pertenece a la liquidación previa (A) y no depende de las visitas ni de
        la tarifa de B.

        Es un método estático (no usa estado) para que los servicios que lo
        consumen —p. ej. `LiquidacionPatchVisitasService`— no tengan que
        instanciar este core service dentro de otro servicio (contrato Django
        P4: "nunca instanciar servicios a mano dentro de otros servicios").
        """
        continuidad.monto_acumulado = quantize_money(monto_acumulado)
        continuidad.total_acumulado = quantize_money(total_acumulado)
        continuidad.save(update_fields=["monto_acumulado", "total_acumulado", "updated_at"])
        return continuidad

    def actualizar_continuidad(
        self,
        continuidad: LiquidacionContinuidadVisitas,
        *,
        monto_acumulado: Decimal,
        total_acumulado: Decimal,
        subtotal_credito: Decimal,
        total_credito: Decimal,
        liquidacion_previa: Optional[LiquidacionGeneral] = None,
        visitas_previas_totales: Optional[int] = None,
        visitas_previas_pendientes: Optional[int] = None,
        categoria_previa: Optional[str] = None,
        observacion: Optional[str] = None,
    ) -> LiquidacionContinuidadVisitas:
        """
        Actualiza el registro de continuidad de B (modo `mantener`).

        Escribe el VALOR COMPLETO del trabajo (`monto_acumulado` /
        `total_acumulado`, recalculados por el servidor) y el CRÉDITO de la
        previa (`subtotal_credito` / `total_credito`, este último ya derivado
        por el servidor aplicando el IGV de referencia).

        NO toca la liquidación previa (A): su tarifa y su valor son un snapshot
        histórico y nunca se re-cotan. Lo que se actualiza es el puntero a A
        dentro del registro de continuidad.

        El `save()` completo (sin `update_fields`) es deliberado: `simple_history`
        registra el cambio con todos sus campos.

        Se invoca dentro de la transacción del PATCH (contrato Django P5).
        """
        continuidad.monto_acumulado = quantize_money(monto_acumulado)
        continuidad.total_acumulado = quantize_money(total_acumulado)
        continuidad.subtotal_credito = quantize_money(subtotal_credito)
        continuidad.total_credito = quantize_money(total_credito)
        continuidad.liquidacion_previa = liquidacion_previa
        continuidad.visitas_previas_totales = visitas_previas_totales
        continuidad.visitas_previas_pendientes = visitas_previas_pendientes
        continuidad.categoria_previa = categoria_previa
        continuidad.observacion = observacion
        continuidad.save()
        return continuidad

    @staticmethod
    def eliminar_continuidad(continuidad: LiquidacionContinuidadVisitas) -> None:
        """
        Elimina la fila de continuidad de B (modo `desactivar`).

        Se invoca dentro de la transacción del PATCH (contrato Django P5):
        eliminar la fila y restaurar los montos normales de B es una sola
        operación atómica. La evidencia histórica del crédito eliminado queda
        en el historial (`simple_history`).
        """
        continuidad.delete()

    @staticmethod
    def guardar_editable_por_rh(
        liquidacion_visitas: LiquidacionPorCategoriaVisitas,
    ) -> None:
        """
        Lanza `ConflictError` (409) si la IO tiene RH mensual o pagos al inspector.

        Precedente directo: `DelegadoCoreService._bloquear_edicion_con_rh_mensual`
        (la asignación de delegado con detalle de honorario vinculado a un RH
        mensual no es editable y se comprueba ANTES de escribir nada).

        Por qué bloquea la continuidad:
        - `DetalleHonorarioInspector` CONGELA `importe_bruto`,
          `costo_por_inspeccion`, `inspecciones_programadas` y `saldo_restante`:
          editar el crédito o apagar la continuidad dejaría dos bases distintas
          en el historial del inspector.
        - `RegistroPagoInspector` (ledger) descuenta inspecciones pagadas del
          saldo: bajar las visitas de B deja `saldo_disponible` negativo y la
          cotización RH futura falla con 400.

        Alcance (D9, diferido a propósito): el guard SOLO se dispara cuando el
        PATCH trae una operación de continuidad. Las ediciones de B solo de
        visitas/tarifa con RH presente siguen permitidas como hoy.

        El import de finanzas es de SOLO MODELOS: no genera ciclo con
        `modules.finanzas.domain.services`.

        Raises:
            ConflictError: 409 si hay detalle de honorario o registro de pago.
        """
        from modules.finanzas.domain.models.detalle_honorario_inspector import (
            DetalleHonorarioInspector,
        )
        from modules.finanzas.domain.models.registro_pago_inspector import (
            RegistroPagoInspector,
        )

        tiene_detalle_honorario = DetalleHonorarioInspector.objects.filter(
            liquidacion_por_categoria_visitas=liquidacion_visitas,
        ).exists()
        if tiene_detalle_honorario:
            raise ConflictError(
                message=(
                    "No se puede modificar la continuidad de la inspección de obra "
                    "porque ya tiene un recibo de honorario mensual emitido. "
                    "Elimina primero el recibo de honorario mensual."
                ),
                code="IO_CONTINUIDAD_CON_RH_MENSUAL_NOT_EDITABLE",
            )

        tiene_registro_pago = RegistroPagoInspector.objects.filter(
            liquidacion_por_categoria_visitas=liquidacion_visitas,
        ).exists()
        if tiene_registro_pago:
            raise ConflictError(
                message=(
                    "No se puede modificar la continuidad de la inspección de obra "
                    "porque ya tiene pagos registrados al inspector. "
                    "Elimina primero los registros de pago."
                ),
                code="IO_CONTINUIDAD_CON_PAGOS_INSPECTOR_NOT_EDITABLE",
            )
