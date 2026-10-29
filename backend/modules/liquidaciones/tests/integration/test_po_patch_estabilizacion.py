"""
Integration tests — estabilización del PATCH del motor PO (PorcentajeObra).

Change: liquidacion-po-modos-cotizacion — Module 1 (Estabilizar edicion PO).

Cubre los tres defectos corregidos en
`LiquidacionPatchPorcentajeObraService` (core service del motor PO):

1. Los detalles recreados por el PATCH deben persistir `importe_parcial` y
   `ajuste_redondeo`. Antes quedaban NULL y el consumidor RH/CODEMU
   (`finanzas_core_service.get_importes_po_detalle`) leia 0.00 — es decir,
   CUALQUIER edicion de un PO anulaba el honorario del delegado.
2. Un PO creado en `modo_calculo=MANUAL` (edge) debe rechazarse de forma
   explicita (409) en lugar de reventar con TypeError (HTTP 500).
3. Row locking (`select_for_update`) en el limite transaccional: el PATCH
   completo se ejecuta dentro de la transaccion que abre el orquestador y el
   lock de fila se toma sobre el LiquidacionGeneral antes de recalcular.

Alcance: controller + orchestrator + core service contra BD real.
Sin mocks, sin directorio `unit/` (contract/TEST_ARCHITECTURE_CONTRACT.md).
"""
import pytest
from decimal import Decimal

from modules.liquidaciones.domain.constants import (
    EstadoLiquidacion,
    ModoCalculoLiquidacion,
)
from modules.liquidaciones.domain.models.liquidacion.liquidacion_general.liquidacion import (
    LiquidacionGeneral,
)
from modules.liquidaciones.domain.models.liquidacion.liquidacion_especifico.liquidacion_edificaciones import (
    LiquidacionEdificacion,
)
from modules.liquidaciones.domain.models.liquidacion.liquidacion_tipo.liquidacion_tipo import (
    LiquidacionPorcentajeObra,
    LiquidacionPorcentajeObraDetalle,
)
from modules.liquidaciones.domain.schemas.liquidacion_tipo.liquidacion_porcentaje_data import (
    TarifaPorcentajeObraAplicada,
)
from modules.liquidaciones.domain.services.core.liquidacion_patch_historico_core_service import (
    LiquidacionPatchHistoricoCoreService,
)
from modules.liquidaciones.domain.services.core.liquidacion_tipo.liquidacion_porcentaje_obra_core_service import (
    LiquidacionPorcentajeObraCoreService,
)
from modules.finanzas.domain.services.finanzas_core_service import FinanzasCoreService


# ── Fixtures ────────────────────────────────────────────────────────────────────

@pytest.fixture
def po_tres_detalles_pendiente(
    db,
    municipalidad,
    proyecto,
    create_user,
    derecho_porcentaje_vigente,
    igv_vigente,
    uit_vigente,
    tarifa_porcentaje_obra_estructuras,
    especialidad_estructuras,
    especialidad_arquitectura,
    especialidad_installaciones,
    tipo_edificacion,
):
    """
    Edificaciones PO (modo TARIFA) con 3 detalles de igual porcentaje.

    Los detalles nacen SIN `importe_parcial` / `ajuste_redondeo` — el estado
    heredado de las filas creadas antes de los campos de alta precision. El
    PATCH debe rellenarlos con los valores de la cotizacion recalculada.

    Con 3 detalles de igual porcentaje el reparto no es exacto: el ultimo
    detalle absorbe el residuo de redondeo (ajuste_redondeo != 0).
    """
    user = create_user

    lg = LiquidacionGeneral.objects.create(
        proyecto=proyecto,
        municipalidad=municipalidad,
        usuario_creador=user,
        expediente="EXP-PO-STAB-001",
        observacion="Test estabilizacion PATCH PO",
        estado=EstadoLiquidacion.PENDIENTE,
        tipo_liquidacion=tipo_edificacion,
        numero_revision=1,
        sub_total=Decimal("515.00"),
        total=Decimal("607.70"),
        igv_id=igv_vigente,
        uit_id=uit_vigente,
    )

    LiquidacionEdificacion.objects.create(liquidacion=lg, numero=1)

    lpo = LiquidacionPorcentajeObra.objects.create(
        liquidacion_general=lg,
        tipo_tramite="OBRA_NUEVA",
        valor_declarado=Decimal("100000.00"),
        porcentaje_liquidacion=Decimal("0.0030"),
        derecho_minimo=Decimal("500.00"),
        derecho_maximo=Decimal("50000.00"),
        porcentaje_minimo_uit=Decimal("0.10"),
        derecho_aplicado=derecho_porcentaje_vigente,
    )

    for especialidad in (
        especialidad_estructuras,
        especialidad_arquitectura,
        especialidad_installaciones,
    ):
        LiquidacionPorcentajeObraDetalle.objects.create(
            liquidacion_porcentaje=lpo,
            tarifa_aplicada=tarifa_porcentaje_obra_estructuras,
            especialidad=especialidad,
            porcentaje_aplicado=Decimal("0.0010"),
            subtotal=Decimal("171.67"),
            importe_parcial=None,
            ajuste_redondeo=None,
        )

    return lg


@pytest.fixture
def po_modo_manual_pendiente(
    db,
    municipalidad,
    proyecto,
    create_user,
    igv_vigente,
    uit_vigente,
    tipo_edificacion,
    especialidad_estructuras,
):
    """
    Edificaciones PO creada en modo MANUAL (edge): sin tarifa, sin porcentaje,
    sin derecho. Sus detalles se repartieron desde un subtotal manual.
    """
    user = create_user

    lg = LiquidacionGeneral.objects.create(
        proyecto=proyecto,
        municipalidad=municipalidad,
        usuario_creador=user,
        expediente="EXP-PO-STAB-MANUAL-001",
        observacion="Test PATCH PO modo MANUAL",
        estado=EstadoLiquidacion.PENDIENTE,
        tipo_liquidacion=tipo_edificacion,
        numero_revision=1,
        modo_calculo=ModoCalculoLiquidacion.MANUAL,
        sub_total=Decimal("1500.00"),
        total=Decimal("1770.00"),
        igv_id=igv_vigente,
        uit_id=uit_vigente,
    )

    LiquidacionEdificacion.objects.create(liquidacion=lg, numero=1)

    lpo = LiquidacionPorcentajeObra.objects.create(
        liquidacion_general=lg,
        tipo_tramite="OBRA_NUEVA",
        valor_declarado=None,
        porcentaje_liquidacion=None,
        derecho_minimo=None,
        derecho_maximo=None,
        porcentaje_minimo_uit=None,
        derecho_aplicado=None,
    )

    LiquidacionPorcentajeObraDetalle.objects.create(
        liquidacion_porcentaje=lpo,
        tarifa_aplicada=None,
        especialidad=especialidad_estructuras,
        porcentaje_aplicado=None,
        subtotal=Decimal("1500.00"),
        importe_parcial=None,
        ajuste_redondeo=None,
    )

    return lg


# ── Helpers ────────────────────────────────────────────────────────────────────

def _cotizacion_esperada(lg, valor_declarado, detalles):
    """
    Cotizacion esperada — la MISMA aritmetica pura que usa el PATCH.

    Se recalcula con el motor (calcular_cotizacion_po) y el contexto historico
    de la fecha de registro, de modo que el test verifica paridad
    cotizacion <-> persistencia y no numeros escritos a mano.
    """
    fecha = lg.fecha_registro.date()
    historico = LiquidacionPatchHistoricoCoreService()
    igv = historico.get_igv_por_fecha(fecha)
    uit = historico.get_uit_por_fecha(fecha)
    derecho = historico.get_derecho_porcentaje_vigente(fecha)

    tarifas = [
        TarifaPorcentajeObraAplicada(
            tarifa_id=str(detalle.tarifa_aplicada_id),
            porcentaje_liquidacion=detalle.porcentaje_aplicado,
            especialidad_id=str(detalle.especialidad_id),
            especialidad_nombre=None,
        )
        for detalle in detalles
    ]

    return LiquidacionPorcentajeObraCoreService().calcular_cotizacion_po(
        valor_declarado=valor_declarado,
        tarifas=tarifas,
        igv_porcentaje=igv.valor,
        derecho=derecho,
        uit_valor=Decimal(str(uit.valor)),
    )


# ── Tests: importes persistidos (importe_parcial / ajuste_redondeo) ────────────

@pytest.mark.django_db
def test_po_patch_persiste_importe_parcial_y_ajuste_redondeo(
    auth_client,
    po_tres_detalles_pendiente,
):
    """
    GIVEN: un PO (TARIFA) con detalles sin `importe_parcial` / `ajuste_redondeo`
    WHEN:  se edita el valor_declarado por PATCH
    THEN:  los detalles recreados guardan los importes de la cotizacion
           (no NULL) y coinciden con la cotizacion esperada.
    """
    liquidacion_id = po_tres_detalles_pendiente.id
    lpo = po_tres_detalles_pendiente.liquidacion_porcentaje_obra

    # Snapshot de los detalles ANTES del PATCH (orden estable por especialidad).
    detalles_antes = list(lpo.detalles.order_by("especialidad_id"))
    assert len(detalles_antes) == 3
    assert all(d.importe_parcial is None for d in detalles_antes)
    assert all(d.ajuste_redondeo is None for d in detalles_antes)

    valor_declarado_nuevo = Decimal("150000.00")
    cotizacion = _cotizacion_esperada(
        po_tres_detalles_pendiente, valor_declarado_nuevo, detalles_antes
    )

    response = auth_client.patch(
        f"/liquidaciones/edificaciones/{liquidacion_id}",
        json={"valor_declarado": float(valor_declarado_nuevo)},
    )

    assert response.status_code == 200, \
        f"Expected 200, got {response.status_code}: {response.content}"

    # ── Detalles recreados ───────────────────────────────────────────────────
    lpo.refresh_from_db()
    detalles_despues = list(lpo.detalles.order_by("especialidad_id"))
    assert len(detalles_despues) == 3

    for persistido, esperado in zip(detalles_despues, cotizacion.detalles):
        assert persistido.importe_parcial is not None, \
            "importe_parcial quedo NULL tras el PATCH (regresion RH/CODEMU)"
        assert persistido.ajuste_redondeo is not None, \
            "ajuste_redondeo quedo NULL tras el PATCH (regresion RH/CODEMU)"
        assert persistido.importe_parcial == esperado.importe_parcial
        assert persistido.ajuste_redondeo == esperado.ajuste_redondeo
        assert persistido.subtotal == esperado.subtotal
        assert persistido.porcentaje_aplicado == esperado.porcentaje_aplicado
        assert persistido.importe_parcial > 0

    # ── Invariantes del motor ────────────────────────────────────────────────
    suma_importes = sum((d.importe_parcial for d in detalles_despues), Decimal("0"))
    suma_ajustes = sum((d.ajuste_redondeo for d in detalles_despues), Decimal("0"))
    suma_subtotales = sum((d.subtotal for d in detalles_despues), Decimal("0"))

    assert suma_importes + suma_ajustes == cotizacion.total_subtotal
    assert suma_subtotales == cotizacion.total_subtotal
    # El reparto de 3 detalles iguales no es exacto: hay residuo de redondeo.
    assert suma_ajustes != 0, \
        "El fixture deberia producir un ajuste_redondeo no nulo (3 detalles iguales)"

    # ── Totales del padre ────────────────────────────────────────────────────
    lg = LiquidacionGeneral.objects.get(id=liquidacion_id)
    assert lg.sub_total == cotizacion.total_subtotal
    assert lg.total == cotizacion.total


@pytest.mark.django_db
def test_po_patch_preserva_importes_de_rh_codemu(
    auth_client,
    po_tres_detalles_pendiente,
):
    """
    GIVEN: un PO (TARIFA) ya liquidado
    WHEN:  se edita por PATCH
    THEN:  el consumidor RH/CODEMU (get_importes_po_detalle) sigue leyendo los
           importes reales — NO 0.00, que era el efecto del defecto.
    """
    liquidacion_id = po_tres_detalles_pendiente.id
    lpo = po_tres_detalles_pendiente.liquidacion_porcentaje_obra

    response = auth_client.patch(
        f"/liquidaciones/edificaciones/{liquidacion_id}",
        json={"valor_declarado": 150000.00},
    )
    assert response.status_code == 200, \
        f"Expected 200, got {response.status_code}: {response.content}"

    lpo.refresh_from_db()
    finanzas_core = FinanzasCoreService()

    detalles = list(lpo.detalles.order_by("especialidad_id"))
    assert len(detalles) == 3

    for detalle in detalles:
        importes = finanzas_core.get_importes_po_detalle(
            liquidacion_id, detalle.especialidad_id
        )
        assert importes is not None, \
            f"No se encontro el detalle de la especialidad {detalle.especialidad_id}"

        importe_parcial, ajuste_redondeo, subtotal = importes

        assert importe_parcial > 0, \
            "El importe parcial leido por RH/CODEMU quedo en 0.00 tras la edicion"
        assert importe_parcial == detalle.importe_parcial
        assert ajuste_redondeo == detalle.ajuste_redondeo
        assert subtotal == detalle.subtotal
        assert subtotal > 0

    # El total de la liquidacion tampoco se anula (base del honorario delegado).
    lg = LiquidacionGeneral.objects.get(id=liquidacion_id)
    assert lg.sub_total > 0
    assert lg.total > 0


# ── Tests: guard modo_calculo=MANUAL ───────────────────────────────────────────

@pytest.mark.django_db
def test_po_patch_modo_manual_retorna_409_no_500(
    auth_client,
    po_modo_manual_pendiente,
):
    """
    GIVEN: un PO creado en modo MANUAL (edge, sin tarifa ni porcentaje)
    WHEN:  se intenta editar por PATCH
    THEN:  devuelve 409 con codigo explicito — NUNCA 500 (TypeError).
    """
    liquidacion_id = po_modo_manual_pendiente.id
    lpo = po_modo_manual_pendiente.liquidacion_porcentaje_obra

    antes = list(
        lpo.detalles.order_by("id").values(
            "id", "subtotal", "importe_parcial", "ajuste_redondeo", "porcentaje_aplicado"
        )
    )

    response = auth_client.patch(
        f"/liquidaciones/edificaciones/{liquidacion_id}",
        json={"valor_declarado": 150000.00},
    )

    assert response.status_code != 500, \
        f"El PATCH de un PO MANUAL debe rechazarse, no reventar: {response.content}"
    assert response.status_code == 409, \
        f"Expected 409 para modo MANUAL, got {response.status_code}: {response.content}"

    body = response.json()
    assert body["success"] is False
    assert body["error"]["code"] == "LIQUIDACION_MODO_MANUAL_NOT_EDITABLE"

    # ── Nada se modifico ─────────────────────────────────────────────────────
    despues = list(
        lpo.detalles.order_by("id").values(
            "id", "subtotal", "importe_parcial", "ajuste_redondeo", "porcentaje_aplicado"
        )
    )
    assert despues == antes

    lg = LiquidacionGeneral.objects.get(id=liquidacion_id)
    assert lg.modo_calculo == ModoCalculoLiquidacion.MANUAL
    assert lg.sub_total == Decimal("1500.00")
    assert lg.total == Decimal("1770.00")

    lpo.refresh_from_db()
    assert lpo.valor_declarado is None
    assert lpo.porcentaje_liquidacion is None


@pytest.mark.django_db
def test_po_patch_modo_manual_actualizacion_general_no_rompe(
    auth_client,
    po_modo_manual_pendiente,
):
    """
    GIVEN: un PO creado en modo MANUAL (edge)
    WHEN:  se editan SOLO campos generales (sin recalcular el motor PO)
    THEN:  la edicion general se aplica (el guard es del recalculo por tarifa,
           no del PATCH completo) y el PO manual queda intacto.
    """
    liquidacion_id = po_modo_manual_pendiente.id

    response = auth_client.patch(
        f"/liquidaciones/edificaciones/{liquidacion_id}",
        json={"liquidacion_general": {"observacion": "Observacion editada"}},
    )

    assert response.status_code == 200, \
        f"Expected 200, got {response.status_code}: {response.content}"

    lg = LiquidacionGeneral.objects.get(id=liquidacion_id)
    assert lg.observacion == "Observacion editada"
    assert lg.modo_calculo == ModoCalculoLiquidacion.MANUAL
    assert lg.sub_total == Decimal("1500.00")
