"""
Integration tests for RH Inspector Mensual flows — cotización y creación.

Tests usan los flujos directamente (no HTTP) para evitar problemas de inyección
con TestClient. Los flujos son los mismos que los endpoints llaman por detrás.
Tests usan @pytest.mark.django_db para acceso a BD.

Covers:
- RHInspectorMensualCotizarFlujo.cotizar() — cotización sin BD
- RHInspectorMensualCrearFlujo.crear() — creación con BD
- Validación: CIP no existe → 404
- Validación: expediente no asociado al inspector → 400
- Validación: saldo excedido → 400
- Idempotencia del crear (get_or_create)
- No pagar doble (saldo reducido tras crear)
"""
import pytest
from decimal import Decimal
from datetime import date

from modules.entidades.domain.models.ubigeo import (
    UbigeoDepartamento,
    UbigeoProvincia,
    UbigeoDistrito,
)
from modules.entidades.domain.models.municipalidad import Municipalidad
from modules.usuarios.domain.models.perfil_ingeniero import (
    PerfilIngeniero,
    EspecialidadRevision,
)
from modules.liquidaciones.domain.models.inspector import Inspector, LiquidacionInspector
from modules.liquidaciones.domain.models.tipo_liquidacion import TipoLiquidacion as TipoLiquidacionModel
from modules.liquidaciones.domain.models.proyecto import Proyecto
from modules.liquidaciones.domain.models.liquidacion.liquidacion_general.liquidacion import (
    LiquidacionGeneral,
)
from modules.liquidaciones.domain.models.liquidacion.liquidacion_tipo.liquidacion_tipo import (
    LiquidacionPorCategoriaVisitas,
)
from modules.liquidaciones.domain.models.liquidacion.liquidacion_tipo.tarifas_reglas import (
    TarifaLiquidacionBase,
    TarifaPorCategoriaVisitas,
)
from modules.liquidaciones.domain.models.liquidacion.liquidacion_especifico.liquidacion_inspeccion_obra import (
    LiquidacionInspeccionObra,
)
from modules.liquidaciones.domain.models.liquidacion.liquidacion_general.comprobante import (
    LiquidacionComprobante,
)
from modules.liquidaciones.domain.constants import TipoLiquidacion as TipoLiquidacionConst
from modules.finanzas.domain.models.descuento_inspector import (
    EscalaDescuentoInspector,
    RangoDescuentoInspector,
)
from modules.finanzas.domain.models.recibo_honorario_inspector_mensual import (
    ReciboHonorarioInspectorMensual,
)
from modules.finanzas.domain.models.detalle_honorario_inspector import (
    DetalleHonorarioInspector,
)
from modules.finanzas.domain.models.registro_pago_inspector import (
    RegistroPagoInspector,
)
from modules.finanzas.domain.services.finanzas_core_service import FinanzasCoreService
from modules.finanzas.domain.services.flujos.rh_inspector_mensual_flujo import (
    RHInspectorMensualCotizarFlujo,
    RHInspectorMensualCrearFlujo,
    RHInspectorMensualListFlujo,
    RHInspectorMensualDeleteFlujo,
    RHInspectorMensualActualizarFlujo,
)
from modules.finanzas.domain.schemas import (
    RHInspectorActualizarIn,
    RHInspectorActualizarItemIn,
    RHInspectorCotizarIn,
    RHInspectorCotizarItemIn,
)
from modules.finanzas.domain.results.rh_delegado_mensual_result import (
    DelegadoRHMinimalResult,
    LiquidacionComprobanteMinimalResult,
    RHDelegadoMensualDetalleResult,
    RHDelegadoMensualListItemResult,
    RHDelegadoMensualTotalesResult,
    RHDelegadoVariablesCalculoResult,
)
from modules.finanzas.presentation.presenters.finanzas_presenter import FinanzasPresenter
from django.contrib.auth import get_user_model
import json
import uuid


# ── Fixtures ────────────────────────────────────────────────────────────────────

@pytest.fixture
def escala_descuento_15(db):
    """Escala vigente con rango 15% (0 – 8000)."""
    escala = EscalaDescuentoInspector.objects.create(
        nombre="Escala 2026",
        periodo_inicio=date(2026, 1, 1),
        periodo_fin=None,
    )
    RangoDescuentoInspector.objects.create(
        escala=escala,
        monto_minimo=Decimal("0"),
        monto_maximo=Decimal("8000"),
        porcentaje_descuento=Decimal("0.15"),
    )
    RangoDescuentoInspector.objects.create(
        escala=escala,
        monto_minimo=Decimal("8000"),
        monto_maximo=Decimal("15000"),
        porcentaje_descuento=Decimal("0.20"),
    )
    RangoDescuentoInspector.objects.create(
        escala=escala,
        monto_minimo=Decimal("15000"),
        monto_maximo=Decimal("30000"),
        porcentaje_descuento=Decimal("0.30"),
    )
    RangoDescuentoInspector.objects.create(
        escala=escala,
        monto_minimo=Decimal("30000"),
        monto_maximo=None,
        porcentaje_descuento=Decimal("0.40"),
    )
    return escala


@pytest.fixture
def ubigeo_test(db):
    depto = UbigeoDepartamento.objects.create(nombre="LIMA")
    prov = UbigeoProvincia.objects.create(departamento=depto, nombre="LIMA")
    dist = UbigeoDistrito.objects.create(
        provincia=prov, nombre="MIRAFLORES", ubigeo="150132"
    )
    return dist


@pytest.fixture
def municipalidad_test(db, ubigeo_test):
    return Municipalidad.objects.create(
        codigo="M001",
        nombre="Municipalidad de Miraflores",
        distrito=ubigeo_test,
    )


@pytest.fixture
def proyecto_test(db, municipalidad_test, ubigeo_test):
    return Proyecto.objects.create(
        nombre_propietario="Propietario IO SAC",
        direccion="Av. Test 123",
        distrito=ubigeo_test,
        entidad_tipo_documento="RUC",
        entidad_numero_documento="20456789012",
        entidad_razon_social="Propietario IO SAC",
    )


@pytest.fixture
def segundo_proyecto_test(db, municipalidad_test, ubigeo_test):
    """Second Proyecto.

    `LiquidacionGeneral.proyecto` is a OneToOneField, so every LiquidacionGeneral
    needs its own Proyecto. Sharing `proyecto_test` between two liquidaciones
    violates the unique constraint on `proyecto_id`.
    """
    return Proyecto.objects.create(
        nombre_propietario="Propietario IO Dos SAC",
        direccion="Av. Test 456",
        distrito=ubigeo_test,
        entidad_tipo_documento="RUC",
        entidad_numero_documento="20456789013",
        entidad_razon_social="Propietario IO Dos SAC",
    )


@pytest.fixture
def usuario_inspector(db):
    User = get_user_model()
    return User.objects.create_user(
        username="inspector_mensual",
        email="inspector_mensual@test.com",
        password="testpass123",
        dni="76543210",
    )


@pytest.fixture
def perfil_ingeniero_inspector(db, usuario_inspector):
    return PerfilIngeniero.objects.create(
        usuario=usuario_inspector,
        apellido_paterno="Quispe",
        apellido_materno="Rojas",
        nombres="María",
        cip="CIP-88888",
        dni="76543210",
    )


@pytest.fixture
def inspector(db, perfil_ingeniero_inspector):
    return Inspector.objects.create(perfil_ingeniero=perfil_ingeniero_inspector)


@pytest.fixture
def especialidad_revision(db):
    return EspecialidadRevision.objects.create(
        slug="estructuras", nombre="Estructuras",
    )


@pytest.fixture
def tipo_inspeccion_obra(db):
    return TipoLiquidacionModel.objects.get_or_create(
        codigo=TipoLiquidacionConst.INSPECCION_OBRA,
        defaults={"nombre": "Inspección de Obra"},
    )[0]


@pytest.fixture
def usuario_liquidacion(db):
    User = get_user_model()
    return User.objects.create_user(
        username="liq_mensual",
        email="liq_mensual@test.com",
        password="testpass123",
        dni="11223344",
    )


@pytest.fixture
def liquidacion_general_io(
    db, proyecto_test, municipalidad_test, tipo_inspeccion_obra, usuario_liquidacion
):
    """LiquidacionGeneral de tipo INSPECCION_OBRA con sub_total=1000.00."""
    return LiquidacionGeneral.objects.create(
        proyecto=proyecto_test,
        municipalidad=municipalidad_test,
        tipo_liquidacion=tipo_inspeccion_obra,
        usuario_creador=usuario_liquidacion,
        expediente="EXP-MENSUAL-001",
        estado="REGISTRADO",
        sub_total=Decimal("1000.00"),
        total=Decimal("1180.00"),
    )


@pytest.fixture
def tarifa_base_io(db, tipo_inspeccion_obra):
    return TarifaLiquidacionBase.objects.create(
        tipo_liquidacion=tipo_inspeccion_obra,
        periodo_inicio=date(2024, 1, 1),
        periodo_fin=None,
    )


@pytest.fixture
def tarifa_visitas_io(db, tarifa_base_io):
    return TarifaPorCategoriaVisitas.objects.create(
        tarifa_base=tarifa_base_io,
        porcentaje_uit=Decimal("0.05"),
        categoria_visitas="INSPECCION",
    )


@pytest.fixture
def liquidacion_visitas(db, liquidacion_general_io, tarifa_visitas_io):
    """LiquidacionPorCategoriaVisitas con 10 visitas programadas."""
    return LiquidacionPorCategoriaVisitas.objects.create(
        liquidacion_general=liquidacion_general_io,
        cantidad_visitas=10,
        porcentaje_uit=Decimal("0.05"),
        categoria="A",
        tarifa_aplicada=tarifa_visitas_io,
    )


@pytest.fixture
def liquidacion_io(db, liquidacion_general_io):
    """LiquidacionInspeccionObra (específico) de la IO."""
    return LiquidacionInspeccionObra.objects.create(liquidacion=liquidacion_general_io)


@pytest.fixture
def liquidacion_inspector(
    db, liquidacion_visitas, inspector, especialidad_revision
):
    """LiquidacionInspector asociando el inspector a la IO."""
    return LiquidacionInspector.objects.create(
        liquidacion=liquidacion_visitas,
        inspector=inspector,
        especialidad_revision=especialidad_revision,
    )


# ── Flujo directo helpers ───────────────────────────────────────────────────────

@pytest.fixture
def core_service(db):
    return FinanzasCoreService()


@pytest.fixture
def cotizar_flujo(core_service):
    return RHInspectorMensualCotizarFlujo(core=core_service)


@pytest.fixture
def crear_flujo(core_service, cotizar_flujo):
    return RHInspectorMensualCrearFlujo(core=core_service, cotizar_flujo=cotizar_flujo)


def _payload(cip: str, periodo: int, mes: int, items: list[dict]):
    """Helper para construir el payload de cotización."""
    return RHInspectorCotizarIn(
        cip=cip,
        periodo=periodo,
        mes=mes,
        items=[RHInspectorCotizarItemIn(**i) for i in items],
    )


# ── Tests ──────────────────────────────────────────────────────────────────────

@pytest.mark.django_db
def test_endpoint_list_rh_inspector_sin_paginacion(
    auth_client,
    db,
    inspector,
    escala_descuento_15,
):
    """
    GIVEN: Un RH mensual de inspector del periodo 2026-01
    WHEN:  GET /finanzas/recibos-inspectores con sin_paginacion=true
    THEN:  Devuelve el conjunto completo en una sola respuesta (total_pages=1)
    """
    ReciboHonorarioInspectorMensual.objects.create(
        inspector=inspector,
        periodo=2026,
        mes=1,
        escala_descuento=escala_descuento_15,
        sub_total=Decimal("1000.00"),
        descuento=Decimal("150.00"),
        honorarios=Decimal("850.00"),
    )

    response = auth_client.get(
        "/finanzas/recibos-inspectores"
        "?page=1&page_size=20&sin_paginacion=true&periodo=2026&mes=1"
    )

    assert response.status_code == 200
    body = response.json()
    assert body["success"] is True
    data = body["data"]
    assert data["total"] == 1
    assert len(data["items"]) == 1
    assert data["total_pages"] == 1


@pytest.mark.django_db
def test_cotizar_con_cip_valido_inspector_asociado(
    cotizar_flujo,
    inspector,
    perfil_ingeniero_inspector,
    liquidacion_inspector,
    liquidacion_visitas,
    liquidacion_general_io,
    escala_descuento_15,
):
    """
    RHInspectorMensualCotizarFlujo.cotizar con CIP válido y expediente belonging
    to the inspector returns correct calculation WITHOUT creating anything in BD.

    sub_total=1000.00, visitas=10, cantidad_visitas=4:
        costo_por_inspeccion = 100.00
        monto_contribuido = 400.00
        sub_total agrupado = 400.00 → 15% → descuento 60.00, honorarios 340.00
    """
    assert ReciboHonorarioInspectorMensual.objects.count() == 0

    result = cotizar_flujo.cotizar(
        _payload(
            cip=perfil_ingeniero_inspector.cip,
            periodo=2026, mes=1,
            items=[{
                "exp_liqui": liquidacion_general_io.expediente,
                "cantidad_visitas": 4,
                "periodo": 2027,
                "mes": 3,
            }],
        )
    )

    assert result.inspector.id == str(inspector.id)
    assert result.inspector.cip == perfil_ingeniero_inspector.cip
    assert result.periodo == 2026
    assert result.mes == 1
    assert len(result.items) == 1

    item = result.items[0]
    assert item.exp_liqui == liquidacion_general_io.expediente
    assert item.inspecciones_programadas == 10
    assert item.inspecciones_liquidadas == 4
    assert Decimal(str(item.costo_por_inspeccion)) == Decimal("100.00")
    assert Decimal(str(item.monto_contribuido)) == Decimal("400.00")
    assert item.saldo_disponible == 10  # available before this quote (no prior payments)
    assert item.saldo_restante == 6  # remaining after this quote: 10 - 0 - 4
    # New fields: liquidacion_especifica_numero and comprobante_activo are null-safe
    assert hasattr(item, "liquidacion_especifica_numero")
    assert hasattr(item, "comprobante_activo")
    assert item.liquidacion_especifica_numero is None  # LiquidacionInspeccionObra has no numero set
    assert item.comprobante_activo is None  # no comprobante activo in test fixture

    assert Decimal(str(result.totales.sub_total)) == Decimal("400.00")
    assert Decimal(str(result.totales.tasa_descuento_aplicada)) == Decimal("0.15")
    assert Decimal(str(result.totales.descuento)) == Decimal("60.00")
    assert Decimal(str(result.totales.honorarios)) == Decimal("340.00")
    assert result.items[0].liquidacion_inspector_id == str(liquidacion_inspector.id)
    assert result.items[0].periodo == 2027
    assert result.items[0].mes == 3

    # Cotizar NO crea nada en BD
    assert ReciboHonorarioInspectorMensual.objects.count() == 0


@pytest.mark.django_db
def test_cotizar_saldo_restante_refleja_quoted(
    cotizar_flujo,
    inspector,
    perfil_ingeniero_inspector,
    liquidacion_inspector,
    liquidacion_visitas,
    liquidacion_general_io,
    escala_descuento_15,
):
    """
    saldo_restante muestra el saldo DESPUÉS de cotizar, no el disponible antes.

    Escenario: programadas=10, pagadas_historicas=3, cantidad_visitas=3
        → saldo_disponible=7 (antes), saldo_restante=4 (después)
    """
    # Simular 3 inspecciones ya pagadas en periodo anterior
    RegistroPagoInspector.objects.create(
        liquidacion_por_categoria_visitas=liquidacion_visitas,
        periodo=2025,
        mes=12,  # mes anterior
        inspecciones_pagadas=3,
    )

    result = cotizar_flujo.cotizar(
        _payload(
            cip=perfil_ingeniero_inspector.cip,
            periodo=2026, mes=1,
            items=[{"exp_liqui": liquidacion_general_io.expediente, "cantidad_visitas": 3}],
        )
    )

    item = result.items[0]
    assert item.inspecciones_programadas == 10
    assert item.inspecciones_pagadas_hasta_mes_anterior == 3
    assert item.inspecciones_liquidadas == 3
    assert item.saldo_disponible == 7  # 10 - 3 (antes de esta cotización)
    assert item.saldo_restante == 4  # 10 - 3 - 3 (después de esta cotización)


@pytest.mark.django_db
def test_cotizar_cip_inexistente(cotizar_flujo, escala_descuento_15):
    """
    Cotizar con CIP inexistente → HttpError 404.
    """
    from ninja.errors import HttpError

    with pytest.raises(HttpError) as excinfo:
        cotizar_flujo.cotizar(
            _payload(
                cip="CIP-INEXISTENTE",
                periodo=2026, mes=1,
                items=[{"exp_liqui": "EXP-ANY", "cantidad_visitas": 1}],
            )
        )
    assert excinfo.value.status_code == 404


@pytest.mark.django_db
def test_cotizar_expediente_no_pertenece_al_inspector(
    cotizar_flujo,
    inspector,
    perfil_ingeniero_inspector,
    escala_descuento_15,
    tipo_inspeccion_obra,
    proyecto_test,
    municipalidad_test,
    usuario_liquidacion,
    tarifa_visitas_io,
    liquidacion_inspector,
):
    """
    Cotizar con un expediente associado a OTRO inspector (no al que hace la query)
    → HttpError 400.

    El primer inspector (liquidacion_inspector) tiene EXP-MENSUAL-001.
    Creamos un segundo inspector con su propria liquidación (EXP-OTRO-001).
    Usamos el CIP del primer inspector pero el expediente del segundo → 400.
    """
    # Segundo inspector
    User = get_user_model()
    user2 = User.objects.create_user(
        username="inspector_otro", email="otro@test.com",
        password="testpass123", dni="33333333",
    )
    perfil2 = PerfilIngeniero.objects.create(
        usuario=user2, apellido_paterno="Torres",
        apellido_materno="Luis", nombres="Pedro",
        cip="CIP-99999", dni="33333333",
    )
    inspector2 = Inspector.objects.create(perfil_ingeniero=perfil2)

    proyecto_otro = Proyecto.objects.create(
        nombre_propietario="Propietario Otro Inspector SAC",
        direccion="Av. Otro Inspector 456",
        distrito=proyecto_test.distrito,
        entidad_tipo_documento="RUC",
        entidad_numero_documento="20999999991",
        entidad_razon_social="Propietario Otro Inspector SAC",
    )

    # LiquidacionGeneral + LiquidacionPorCategoriaVisitas + LiquidacionInspector para inspector2
    lg_otro = LiquidacionGeneral.objects.create(
        proyecto=proyecto_otro,
        municipalidad=municipalidad_test,
        tipo_liquidacion=tipo_inspeccion_obra,
        usuario_creador=usuario_liquidacion,
        expediente="EXP-OTRO-001",
        estado="REGISTRADO",
        sub_total=Decimal("3000.00"),
        total=Decimal("3540.00"),
    )
    lcv_otro = LiquidacionPorCategoriaVisitas.objects.create(
        liquidacion_general=lg_otro,
        cantidad_visitas=10,
        porcentaje_uit=Decimal("0.05"),
        categoria="A",
        tarifa_aplicada=tarifa_visitas_io,
    )
    LiquidacionInspector.objects.create(
        liquidacion=lcv_otro,
        inspector=inspector2,
        especialidad_revision=liquidacion_inspector.especialidad_revision,
    )

    # CIP del primer inspector + expediente del segundo inspector → 400
    from ninja.errors import HttpError
    with pytest.raises(HttpError) as excinfo:
        cotizar_flujo.cotizar(
            _payload(
                cip=perfil_ingeniero_inspector.cip,  # primer inspector
                periodo=2026, mes=1,
                items=[{"exp_liqui": lg_otro.expediente, "cantidad_visitas": 1}],
            )
        )
    assert excinfo.value.status_code == 400


@pytest.mark.django_db
def test_cotizar_excede_saldo_disponible(
    cotizar_flujo,
    inspector,
    perfil_ingeniero_inspector,
    liquidacion_inspector,
    liquidacion_visitas,
    liquidacion_general_io,
    escala_descuento_15,
):
    """
    Cotizar con cantidad_visitas > saldo disponible (10 programadas, 0 pagadas,
    solicitar 11) → HttpError 400.
    """
    from ninja.errors import HttpError

    with pytest.raises(HttpError) as excinfo:
        cotizar_flujo.cotizar(
            _payload(
                cip=perfil_ingeniero_inspector.cip,
                periodo=2026, mes=1,
                items=[{"exp_liqui": liquidacion_general_io.expediente, "cantidad_visitas": 11}],
            )
        )
    assert excinfo.value.status_code == 400
    assert "excede" in str(excinfo.value.message).lower()


@pytest.mark.django_db
def test_cotizar_expediente_no_existe(
    cotizar_flujo,
    inspector,
    perfil_ingeniero_inspector,
    escala_descuento_15,
):
    """
    Cotizar con expediente inexistente → HttpError 404.
    """
    from ninja.errors import HttpError

    with pytest.raises(HttpError) as excinfo:
        cotizar_flujo.cotizar(
            _payload(
                cip=perfil_ingeniero_inspector.cip,
                periodo=2026, mes=1,
                items=[{"exp_liqui": "EXP-INEXISTENTE", "cantidad_visitas": 1}],
            )
        )
    assert excinfo.value.status_code == 404


@pytest.mark.django_db
def test_crear_rh_inspector_mensual(
    crear_flujo,
    cotizar_flujo,
    inspector,
    perfil_ingeniero_inspector,
    liquidacion_inspector,
    liquidacion_visitas,
    liquidacion_general_io,
    escala_descuento_15,
):
    """
    RHInspectorMensualCrearFlujo.crear() crea:
    - ReciboHonorarioInspectorMensual
    - DetalleHonorarioInspector
    - RegistroPagoInspector

    Con sub_total=1000.00, visitas=10, cantidad_visitas=4:
        costo=100.00, monto_contribuido=400.00 → 15% → descuento 60.00, honorarios 340.00
    """
    result = crear_flujo.crear(
        _payload(
            cip=perfil_ingeniero_inspector.cip,
            periodo=2026, mes=1,
            items=[{
                "exp_liqui": liquidacion_general_io.expediente,
                "cantidad_visitas": 4,
                "periodo": 2027,
                "mes": 3,
            }],
        )
    )

    assert Decimal(str(result.totales.sub_total)) == Decimal("400.00")
    assert Decimal(str(result.totales.tasa_descuento_aplicada)) == Decimal("0.15")
    assert Decimal(str(result.totales.descuento)) == Decimal("60.00")
    assert Decimal(str(result.totales.honorarios)) == Decimal("340.00")
    assert result.items[0].liquidacion_inspector_id == str(liquidacion_inspector.id)
    assert result.items[0].periodo == 2027
    assert result.items[0].mes == 3

    # Verify BD records
    assert ReciboHonorarioInspectorMensual.objects.count() == 1
    rh = ReciboHonorarioInspectorMensual.objects.first()
    assert rh.inspector_id == inspector.id
    assert rh.periodo == 2026
    assert rh.mes == 1
    assert rh.sub_total == Decimal("400.00")
    assert rh.descuento == Decimal("60.00")
    assert rh.honorarios == Decimal("340.00")

    # Detalle
    assert rh.detalles.count() == 1
    detalle = rh.detalles.first()
    assert detalle.liquidacion_por_categoria_visitas_id == liquidacion_visitas.id
    assert detalle.inspecciones_liquidadas == 4
    assert detalle.costo_por_inspeccion == Decimal("100.00")
    assert detalle.monto_contribuido == Decimal("400.00")

    liquidacion_inspector.refresh_from_db()
    assert liquidacion_inspector.periodo == 2027
    assert liquidacion_inspector.mes == 3

    # RegistroPago
    registro = RegistroPagoInspector.objects.get(
        liquidacion_por_categoria_visitas=liquidacion_visitas,
        periodo=2026,
        mes=1,
    )
    assert registro.inspecciones_pagadas == 4


@pytest.mark.django_db
def test_crear_siempre_nuevo(
    crear_flujo,
    cotizar_flujo,
    inspector,
    perfil_ingeniero_inspector,
    liquidacion_inspector,
    liquidacion_visitas,
    liquidacion_general_io,
    escala_descuento_15,
):
    """
    Llamar crear 2 veces con el mismo (inspector, periodo) crea DOS RH headers —
    crear_rh_inspector_mensual siempre crea, nunca reutiliza.
    Los detalles del primer RH permanecen attached a ese primer header.
    """
    payload = _payload(
        cip=perfil_ingeniero_inspector.cip,
        periodo=2026, mes=1,
        items=[{"exp_liqui": liquidacion_general_io.expediente, "cantidad_visitas": 3}],
    )

    result1 = crear_flujo.crear(payload)
    assert result1.totales.sub_total == 300.0  # 100 * 3

    result2 = crear_flujo.crear(payload)
    assert result2.totales.sub_total == 300.0  # 100 * 3

    # Se crearon 2 RH mensuales distintos (siempre crea nuevo)
    assert ReciboHonorarioInspectorMensual.objects.count() == 2
    rh_list = list(ReciboHonorarioInspectorMensual.objects.order_by("fecha_registro"))
    assert rh_list[0].periodo == 2026
    assert rh_list[0].mes == 1
    assert rh_list[1].periodo == 2026
    assert rh_list[1].mes == 1

    # Cada RH tiene su propio detalle
    assert rh_list[0].detalles.count() == 1
    assert rh_list[1].detalles.count() == 1

    # Los detalles son de distintos receipts (no se mezclan)
    detalle1_lcv = rh_list[0].detalles.first().liquidacion_por_categoria_visitas_id
    detalle2_lcv = rh_list[1].detalles.first().liquidacion_por_categoria_visitas_id
    assert detalle1_lcv == detalle2_lcv  # Misma IO pero en distintos RH


@pytest.mark.django_db
def test_no_pagar_doble(
    crear_flujo,
    cotizar_flujo,
    inspector,
    perfil_ingeniero_inspector,
    liquidacion_inspector,
    liquidacion_visitas,
    liquidacion_general_io,
    escala_descuento_15,
):
    """
    Tras crear con 4 visitas, una nueva cotización del mismo periodo calcula
    saldo reducido (10 - 4 = 6 disponibles). Solicitar 7 → HttpError 400.
    """
    # Crear con 4 visitas
    crear_flujo.crear(
        _payload(
            cip=perfil_ingeniero_inspector.cip,
            periodo=2026, mes=1,
            items=[{"exp_liqui": liquidacion_general_io.expediente, "cantidad_visitas": 4}],
        )
    )

    # El saldo ahora es 6 (10 - 4 pagadas)
    registro = RegistroPagoInspector.objects.get(
        liquidacion_por_categoria_visitas=liquidacion_visitas,
        periodo=2026,
        mes=1,
    )
    assert registro.inspecciones_pagadas == 4

    # Cotizar con 7 visitas (excede el saldo de 6) → 400
    from ninja.errors import HttpError
    with pytest.raises(HttpError) as excinfo:
        cotizar_flujo.cotizar(
            _payload(
                cip=perfil_ingeniero_inspector.cip,
                periodo=2026, mes=1,
                items=[{"exp_liqui": liquidacion_general_io.expediente, "cantidad_visitas": 7}],
            )
        )
    assert excinfo.value.status_code == 400

    # Cotizar con 6 visitas (exactamente el saldo) → OK
    result = cotizar_flujo.cotizar(
        _payload(
            cip=perfil_ingeniero_inspector.cip,
            periodo=2026, mes=1,
            items=[{"exp_liqui": liquidacion_general_io.expediente, "cantidad_visitas": 6}],
        )
    )
    assert result.items[0].saldo_restante == 0  # 10 - 4 (pagadas) - 6 (this quote) = 0


@pytest.mark.django_db
def test_cotizar_con_multiple_items_diferentes(
    cotizar_flujo,
    inspector,
    perfil_ingeniero_inspector,
    escala_descuento_15,
    tipo_inspeccion_obra,
    proyecto_test,
    municipalidad_test,
    usuario_liquidacion,
    tarifa_visitas_io,
    liquidacion_inspector,
):
    """
    Cotizar con 2 items de distinta LiquidacionGeneral:
    - Item 1: sub_total=1000, 4 visitas → costo=100, monto=400
    - Item 2: sub_total=5000, 2 visitas → costo=500, monto=1000
    sub_total agrupado = 1400 → rango 15% → descuento=210, honorarios=1190
    """
    # Crear segunda LiquidacionGeneral + LiquidacionPorCategoriaVisitas + LiquidacionInspector
    proyecto_2 = Proyecto.objects.create(
        nombre_propietario="Propietario IO 2 SAC",
        direccion="Av. Test 456",
        distrito=proyecto_test.distrito,
        entidad_tipo_documento="RUC",
        entidad_numero_documento="20456789013",
        entidad_razon_social="Propietario IO 2 SAC",
    )
    lg2 = LiquidacionGeneral.objects.create(
        proyecto=proyecto_2,
        municipalidad=municipalidad_test,
        tipo_liquidacion=tipo_inspeccion_obra,
        usuario_creador=usuario_liquidacion,
        expediente="EXP-MENSUAL-002",
        estado="REGISTRADO",
        sub_total=Decimal("5000.00"),
        total=Decimal("5900.00"),
    )
    lcv2 = LiquidacionPorCategoriaVisitas.objects.create(
        liquidacion_general=lg2,
        cantidad_visitas=10,
        porcentaje_uit=Decimal("0.05"),
        categoria="A",
        tarifa_aplicada=tarifa_visitas_io,
    )
    # Asociar la segunda IO al inspector usando la especialidad de liquidacion_inspector
    LiquidacionInspector.objects.create(
        liquidacion=lcv2,
        inspector=inspector,
        especialidad_revision=liquidacion_inspector.especialidad_revision,
    )

    result = cotizar_flujo.cotizar(
        _payload(
            cip=perfil_ingeniero_inspector.cip,
            periodo=2026, mes=2,
            items=[
                {"exp_liqui": "EXP-MENSUAL-001", "cantidad_visitas": 4},
                {"exp_liqui": "EXP-MENSUAL-002", "cantidad_visitas": 2},
            ],
        )
    )

    # Item 1: costo=100.00, monto=400.00
    item1 = next(i for i in result.items if i.exp_liqui == "EXP-MENSUAL-001")
    assert Decimal(str(item1.costo_por_inspeccion)) == Decimal("100.00")
    assert Decimal(str(item1.monto_contribuido)) == Decimal("400.00")

    # Item 2: costo=500.00, monto=1000.00
    item2 = next(i for i in result.items if i.exp_liqui == "EXP-MENSUAL-002")
    assert Decimal(str(item2.costo_por_inspeccion)) == Decimal("500.00")
    assert Decimal(str(item2.monto_contribuido)) == Decimal("1000.00")

    # Totales: sub_total=1400 → 15% → descuento=210, honorarios=1190
    assert Decimal(str(result.totales.sub_total)) == Decimal("1400.00")
    assert Decimal(str(result.totales.tasa_descuento_aplicada)) == Decimal("0.15")
    assert Decimal(str(result.totales.descuento)) == Decimal("210.00")
    assert Decimal(str(result.totales.honorarios)) == Decimal("1190.00")


@pytest.mark.django_db
def test_cotizar_liquidacion_no_es_io(
    cotizar_flujo,
    inspector,
    perfil_ingeniero_inspector,
    escala_descuento_15,
    tipo_inspeccion_obra,
    proyecto_test,
    municipalidad_test,
    usuario_liquidacion,
):
    """
    Cotizar con una LiquidacionGeneral que no es de tipo INSPECCION_OBRA → 404.
    """
    from modules.liquidaciones.domain.models.tipo_liquidacion import TipoLiquidacion as TL
    from ninja.errors import HttpError

    tipo_otro = TL.objects.get_or_create(
        codigo="EDIFICACION", defaults={"nombre": "Edificaciones"}
    )[0]

    lg_otro = LiquidacionGeneral.objects.create(
        proyecto=proyecto_test,
        municipalidad=municipalidad_test,
        tipo_liquidacion=tipo_otro,
        usuario_creador=usuario_liquidacion,
        expediente="EXP-NO-IO",
        estado="REGISTRADO",
        sub_total=Decimal("5000.00"),
        total=Decimal("5900.00"),
    )

    with pytest.raises(HttpError) as excinfo:
        cotizar_flujo.cotizar(
            _payload(
                cip=perfil_ingeniero_inspector.cip,
                periodo=2026, mes=1,
                items=[{"exp_liqui": lg_otro.expediente, "cantidad_visitas": 1}],
            )
        )
    assert excinfo.value.status_code == 404


@pytest.mark.django_db
def test_crear_registra_pagos_independientes_mismo_mes(
    crear_flujo,
    cotizar_flujo,
    inspector,
    perfil_ingeniero_inspector,
    liquidacion_inspector,
    liquidacion_visitas,
    liquidacion_general_io,
    escala_descuento_15,
):
    """
    Crear dos veces con distintos items del mismo periodo crea registros de pago
    independientes para cada RH.
    Los detalles se attachan a cada RH nuevo, no se mezclan.
    """
    # Primera creación: 3 visitas
    crear_flujo.crear(
        _payload(
            cip=perfil_ingeniero_inspector.cip,
            periodo=2026, mes=3,
            items=[{"exp_liqui": liquidacion_general_io.expediente, "cantidad_visitas": 3}],
        )
    )

    # Segunda creación: 2 visitas más del mismo período
    crear_flujo.crear(
        _payload(
            cip=perfil_ingeniero_inspector.cip,
            periodo=2026, mes=3,
            items=[{"exp_liqui": liquidacion_general_io.expediente, "cantidad_visitas": 2}],
        )
    )

    # Dos RegistroPagoInspector independientes en el mismo mes.
    registros = list(RegistroPagoInspector.objects.filter(
        liquidacion_por_categoria_visitas=liquidacion_visitas,
        periodo=2026,
        mes=3,
    ).order_by("created_at"))
    assert len(registros) == 2
    assert [r.inspecciones_pagadas for r in registros] == [3, 2]
    assert sum(r.inspecciones_pagadas for r in registros) == 5

    # Dos RH mensuales distintos (siempre crea nuevo)
    assert ReciboHonorarioInspectorMensual.objects.filter(periodo=2026, mes=3).count() == 2
    rh_list = list(ReciboHonorarioInspectorMensual.objects.filter(periodo=2026, mes=3).order_by("fecha_registro"))
    # Cada RH tiene su propio detalle (no se mezclan)
    assert rh_list[0].detalles.count() == 1
    assert rh_list[1].detalles.count() == 1


# ── Inspector Candidatas Tests ────────────────────────────────────────────────────

@pytest.mark.django_db
def test_list_candidatas_inspector_returns_candidatas_con_saldo(
    db,
    inspector,
    perfil_ingeniero_inspector,
    liquidacion_inspector,
    liquidacion_visitas,
    liquidacion_general_io,
    escala_descuento_15,
):
    """
    El candidates endpoint retorna las IOs con saldo_disponible > 0.
    """
    from modules.finanzas.domain.services.finanzas_core_service import FinanzasCoreService
    from modules.finanzas.domain.services.finanzas_orchestrator import FinanzasOrchestrator

    core = FinanzasCoreService()
    orchestrator = FinanzasOrchestrator(
        flujo=None,
        core=core,
        rh_mensual_cotizar_flujo=None,
        rh_mensual_crear_flujo=None,
        rh_delegado_mensual_cotizar_flujo=None,
        rh_delegado_mensual_crear_flujo=None,
    )

    result = orchestrator.list_candidatos_inspector_proceso(
        cip=perfil_ingeniero_inspector.cip,
        periodo="2026-01",
    )

    assert result.total == 1
    assert result.inspector_cip == perfil_ingeniero_inspector.cip
    candidata = result.candidatos[0]
    assert candidata.expediente == liquidacion_general_io.expediente
    assert candidata.cantidad_visitas == liquidacion_visitas.cantidad_visitas
    assert candidata.inspecciones_pagadas == 0
    assert candidata.saldo_disponible == liquidacion_visitas.cantidad_visitas
    assert candidata.liquidacion_inspector_id == str(liquidacion_inspector.id)
    assert candidata.liquidacion_categoria_visitas_id == str(liquidacion_visitas.id)
    # Decimal precision assertions — financial fields must preserve precision
    assert Decimal(str(candidata.costo_por_inspeccion)) == Decimal("100.00")
    assert Decimal(str(candidata.total_liquidacion)) == Decimal("1000.00")
    assert Decimal(str(candidata.sub_total_liquidacion)) == Decimal("1000.00")


@pytest.mark.django_db
def test_list_candidatas_inspector_404_cip_no_existe(
    db,
    escala_descuento_15,
):
    """
    Candidates endpoint con CIP inexistente → 404.
    """
    from modules.finanzas.domain.services.finanzas_core_service import FinanzasCoreService
    from modules.finanzas.domain.services.finanzas_orchestrator import FinanzasOrchestrator
    from ninja.errors import HttpError

    core = FinanzasCoreService()
    orchestrator = FinanzasOrchestrator(
        flujo=None,
        core=core,
        rh_mensual_cotizar_flujo=None,
        rh_mensual_crear_flujo=None,
        rh_delegado_mensual_cotizar_flujo=None,
        rh_delegado_mensual_crear_flujo=None,
    )

    with pytest.raises(HttpError) as excinfo:
        orchestrator.list_candidatos_inspector_proceso(
            cip="CIP-INEXISTENTE",
            periodo="2026-01",
        )
    assert excinfo.value.status_code == 404


@pytest.mark.django_db
def test_list_candidatas_inspector_saldo_excedido_no_retorna(
    db,
    inspector,
    perfil_ingeniero_inspector,
    liquidacion_inspector,
    liquidacion_visitas,
    liquidacion_general_io,
    escala_descuento_15,
):
    """
    Cuando saldo_disponible = 0 (todas las visitas pagadas), no se retorna como candidata.
    """
    from modules.finanzas.domain.models.registro_pago_inspector import RegistroPagoInspector
    from modules.finanzas.domain.services.finanzas_core_service import FinanzasCoreService
    from modules.finanzas.domain.services.finanzas_orchestrator import FinanzasOrchestrator

    # Simular que ya se pagaron todas las visitas
    RegistroPagoInspector.objects.create(
        liquidacion_por_categoria_visitas=liquidacion_visitas,
        periodo=2026,
        mes=1,
        inspecciones_pagadas=liquidacion_visitas.cantidad_visitas,
    )

    core = FinanzasCoreService()
    orchestrator = FinanzasOrchestrator(
        flujo=None,
        core=core,
        rh_mensual_cotizar_flujo=None,
        rh_mensual_crear_flujo=None,
        rh_delegado_mensual_cotizar_flujo=None,
        rh_delegado_mensual_crear_flujo=None,
    )

    result = orchestrator.list_candidatos_inspector_proceso(
        cip=perfil_ingeniero_inspector.cip,
        periodo="2026-01",
    )

    assert result.total == 0


@pytest.mark.django_db
def test_cotizar_con_liquidacion_categoria_visitas_id(
    cotizar_flujo,
    inspector,
    perfil_ingeniero_inspector,
    liquidacion_inspector,
    liquidacion_visitas,
    liquidacion_general_io,
    escala_descuento_15,
):
    """
    Cotizar usando liquidacion_categoria_visitas_id (flujo por candidatas) en lugar de exp_liqui.
    """
    from modules.finanzas.domain.schemas import RHInspectorCotizarIn, RHInspectorCotizarItemIn

    payload = RHInspectorCotizarIn(
        cip=perfil_ingeniero_inspector.cip,
        periodo=2026,
        mes=1,
        items=[
            RHInspectorCotizarItemIn(
                liquidacion_categoria_visitas_id=str(liquidacion_visitas.id),
                cantidad_visitas=3,
            )
        ],
    )

    result = cotizar_flujo.cotizar(payload)

    assert len(result.items) == 1
    item = result.items[0]
    assert item.exp_liqui == liquidacion_general_io.expediente
    assert item.liquidacion_inspector_id == str(liquidacion_inspector.id)
    assert item.liquidacion_categoria_visitas_id == str(liquidacion_visitas.id)
    assert item.inspecciones_liquidadas == 3


@pytest.mark.django_db
def test_cotizar_result_tiene_liquidacion_inspector_id(
    cotizar_flujo,
    inspector,
    perfil_ingeniero_inspector,
    liquidacion_inspector,
    liquidacion_visitas,
    liquidacion_general_io,
    escala_descuento_15,
):
    """
    El resultado de cotizar incluye liquidacion_inspector_id en cada item.
    """
    from modules.finanzas.domain.schemas import RHInspectorCotizarIn, RHInspectorCotizarItemIn

    payload = RHInspectorCotizarIn(
        cip=perfil_ingeniero_inspector.cip,
        periodo=2026,
        mes=1,
        items=[
            RHInspectorCotizarItemIn(
                exp_liqui=liquidacion_general_io.expediente,
                cantidad_visitas=2,
            )
        ],
    )

    result = cotizar_flujo.cotizar(payload)

    assert len(result.items) == 1
    item = result.items[0]
    assert item.liquidacion_inspector_id == str(liquidacion_inspector.id)
    assert item.liquidacion_categoria_visitas_id == str(liquidacion_visitas.id)


# ── RH Inspector Candidatas Paginated Tests ────────────────────────────────────


@pytest.fixture
def rh_inspector_mensual_flujo():
    from modules.finanzas.domain.services.flujos.rh_inspector_mensual_flujo import RHInspectorMensualListFlujo
    from modules.finanzas.domain.services.finanzas_core_service import FinanzasCoreService
    core = FinanzasCoreService()
    return RHInspectorMensualListFlujo(core=core)


@pytest.mark.django_db
def test_listar_candidatas_paginated_returns_correct_structure(
    rh_inspector_mensual_flujo,
    inspector,
    perfil_ingeniero_inspector,
    liquidacion_inspector,
    liquidacion_visitas,
    liquidacion_general_io,
):
    """
    The paginated candidatas endpoint returns InspectorCandidatosPaginatedResult
    with items/total/page/page_size/total_pages.
    """
    result = rh_inspector_mensual_flujo.list_candidatos_inspector_proceso_paginated(
        cip=perfil_ingeniero_inspector.cip,
        page=1,
        page_size=10,
    )

    assert hasattr(result, "items")
    assert hasattr(result, "total")
    assert hasattr(result, "page")
    assert hasattr(result, "page_size")
    assert hasattr(result, "total_pages")
    assert isinstance(result.items, list)
    assert result.page == 1
    assert result.page_size == 10


@pytest.mark.django_db
def test_listar_candidatas_paginated_filters_by_expediente(
    rh_inspector_mensual_flujo,
    inspector,
    perfil_ingeniero_inspector,
    liquidacion_inspector,
    liquidacion_visitas,
    liquidacion_general_io,
):
    """
    expediente filter applies icontains on LiquidacionGeneral.expediente.
    """
    # Matching filter
    result_match = rh_inspector_mensual_flujo.list_candidatos_inspector_proceso_paginated(
        cip=perfil_ingeniero_inspector.cip,
        page=1,
        page_size=10,
        expediente="EXP-MENSUAL",
    )
    assert result_match.total >= 1

    # Non-matching filter
    result_none = rh_inspector_mensual_flujo.list_candidatos_inspector_proceso_paginated(
        cip=perfil_ingeniero_inspector.cip,
        page=1,
        page_size=10,
        expediente="NON-EXISTENT",
    )
    assert result_none.total == 0


@pytest.mark.django_db
def test_listar_candidatas_paginated_filters_by_numero(
    rh_inspector_mensual_flujo,
    inspector,
    perfil_ingeniero_inspector,
    liquidacion_inspector,
    liquidacion_visitas,
    liquidacion_general_io,
):
    """
    numero filter applies exact match on LiquidacionPorCategoriaVisitas.numero.
    """
    # Non-matching numero
    result_none = rh_inspector_mensual_flujo.list_candidatos_inspector_proceso_paginated(
        cip=perfil_ingeniero_inspector.cip,
        page=1,
        page_size=10,
        numero=99999,
    )
    assert result_none.total == 0


@pytest.mark.django_db
def test_listar_candidatas_paginated_filters_by_propietario(
    rh_inspector_mensual_flujo,
    inspector,
    perfil_ingeniero_inspector,
    liquidacion_inspector,
    liquidacion_visitas,
    liquidacion_general_io,
):
    """
    propietario filter applies icontains on proyecto.nombre_propietario.
    """
    # Matching filter
    result_match = rh_inspector_mensual_flujo.list_candidatos_inspector_proceso_paginated(
        cip=perfil_ingeniero_inspector.cip,
        page=1,
        page_size=10,
        propietario="Propietario",
    )
    assert result_match.total >= 1

    # Non-matching filter
    result_none = rh_inspector_mensual_flujo.list_candidatos_inspector_proceso_paginated(
        cip=perfil_ingeniero_inspector.cip,
        page=1,
        page_size=10,
        propietario="NONEXISTENTOWNER",
    )
    assert result_none.total == 0


@pytest.mark.django_db
def test_listar_candidatas_paginated_filters_by_direccion(
    rh_inspector_mensual_flujo,
    inspector,
    perfil_ingeniero_inspector,
    liquidacion_inspector,
    liquidacion_visitas,
    liquidacion_general_io,
):
    """
    direccion filter applies icontains on proyecto.direccion.
    """
    # Matching filter
    result_match = rh_inspector_mensual_flujo.list_candidatos_inspector_proceso_paginated(
        cip=perfil_ingeniero_inspector.cip,
        page=1,
        page_size=10,
        direccion="Av. Test",
    )
    assert result_match.total >= 1

    # Non-matching filter
    result_none = rh_inspector_mensual_flujo.list_candidatos_inspector_proceso_paginated(
        cip=perfil_ingeniero_inspector.cip,
        page=1,
        page_size=10,
        direccion="Calle Inexistente 999",
    )
    assert result_none.total == 0


@pytest.mark.django_db
def test_listar_candidatas_paginated_saldo_in_item(
    rh_inspector_mensual_flujo,
    inspector,
    perfil_ingeniero_inspector,
    liquidacion_inspector,
    liquidacion_visitas,
    liquidacion_general_io,
):
    """
    Each item in paginated result includes saldo_disponible computed from
    LiquidacionPorCategoriaVisitas.cantidad_visitas minus RegistroPagoInspector.
    """
    result = rh_inspector_mensual_flujo.list_candidatos_inspector_proceso_paginated(
        cip=perfil_ingeniero_inspector.cip,
        page=1,
        page_size=10,
    )

    assert result.total >= 1
    item = result.items[0]
    assert hasattr(item, "saldo_disponible")
    assert item.saldo_disponible == liquidacion_visitas.cantidad_visitas  # 10 - 0 = 10


@pytest.mark.django_db
def test_listar_candidatas_paginated_page_size_respected(
    rh_inspector_mensual_flujo,
    inspector,
    perfil_ingeniero_inspector,
    liquidacion_inspector,
    liquidacion_visitas,
    liquidacion_general_io,
):
    """
    page_size=1 returns at most 1 item per page.
    """
    result = rh_inspector_mensual_flujo.list_candidatos_inspector_proceso_paginated(
        cip=perfil_ingeniero_inspector.cip,
        page=1,
        page_size=1,
    )

    assert len(result.items) <= 1
    assert result.total_pages >= 1


@pytest.mark.django_db
def test_listar_candidatas_paginated_cip_invalido_raises_404(
    rh_inspector_mensual_flujo,
):
    """
    CIP que no existe lanza HttpError 404.
    """
    from ninja.errors import HttpError

    with pytest.raises(HttpError) as excinfo:
        rh_inspector_mensual_flujo.list_candidatos_inspector_proceso_paginated(
            cip="CIP-INEXISTENTE",
            page=1,
            page_size=10,
        )
    assert excinfo.value.status_code == 404


# ── Tests para recibo_mensual nullable ──────────────────────────────────────

@pytest.mark.django_db
def test_crear_detalle_honorario_inspector_recibo_mensual_none_valido(
    db,
    liquidacion_visitas,
    escala_descuento_15,
):
    """
    GIVEN: Un DetalleHonorarioInspector puede crearse con recibo_mensual=None.
    WHEN: Se crea un detalle sin FK al recibo mensual.
    THEN: El detalle se guarda en BD correctamente.
    """
    detalle = DetalleHonorarioInspector.objects.create(
        recibo_mensual=None,
        liquidacion_por_categoria_visitas=liquidacion_visitas,
        inspecciones_liquidadas=2,
        costo_por_inspeccion=Decimal("100.00"),
        monto_contribuido=Decimal("200.00"),
    )
    detalle.refresh_from_db()
    assert detalle.pk is not None
    assert detalle.recibo_mensual is None


@pytest.mark.django_db
def test_list_rh_mensuales_inspectores_excluye_detalles_sin_recibo(
    crear_flujo,
    cotizar_flujo,
    inspector,
    perfil_ingeniero_inspector,
    liquidacion_inspector,
    liquidacion_visitas,
    liquidacion_general_io,
    escala_descuento_15,
    core_service,
):
    """
    GIVEN: Un RH Inspector Mensual con detalles + un detalle huerfano (recibo_mensual=None).
    WHEN: Se lista los RH mensuales con list_rh_mensuales_inspectores_paginated.
    THEN: Los detalles huerfanos NO aparecen en los resultados.
    """
    # Crear RH mensual normal con detalle
    result = crear_flujo.crear(
        _payload(
            cip=perfil_ingeniero_inspector.cip,
            periodo=2026, mes=1,
            items=[{
                "exp_liqui": liquidacion_general_io.expediente,
                "cantidad_visitas": 4,
                "periodo": 2027,
                "mes": 3,
            }],
        )
    )
    rh = ReciboHonorarioInspectorMensual.objects.first()
    assert rh.detalles.count() == 1

    # Crear detalle huerfano (sin recibo_mensual)
    DetalleHonorarioInspector.objects.create(
        recibo_mensual=None,
        liquidacion_por_categoria_visitas=liquidacion_visitas,
        inspecciones_liquidadas=1,
        costo_por_inspeccion=Decimal("100.00"),
        monto_contribuido=Decimal("100.00"),
    )

    # Listar RH mensuales
    objects, total = core_service.list_rh_mensuales_inspectores_paginated(
        page=1, page_size=10, inspector_id=inspector.id
    )

    # Verificar que el RH tiene exactamente 1 detalle (el huerfano NO aparece)
    assert len(objects) == 1
    assert objects[0].detalles.count() == 1


@pytest.mark.django_db
def test_borrar_recibo_inspector_cascada_deja_detalles_nulos(
    crear_flujo,
    cotizar_flujo,
    inspector,
    perfil_ingeniero_inspector,
    liquidacion_inspector,
    liquidacion_visitas,
    liquidacion_general_io,
    escala_descuento_15,
):
    """
    GIVEN: Un RH Inspector con detalles + un detalle huerfano (recibo_mensual=None).
    WHEN: Se elimina el RH mensual.
    THEN: Los detalles vinculados al RH se borran en cascada, el detalle huerfano sobrevive.
    """
    # Crear RH mensual con detalle usando el flujo
    result = crear_flujo.crear(
        _payload(
            cip=perfil_ingeniero_inspector.cip,
            periodo=2026, mes=1,
            items=[{
                "exp_liqui": liquidacion_general_io.expediente,
                "cantidad_visitas": 4,
                "periodo": 2027,
                "mes": 3,
            }],
        )
    )
    rh = ReciboHonorarioInspectorMensual.objects.first()
    detalle_vinculado = rh.detalles.first()

    # Crear detalle huerfano (sin recibo_mensual)
    detalle_huerfano = DetalleHonorarioInspector.objects.create(
        recibo_mensual=None,
        liquidacion_por_categoria_visitas=liquidacion_visitas,
        inspecciones_liquidadas=1,
        costo_por_inspeccion=Decimal("100.00"),
        monto_contribuido=Decimal("100.00"),
    )

    detalle_vinculado_id = detalle_vinculado.id
    detalle_huerfano_id = detalle_huerfano.id

    # Eliminar el RH
    rh.delete()

    # El detalle vinculado se borra en cascada
    assert not DetalleHonorarioInspector.objects.filter(id=detalle_vinculado_id).exists()

    # El detalle huerfano sobrevive
    assert DetalleHonorarioInspector.objects.filter(id=detalle_huerfano_id).exists()


@pytest.mark.django_db
def test_get_rh_inspector_mensual_by_id_excluye_detalles_sin_recibo(
    crear_flujo,
    cotizar_flujo,
    inspector,
    perfil_ingeniero_inspector,
    liquidacion_inspector,
    liquidacion_visitas,
    liquidacion_general_io,
    escala_descuento_15,
    core_service,
):
    """
    GIVEN: Un RH Inspector Mensual con detalles + un detalle huerfano.
    WHEN: Se obtiene el RH por ID con get_rh_inspector_mensual_by_id.
    THEN: Solo los detalles vinculados al RH aparecen, los huerfanos no.
    """
    # Crear RH mensual
    result = crear_flujo.crear(
        _payload(
            cip=perfil_ingeniero_inspector.cip,
            periodo=2026, mes=1,
            items=[{
                "exp_liqui": liquidacion_general_io.expediente,
                "cantidad_visitas": 4,
                "periodo": 2027,
                "mes": 3,
            }],
        )
    )
    rh = ReciboHonorarioInspectorMensual.objects.first()

    # Crear detalle huerfano
    DetalleHonorarioInspector.objects.create(
        recibo_mensual=None,
        liquidacion_por_categoria_visitas=liquidacion_visitas,
        inspecciones_liquidadas=1,
        costo_por_inspeccion=Decimal("100.00"),
        monto_contribuido=Decimal("100.00"),
    )

    # Obtener RH por ID
    rh_obtained = core_service.get_rh_inspector_mensual_by_id(rh.id)

    # Verificar que solo tiene el detalle vinculado, no el huerfano
    assert rh_obtained is not None
    assert rh_obtained.detalles.count() == 1


@pytest.mark.django_db
def test_normal_creacion_rh_inspector_fk_establecido(
    crear_flujo,
    cotizar_flujo,
    inspector,
    perfil_ingeniero_inspector,
    liquidacion_inspector,
    liquidacion_visitas,
    liquidacion_general_io,
    escala_descuento_15,
):
    """
    GIVEN: Flujo normal de creacion de RH Inspector.
    WHEN: Se crea un RH mensual via crear_flujo.
    THEN: El detalle tiene FK recibo_mensual establecido (no null).
    """
    result = crear_flujo.crear(
        _payload(
            cip=perfil_ingeniero_inspector.cip,
            periodo=2026, mes=1,
            items=[{
                "exp_liqui": liquidacion_general_io.expediente,
                "cantidad_visitas": 4,
                "periodo": 2027,
                "mes": 3,
            }],
        )
    )

    rh = ReciboHonorarioInspectorMensual.objects.first()
    detalle = rh.detalles.first()

    # Verificar que el FK no es null
    assert detalle.recibo_mensual is not None
    assert detalle.recibo_mensual_id == rh.id


# ── Delete Tests ──────────────────────────────────────────────────────────────────

@pytest.fixture
def delete_flujo(core_service):
    return RHInspectorMensualDeleteFlujo(core=core_service)


@pytest.mark.django_db
def test_delete_latest_rh_inspector_returns_200(
    crear_flujo,
    cotizar_flujo,
    delete_flujo,
    inspector,
    perfil_ingeniero_inspector,
    liquidacion_inspector,
    liquidacion_visitas,
    liquidacion_general_io,
    escala_descuento_15,
):
    """
    GIVEN: Un RH Inspector Mensual recién creado (es el latest por fecha_registro).
    WHEN: Se elimina via delete_flujo.eliminar().
    THEN: Retorna sin excepción (200 equivalent) y el RH es borrado de BD.
    """
    # Crear RH (vínculo recibo_mensual establecido)
    crear_flujo.crear(
        _payload(
            cip=perfil_ingeniero_inspector.cip,
            periodo=2026, mes=1,
            items=[{
                "exp_liqui": liquidacion_general_io.expediente,
                "cantidad_visitas": 4,
                "periodo": 2027,
                "mes": 3,
            }],
        )
    )
    rh = ReciboHonorarioInspectorMensual.objects.first()
    assert rh is not None

    # Eliminar — no debe lanzar excepción
    delete_flujo.eliminar(rh.id)

    # RH borrado de BD
    assert not ReciboHonorarioInspectorMensual.objects.filter(id=rh.id).exists()


@pytest.mark.django_db
def test_delete_latest_rh_deletes_recibo_honorario_inspector_mensual(
    crear_flujo,
    cotizar_flujo,
    delete_flujo,
    inspector,
    perfil_ingeniero_inspector,
    liquidacion_inspector,
    liquidacion_visitas,
    liquidacion_general_io,
    escala_descuento_15,
):
    """
    GIVEN: Un RH Inspector Mensual.
    WHEN: Se elimina.
    THEN: ReciboHonorarioInspectorMensual es eliminado de BD.
    """
    crear_flujo.crear(
        _payload(
            cip=perfil_ingeniero_inspector.cip,
            periodo=2026, mes=1,
            items=[{
                "exp_liqui": liquidacion_general_io.expediente,
                "cantidad_visitas": 4,
                "periodo": 2027,
                "mes": 3,
            }],
        )
    )
    rh = ReciboHonorarioInspectorMensual.objects.first()
    rh_id = rh.id

    delete_flujo.eliminar(rh_id)

    assert ReciboHonorarioInspectorMensual.objects.filter(id=rh_id).count() == 0


@pytest.mark.django_db
def test_delete_latest_rh_cascades_to_detalle_honorario_inspector(
    crear_flujo,
    cotizar_flujo,
    delete_flujo,
    inspector,
    perfil_ingeniero_inspector,
    liquidacion_inspector,
    liquidacion_visitas,
    liquidacion_general_io,
    escala_descuento_15,
):
    """
    GIVEN: Un RH Inspector Mensual con DetalleHonorarioInspector.
    WHEN: Se elimina el RH.
    THEN: DetalleHonorarioInspector es eliminado en cascada por Django.
    """
    crear_flujo.crear(
        _payload(
            cip=perfil_ingeniero_inspector.cip,
            periodo=2026, mes=1,
            items=[{
                "exp_liqui": liquidacion_general_io.expediente,
                "cantidad_visitas": 4,
                "periodo": 2027,
                "mes": 3,
            }],
        )
    )
    rh = ReciboHonorarioInspectorMensual.objects.first()
    detalle_ids = list(rh.detalles.values_list("id", flat=True))
    assert len(detalle_ids) > 0

    delete_flujo.eliminar(rh.id)

    assert DetalleHonorarioInspector.objects.filter(id__in=detalle_ids).count() == 0


@pytest.mark.django_db
def test_delete_latest_rh_deletes_linked_registro_pago_inspector(
    crear_flujo,
    cotizar_flujo,
    delete_flujo,
    inspector,
    perfil_ingeniero_inspector,
    liquidacion_inspector,
    liquidacion_visitas,
    liquidacion_general_io,
    escala_descuento_15,
):
    """
    GIVEN: Un RH Inspector Mensual con RegistroPagoInspector vinculado (recibo_mensual_id set).
    WHEN: Se elimina el RH.
    THEN: El RegistroPagoInspector vinculado es eliminado.
    """
    crear_flujo.crear(
        _payload(
            cip=perfil_ingeniero_inspector.cip,
            periodo=2026, mes=1,
            items=[{
                "exp_liqui": liquidacion_general_io.expediente,
                "cantidad_visitas": 4,
                "periodo": 2027,
                "mes": 3,
            }],
        )
    )
    rh = ReciboHonorarioInspectorMensual.objects.first()

    # Verificar que existe un RegistroPagoInspector vinculado
    registro_ids = list(RegistroPagoInspector.objects.filter(
        liquidacion_por_categoria_visitas=liquidacion_visitas,
        periodo=2026,
        mes=1,
    ).values_list("id", flat=True))
    assert len(registro_ids) > 0

    delete_flujo.eliminar(rh.id)

    # Los Registros de Pago vinculados fueron eliminados
    assert RegistroPagoInspector.objects.filter(id__in=registro_ids).count() == 0


@pytest.mark.django_db
def test_delete_preserves_null_fk_legacy_registro_pago_inspector(
    crear_flujo,
    cotizar_flujo,
    delete_flujo,
    inspector,
    perfil_ingeniero_inspector,
    liquidacion_inspector,
    liquidacion_visitas,
    liquidacion_general_io,
    escala_descuento_15,
):
    """
    GIVEN: Un RegistroPagoInspector legacy con recibo_mensual=null.
    WHEN: Se elimina el RH.
    THEN: El RegistroPagoInspector legacy sobrevive (no es tocado).
    """
    crear_flujo.crear(
        _payload(
            cip=perfil_ingeniero_inspector.cip,
            periodo=2026, mes=1,
            items=[{
                "exp_liqui": liquidacion_general_io.expediente,
                "cantidad_visitas": 4,
                "periodo": 2027,
                "mes": 3,
            }],
        )
    )
    rh = ReciboHonorarioInspectorMensual.objects.first()

    # Crear un RegistroPagoInspector legacy (sin vínculo a recibo_mensual)
    legacy_registro = RegistroPagoInspector.objects.create(
        liquidacion_por_categoria_visitas=liquidacion_visitas,
        periodo=2025,
        mes=12,
        inspecciones_pagadas=2,
        # recibo_mensual=None (default)
    )
    legacy_registro_id = legacy_registro.id

    delete_flujo.eliminar(rh.id)

    # El registro legacy sobrevive
    assert RegistroPagoInspector.objects.filter(id=legacy_registro_id).exists()


@pytest.mark.django_db
def test_delete_non_latest_rh_returns_conflict(
    crear_flujo,
    cotizar_flujo,
    delete_flujo,
    inspector,
    perfil_ingeniero_inspector,
    liquidacion_inspector,
    liquidacion_visitas,
    liquidacion_general_io,
    escala_descuento_15,
):
    """
    GIVEN: Dos RH Inspector Mensuales (mes 1 y mes 2).
    WHEN: Se intenta eliminar el RH más antiguo (no el latest).
    THEN: HttpError 409 — solo se puede eliminar el último.
    """
    from ninja.errors import HttpError

    # Crear RH de mes 1
    crear_flujo.crear(
        _payload(
            cip=perfil_ingeniero_inspector.cip,
            periodo=2026, mes=1,
            items=[{
                "exp_liqui": liquidacion_general_io.expediente,
                "cantidad_visitas": 4,
                "periodo": 2027,
                "mes": 3,
            }],
        )
    )
    rh_mes1 = ReciboHonorarioInspectorMensual.objects.filter(mes=1).first()

    # Crear RH de mes 2 (será el latest)
    crear_flujo.crear(
        _payload(
            cip=perfil_ingeniero_inspector.cip,
            periodo=2026, mes=2,
            items=[{
                "exp_liqui": liquidacion_general_io.expediente,
                "cantidad_visitas": 3,
                "periodo": 2027,
                "mes": 4,
            }],
        )
    )

    # Intentar eliminar mes 1 (no es el latest) → 409
    with pytest.raises(HttpError) as excinfo:
        delete_flujo.eliminar(rh_mes1.id)
    assert excinfo.value.status_code == 409


@pytest.mark.django_db
def test_delete_non_latest_rh_no_modifica_estado(
    crear_flujo,
    cotizar_flujo,
    delete_flujo,
    inspector,
    perfil_ingeniero_inspector,
    liquidacion_inspector,
    liquidacion_visitas,
    liquidacion_general_io,
    escala_descuento_15,
):
    """
    GIVEN: Dos RH Inspector Mensuales (mes 1 y mes 2) con su ledger y marcador.
    WHEN: Se intenta eliminar el RH no latest.
    THEN: 409 y ningún estado cambia (RH, ledger ni marcador de periodo).
    """
    from ninja.errors import HttpError

    crear_flujo.crear(
        _payload(
            cip=perfil_ingeniero_inspector.cip,
            periodo=2026, mes=1,
            items=[{
                "exp_liqui": liquidacion_general_io.expediente,
                "cantidad_visitas": 4,
                "periodo": 2027,
                "mes": 3,
            }],
        )
    )
    rh_mes1 = ReciboHonorarioInspectorMensual.objects.filter(mes=1).first()

    crear_flujo.crear(
        _payload(
            cip=perfil_ingeniero_inspector.cip,
            periodo=2026, mes=2,
            items=[{
                "exp_liqui": liquidacion_general_io.expediente,
                "cantidad_visitas": 3,
                "periodo": 2027,
                "mes": 4,
            }],
        )
    )

    liquidacion_inspector.refresh_from_db()
    marcador_antes = (liquidacion_inspector.periodo, liquidacion_inspector.mes)
    registros_antes = RegistroPagoInspector.objects.count()

    with pytest.raises(HttpError) as excinfo:
        delete_flujo.eliminar(rh_mes1.id)
    assert excinfo.value.status_code == 409

    # Ningún estado cambió.
    assert ReciboHonorarioInspectorMensual.objects.filter(id=rh_mes1.id).exists()
    assert RegistroPagoInspector.objects.count() == registros_antes
    liquidacion_inspector.refresh_from_db()
    assert (liquidacion_inspector.periodo, liquidacion_inspector.mes) == marcador_antes


@pytest.mark.django_db
def test_delete_latest_rh_limpia_marcador_sin_ledger(
    crear_flujo,
    cotizar_flujo,
    delete_flujo,
    inspector,
    perfil_ingeniero_inspector,
    liquidacion_inspector,
    liquidacion_visitas,
    liquidacion_general_io,
    escala_descuento_15,
):
    """
    GIVEN: Un RH Inspector Mensual (único) que avanzó el marcador de periodo.
    WHEN: Se elimina.
    THEN: Se borran sus filas de ledger y el marcador se recalcula (queda vacío).
    """
    crear_flujo.crear(
        _payload(
            cip=perfil_ingeniero_inspector.cip,
            periodo=2026, mes=1,
            items=[{
                "exp_liqui": liquidacion_general_io.expediente,
                "cantidad_visitas": 4,
                "periodo": 2027,
                "mes": 3,
            }],
        )
    )
    rh = ReciboHonorarioInspectorMensual.objects.first()

    liquidacion_inspector.refresh_from_db()
    assert liquidacion_inspector.periodo == 2027
    assert liquidacion_inspector.mes == 3
    assert RegistroPagoInspector.objects.filter(recibo_mensual_id=rh.id).count() == 1

    delete_flujo.eliminar(rh.id)

    # Sin ledger restante el marcador se limpia.
    assert RegistroPagoInspector.objects.filter(recibo_mensual_id=rh.id).count() == 0
    liquidacion_inspector.refresh_from_db()
    assert liquidacion_inspector.periodo is None
    assert liquidacion_inspector.mes is None


@pytest.mark.django_db
def test_delete_latest_rh_recalcula_marcador_con_ledger_restante(
    crear_flujo,
    cotizar_flujo,
    delete_flujo,
    inspector,
    perfil_ingeniero_inspector,
    liquidacion_inspector,
    liquidacion_visitas,
    liquidacion_general_io,
    escala_descuento_15,
):
    """
    GIVEN: Dos RH Inspector Mensuales (2026-01 y 2026-02) sobre la misma IO.
    WHEN: Se elimina el último (2026-02).
    THEN: El marcador vuelve al periodo del ledger restante (2026-01).
    """
    crear_flujo.crear(
        _payload(
            cip=perfil_ingeniero_inspector.cip,
            periodo=2026, mes=1,
            items=[{
                "exp_liqui": liquidacion_general_io.expediente,
                "cantidad_visitas": 4,
            }],
        )
    )
    crear_flujo.crear(
        _payload(
            cip=perfil_ingeniero_inspector.cip,
            periodo=2026, mes=2,
            items=[{
                "exp_liqui": liquidacion_general_io.expediente,
                "cantidad_visitas": 3,
            }],
        )
    )
    rh_mes2 = ReciboHonorarioInspectorMensual.objects.filter(mes=2).first()

    liquidacion_inspector.refresh_from_db()
    assert liquidacion_inspector.periodo == 2026
    assert liquidacion_inspector.mes == 2
    assert RegistroPagoInspector.objects.count() == 2

    delete_flujo.eliminar(rh_mes2.id)

    # Solo queda el ledger de 2026-01 → el marcador retrocede a ese periodo.
    assert RegistroPagoInspector.objects.count() == 1
    liquidacion_inspector.refresh_from_db()
    assert liquidacion_inspector.periodo == 2026
    assert liquidacion_inspector.mes == 1


@pytest.mark.django_db
def test_admin_delete_rh_inspector_rechaza_rh_no_latest(
    crear_flujo,
    cotizar_flujo,
    delete_flujo,
    inspector,
    perfil_ingeniero_inspector,
    liquidacion_inspector,
    liquidacion_visitas,
    liquidacion_general_io,
    escala_descuento_15,
):
    """
    GIVEN: Dos RH Inspector Mensuales (mes 1 y mes 2).
    WHEN: Se intenta eliminar desde el admin el RH no latest.
    THEN: El admin rechaza la operación (PermissionDenied) y nada cambia.
    """
    from django.contrib import admin as django_admin
    from django.core.exceptions import PermissionDenied
    from modules.finanzas.admin.rh_admin import ReciboHonorarioInspectorMensualAdmin

    crear_flujo.crear(
        _payload(
            cip=perfil_ingeniero_inspector.cip,
            periodo=2026, mes=1,
            items=[{
                "exp_liqui": liquidacion_general_io.expediente,
                "cantidad_visitas": 4,
            }],
        )
    )
    rh_mes1 = ReciboHonorarioInspectorMensual.objects.filter(mes=1).first()

    crear_flujo.crear(
        _payload(
            cip=perfil_ingeniero_inspector.cip,
            periodo=2026, mes=2,
            items=[{
                "exp_liqui": liquidacion_general_io.expediente,
                "cantidad_visitas": 3,
            }],
        )
    )

    admin_obj = ReciboHonorarioInspectorMensualAdmin(
        ReciboHonorarioInspectorMensual,
        django_admin.site,
    )
    with pytest.raises(PermissionDenied):
        admin_obj.delete_model(request=None, obj=rh_mes1)

    assert ReciboHonorarioInspectorMensual.objects.filter(id=rh_mes1.id).exists()


@pytest.mark.django_db
def test_admin_delete_rh_inspector_usa_el_lifecycle(
    crear_flujo,
    cotizar_flujo,
    delete_flujo,
    inspector,
    perfil_ingeniero_inspector,
    liquidacion_inspector,
    liquidacion_visitas,
    liquidacion_general_io,
    escala_descuento_15,
):
    """
    GIVEN: Un RH Inspector Mensual (único).
    WHEN: Se elimina desde el admin (delete_model).
    THEN: Pasa por el lifecycle: borra el RH, su ledger y recalcula el marcador.
    """
    from django.contrib import admin as django_admin
    from modules.finanzas.admin.rh_admin import ReciboHonorarioInspectorMensualAdmin

    crear_flujo.crear(
        _payload(
            cip=perfil_ingeniero_inspector.cip,
            periodo=2026, mes=1,
            items=[{
                "exp_liqui": liquidacion_general_io.expediente,
                "cantidad_visitas": 4,
                "periodo": 2027,
                "mes": 3,
            }],
        )
    )
    rh = ReciboHonorarioInspectorMensual.objects.first()

    admin_obj = ReciboHonorarioInspectorMensualAdmin(
        ReciboHonorarioInspectorMensual,
        django_admin.site,
    )
    admin_obj.delete_model(request=None, obj=rh)

    assert not ReciboHonorarioInspectorMensual.objects.filter(id=rh.id).exists()
    assert RegistroPagoInspector.objects.filter(recibo_mensual_id=rh.id).count() == 0
    liquidacion_inspector.refresh_from_db()
    assert liquidacion_inspector.periodo is None
    assert liquidacion_inspector.mes is None




# ── PATCH (Sincronización del conjunto final) ───────────────────────────────────
#
# El PATCH define el conjunto FINAL de liquidaciones del RH:
#   - items con `detalle_id`  -> la fila persistida se CONSERVA (se re-cotiza
#                                 excluyendo el propio RH de su balance).
#   - items sin `detalle_id` -> la fila se AGREGA.
#   - detalles persistidos ausentes del payload -> se RETIRAN (y su fila del
#     ledger de pagos vinculada al RH se reemplaza).


@pytest.fixture
def actualizar_flujo(core_service, cotizar_flujo):
    return RHInspectorMensualActualizarFlujo(core=core_service, cotizar_flujo=cotizar_flujo)


@pytest.fixture
def segunda_general_io(db, segundo_proyecto_test, municipalidad_test, tipo_inspeccion_obra, usuario_liquidacion):
    """Segunda LiquidacionGeneral de tipo INSPECCION_OBRA (para pruebas multi-IO).

    Usa su propio Proyecto: `LiquidacionGeneral.proyecto` es OneToOneField.
    """
    return LiquidacionGeneral.objects.create(
        proyecto=segundo_proyecto_test,
        municipalidad=municipalidad_test,
        tipo_liquidacion=tipo_inspeccion_obra,
        usuario_creador=usuario_liquidacion,
        expediente="EXP-MENSUAL-002",
        estado="REGISTRADO",
        sub_total=Decimal("2000.00"),
        total=Decimal("2360.00"),
    )


@pytest.fixture
def segunda_visitas_io(db, segunda_general_io, tarifa_visitas_io):
    """Segunda LiquidacionPorCategoriaVisitas con 10 visitas programadas."""
    return LiquidacionPorCategoriaVisitas.objects.create(
        liquidacion_general=segunda_general_io,
        cantidad_visitas=10,
        porcentaje_uit=Decimal("0.05"),
        categoria="B",
        tarifa_aplicada=tarifa_visitas_io,
    )


@pytest.fixture
def segunda_liquidacion_inspector(db, segunda_visitas_io, inspector, especialidad_revision):
    """LiquidacionInspector asociando el inspector a la segunda IO."""
    return LiquidacionInspector.objects.create(
        liquidacion=segunda_visitas_io,
        inspector=inspector,
        especialidad_revision=especialidad_revision,
    )


def _payload_actualizar(cip: str, periodo: int, mes: int, items: list[dict]):
    """Helper para construir el payload de PATCH (sincronización) del inspector."""
    return RHInspectorActualizarIn(
        cip=cip,
        periodo=periodo,
        mes=mes,
        items=[RHInspectorActualizarItemIn(**i) for i in items],
    )


@pytest.mark.django_db
def test_patch_rh_inspector_conserva_el_detalle_y_actualiza_los_totales(
    crear_flujo,
    actualizar_flujo,
    inspector,
    perfil_ingeniero_inspector,
    escala_descuento_15,
    liquidacion_general_io,
    liquidacion_visitas,
    liquidacion_inspector,
):
    """
    GIVEN: Un RH Inspector Mensual con un detalle persistido.
    WHEN: Se hace PATCH con el mismo detalle (conservar).
    THEN: La fila conserva su identidad, los totales se recalculan y el
          resultado expone el identificador estable del detalle.
    """
    crear_flujo.crear(
        _payload(
            cip=perfil_ingeniero_inspector.cip,
            periodo=2026, mes=1,
            items=[{
                "liquidacion_categoria_visitas_id": str(liquidacion_visitas.id),
                "cantidad_visitas": 3,
            }],
        )
    )
    rh = ReciboHonorarioInspectorMensual.objects.first()
    detalle = rh.detalles.first()

    resultado = actualizar_flujo.actualizar(
        rh.id,
        _payload_actualizar(
            cip=perfil_ingeniero_inspector.cip,
            periodo=2026, mes=1,
            items=[{
                "liquidacion_categoria_visitas_id": str(liquidacion_visitas.id),
                "cantidad_visitas": 3,
                "detalle_id": str(detalle.id),
            }],
        ),
    )

    rh.refresh_from_db()
    assert rh.detalles.count() == 1
    assert rh.detalles.filter(id=detalle.id).exists()
    assert rh.sub_total == Decimal("300.00")
    assert rh.descuento == Decimal("45.00")
    assert rh.honorarios == Decimal("255.00")
    assert resultado.items[0].detalle_id == str(detalle.id)


@pytest.mark.django_db
def test_cotizar_edicion_resuelve_la_liquidacion_desde_el_detalle_persistido(
    crear_flujo,
    actualizar_flujo,
    perfil_ingeniero_inspector,
    escala_descuento_15,
    liquidacion_general_io,
    liquidacion_visitas,
    liquidacion_inspector,
):
    """La previsualización de edición no vuelve a resolver por expediente."""
    crear_flujo.crear(
        _payload(
            cip=perfil_ingeniero_inspector.cip,
            periodo=2026,
            mes=1,
            items=[
                {
                    "liquidacion_categoria_visitas_id": str(liquidacion_visitas.id),
                    "cantidad_visitas": 3,
                }
            ],
        )
    )
    rh = ReciboHonorarioInspectorMensual.objects.first()
    detalle = rh.detalles.first()

    resultado = actualizar_flujo.cotizar_actualizacion(
        rh.id,
        _payload_actualizar(
            cip=perfil_ingeniero_inspector.cip,
            periodo=2026,
            mes=1,
            items=[
                {
                    "detalle_id": str(detalle.id),
                    "exp_liqui": "EXPEDIENTE-AMBIGUO-O-DESACTUALIZADO",
                    "cantidad_visitas": 3,
                }
            ],
        ),
    )

    assert len(resultado.items) == 1
    assert resultado.items[0].liquidacion_categoria_visitas_id == str(
        liquidacion_visitas.id
    )
    assert resultado.items[0].inspecciones_liquidadas == 3
    detalle.refresh_from_db()
    assert detalle.inspecciones_liquidadas == 3


@pytest.mark.django_db
def test_patch_rh_inspector_excluye_el_rh_de_su_propio_balance(
    crear_flujo,
    actualizar_flujo,
    inspector,
    perfil_ingeniero_inspector,
    escala_descuento_15,
    liquidacion_general_io,
    liquidacion_visitas,
    liquidacion_inspector,
):
    """
    GIVEN: Un RH Inspector Mensual que consumió 9 de las 10 visitas programadas.
    WHEN: Se hace PATCH pidiendo las mismas 9 visitas.
    THEN: Se acepta: el saldo se calcula excluyendo al propio RH de su balance.
    """
    crear_flujo.crear(
        _payload(
            cip=perfil_ingeniero_inspector.cip,
            periodo=2026, mes=1,
            items=[{
                "liquidacion_categoria_visitas_id": str(liquidacion_visitas.id),
                "cantidad_visitas": 9,
            }],
        )
    )
    rh = ReciboHonorarioInspectorMensual.objects.first()
    detalle = rh.detalles.first()

    resultado = actualizar_flujo.actualizar(
        rh.id,
        _payload_actualizar(
            cip=perfil_ingeniero_inspector.cip,
            periodo=2026, mes=1,
            items=[{
                "liquidacion_categoria_visitas_id": str(liquidacion_visitas.id),
                "cantidad_visitas": 9,
                "detalle_id": str(detalle.id),
            }],
        ),
    )

    assert resultado.totales.sub_total == Decimal("900.00")
    rh.refresh_from_db()
    assert rh.sub_total == Decimal("900.00")
    assert rh.honorarios == Decimal("765.00")


@pytest.mark.django_db
def test_patch_rh_inspector_404_si_el_rh_no_existe(
    actualizar_flujo,
    perfil_ingeniero_inspector,
    escala_descuento_15,
    liquidacion_general_io,
    liquidacion_visitas,
    liquidacion_inspector,
):
    """
    GIVEN: Un identificador de RH que no existe.
    WHEN: Se hace PATCH.
    THEN: Se responde 404.
    """
    from ninja.errors import HttpError

    with pytest.raises(HttpError) as exc_info:
        actualizar_flujo.actualizar(
            uuid.uuid4(),
            _payload_actualizar(
                cip=perfil_ingeniero_inspector.cip,
                periodo=2026, mes=1,
                items=[{
                    "liquidacion_categoria_visitas_id": str(liquidacion_visitas.id),
                    "cantidad_visitas": 1,
                }],
            ),
        )

    assert exc_info.value.status_code == 404


@pytest.mark.django_db
def test_patch_rh_inspector_400_si_la_seleccion_es_vacia(
    crear_flujo,
    actualizar_flujo,
    perfil_ingeniero_inspector,
    escala_descuento_15,
    liquidacion_general_io,
    liquidacion_visitas,
    liquidacion_inspector,
):
    """
    GIVEN: Un RH Inspector Mensual existente.
    WHEN: Se hace PATCH con un conjunto final vacío.
    THEN: Se responde 400 y el recibo conserva sus detalles.
    """
    from ninja.errors import HttpError

    crear_flujo.crear(
        _payload(
            cip=perfil_ingeniero_inspector.cip,
            periodo=2026, mes=1,
            items=[{
                "liquidacion_categoria_visitas_id": str(liquidacion_visitas.id),
                "cantidad_visitas": 2,
            }],
        )
    )
    rh = ReciboHonorarioInspectorMensual.objects.first()

    with pytest.raises(HttpError) as exc_info:
        actualizar_flujo.actualizar(
            rh.id,
            _payload_actualizar(
                cip=perfil_ingeniero_inspector.cip,
                periodo=2026, mes=1,
                items=[],
            ),
        )

    assert exc_info.value.status_code == 400
    assert rh.detalles.count() == 1


@pytest.mark.django_db
def test_patch_rh_inspector_permite_editar_cualquier_rh_no_solo_el_ultimo(
    crear_flujo,
    actualizar_flujo,
    inspector,
    perfil_ingeniero_inspector,
    escala_descuento_15,
    liquidacion_general_io,
    liquidacion_visitas,
    liquidacion_inspector,
):
    """
    GIVEN: Dos RH Inspector Mensuales del mismo inspector (el segundo es el último).
    WHEN: Se hace PATCH sobre el primero (no latest).
    THEN: El PATCH se aplica: cualquier RH es editable.
    """
    crear_flujo.crear(
        _payload(
            cip=perfil_ingeniero_inspector.cip,
            periodo=2026, mes=1,
            items=[{
                "liquidacion_categoria_visitas_id": str(liquidacion_visitas.id),
                "cantidad_visitas": 2,
            }],
        )
    )
    rh_mes1 = ReciboHonorarioInspectorMensual.objects.filter(mes=1).first()

    crear_flujo.crear(
        _payload(
            cip=perfil_ingeniero_inspector.cip,
            periodo=2026, mes=2,
            items=[{
                "liquidacion_categoria_visitas_id": str(liquidacion_visitas.id),
                "cantidad_visitas": 2,
            }],
        )
    )
    rh_mes2 = ReciboHonorarioInspectorMensual.objects.filter(mes=2).first()
    totales_previos = (rh_mes1.sub_total, rh_mes1.honorarios)

    resultado = actualizar_flujo.actualizar(
        rh_mes1.id,
        _payload_actualizar(
            cip=perfil_ingeniero_inspector.cip,
            periodo=2026, mes=1,
            items=[{
                "liquidacion_categoria_visitas_id": str(liquidacion_visitas.id),
                "cantidad_visitas": 5,
            }],
        ),
    )

    rh_mes1.refresh_from_db()
    assert (rh_mes1.sub_total, rh_mes1.honorarios) != totales_previos
    assert resultado.items[0].inspecciones_liquidadas == 5
    # El RH más reciente no se ve afectado.
    rh_mes2.refresh_from_db()
    assert rh_mes2.detalles.count() == 1



@pytest.mark.django_db
def test_patch_rh_inspector_422_si_el_rango_de_fechas_esta_invertido(
    crear_flujo,
    actualizar_flujo,
    inspector,
    perfil_ingeniero_inspector,
    escala_descuento_15,
    liquidacion_general_io,
    liquidacion_visitas,
    liquidacion_inspector,
):
    """
    GIVEN: Un RH Inspector Mensual existente.
    WHEN: Se hace PATCH con un item cuya revisión es posterior a la presentación.
    THEN: Se responde 422 y el recibo no se modifica.
    """
    from ninja.errors import HttpError

    crear_flujo.crear(
        _payload(
            cip=perfil_ingeniero_inspector.cip,
            periodo=2026, mes=1,
            items=[{
                "liquidacion_categoria_visitas_id": str(liquidacion_visitas.id),
                "cantidad_visitas": 2,
            }],
        )
    )
    rh = ReciboHonorarioInspectorMensual.objects.first()
    totales_previos = (rh.sub_total, rh.honorarios)

    with pytest.raises(HttpError) as exc_info:
        actualizar_flujo.actualizar(
            rh.id,
            _payload_actualizar(
                cip=perfil_ingeniero_inspector.cip,
                periodo=2026, mes=1,
                items=[{
                    "liquidacion_categoria_visitas_id": str(liquidacion_visitas.id),
                    "cantidad_visitas": 2,
                    "fecha_revision": date(2026, 2, 10),
                    "fecha_presentacion": date(2026, 1, 10),
                }],
            ),
        )

    assert exc_info.value.status_code == 422
    rh.refresh_from_db()
    assert (rh.sub_total, rh.honorarios) == totales_previos


@pytest.mark.django_db
def test_patch_rh_inspector_retira_detalles_no_seleccionados_y_reemplaza_el_ledger(
    crear_flujo,
    actualizar_flujo,
    inspector,
    perfil_ingeniero_inspector,
    escala_descuento_15,
    liquidacion_general_io,
    liquidacion_visitas,
    liquidacion_inspector,
    segunda_general_io,
    segunda_visitas_io,
    segunda_liquidacion_inspector,
):
    """
    GIVEN: Un RH Inspector Mensual con 2 IOs (2 detalles y 2 filas de ledger).
    WHEN: Se hace PATCH conservando solo una IO.
    THEN: El detalle retirado se elimina, el ledger del RH queda con una sola fila
          y las filas de otros RH (o legacy sin FK) no se tocan.
    """
    crear_flujo.crear(
        _payload(
            cip=perfil_ingeniero_inspector.cip,
            periodo=2026, mes=1,
            items=[
                {
                    "liquidacion_categoria_visitas_id": str(liquidacion_visitas.id),
                    "cantidad_visitas": 2,
                },
                {
                    "liquidacion_categoria_visitas_id": str(segunda_visitas_io.id),
                    "cantidad_visitas": 3,
                },
            ],
        )
    )
    rh = ReciboHonorarioInspectorMensual.objects.first()
    assert rh.detalles.count() == 2
    assert RegistroPagoInspector.objects.filter(recibo_mensual_id=rh.id).count() == 2

    detalle_conservado = rh.detalles.filter(
        liquidacion_por_categoria_visitas_id=liquidacion_visitas.id
    ).first()
    detalle_retirado = rh.detalles.filter(
        liquidacion_por_categoria_visitas_id=segunda_visitas_io.id
    ).first()

    actualizar_flujo.actualizar(
        rh.id,
        _payload_actualizar(
            cip=perfil_ingeniero_inspector.cip,
            periodo=2026, mes=1,
            items=[{
                "liquidacion_categoria_visitas_id": str(liquidacion_visitas.id),
                "cantidad_visitas": 2,
                "detalle_id": str(detalle_conservado.id),
            }],
        ),
    )

    rh.refresh_from_db()
    assert rh.detalles.count() == 1
    assert rh.detalles.filter(id=detalle_conservado.id).exists()
    assert not DetalleHonorarioInspector.objects.filter(id=detalle_retirado.id).exists()
    ledger = RegistroPagoInspector.objects.filter(recibo_mensual_id=rh.id)
    assert ledger.count() == 1
    assert ledger.first().liquidacion_por_categoria_visitas_id == liquidacion_visitas.id
    # Los totales reflejan el conjunto final (2 visitas × 100.00).
    assert rh.sub_total == Decimal("200.00")
    assert rh.descuento == Decimal("30.00")
    assert rh.honorarios == Decimal("170.00")


@pytest.mark.django_db
def test_patch_rh_inspector_recalcula_el_marcador_de_periodo(
    crear_flujo,
    actualizar_flujo,
    inspector,
    perfil_ingeniero_inspector,
    escala_descuento_15,
    liquidacion_general_io,
    liquidacion_visitas,
    liquidacion_inspector,
):
    """
    GIVEN: Un RH Inspector Mensual cuyo marcador de periodo quedó desactualizado.
    WHEN: Se hace PATCH del mismo conjunto.
    THEN: El marcador de la LiquidacionInspector se recalcula desde el ledger
          (periodo y mes del recibo).
    """
    crear_flujo.crear(
        _payload(
            cip=perfil_ingeniero_inspector.cip,
            periodo=2026, mes=1,
            items=[{
                "liquidacion_categoria_visitas_id": str(liquidacion_visitas.id),
                "cantidad_visitas": 2,
            }],
        )
    )
    rh = ReciboHonorarioInspectorMensual.objects.first()
    detalle = rh.detalles.first()

    liquidacion_inspector.periodo = 2025
    liquidacion_inspector.mes = 12
    liquidacion_inspector.save(update_fields=["periodo", "mes"])

    actualizar_flujo.actualizar(
        rh.id,
        _payload_actualizar(
            cip=perfil_ingeniero_inspector.cip,
            periodo=2026, mes=1,
            items=[{
                "liquidacion_categoria_visitas_id": str(liquidacion_visitas.id),
                "cantidad_visitas": 2,
                "detalle_id": str(detalle.id),
            }],
        ),
    )

    liquidacion_inspector.refresh_from_db()
    assert liquidacion_inspector.periodo == 2026
    assert liquidacion_inspector.mes == 1


@pytest.mark.django_db
def test_patch_rh_inspector_400_si_el_detalle_no_pertenece_al_rh(
    crear_flujo,
    actualizar_flujo,
    inspector,
    perfil_ingeniero_inspector,
    escala_descuento_15,
    liquidacion_general_io,
    liquidacion_visitas,
    liquidacion_inspector,
    segunda_general_io,
    segunda_visitas_io,
segunda_liquidacion_inspector,
):
    """
    GIVEN: Dos RH Inspector Mensuales del mismo inspector.
    WHEN: Se hace PATCH sobre el ÚLTIMO RH usando el detalle del otro.
    THEN: Se responde 400 y el recibo no se modifica.

    El PATCH solo se permite sobre el último RH del inspector (el de mes 2):
    el detalle ajeno es el del RH de mes 1.
    """
    from ninja.errors import HttpError

    crear_flujo.crear(
        _payload(
            cip=perfil_ingeniero_inspector.cip,
            periodo=2026, mes=1,
            items=[{
                "liquidacion_categoria_visitas_id": str(liquidacion_visitas.id),
                "cantidad_visitas": 2,
            }],
        )
    )
    rh_mes1 = ReciboHonorarioInspectorMensual.objects.filter(mes=1).first()

    crear_flujo.crear(
        _payload(
            cip=perfil_ingeniero_inspector.cip,
            periodo=2026, mes=2,
            items=[{
                "liquidacion_categoria_visitas_id": str(liquidacion_visitas.id),
                "cantidad_visitas": 2,
            }],
        )
    )
    rh_mes2 = ReciboHonorarioInspectorMensual.objects.filter(mes=2).first()
    detalle_ajeno = rh_mes1.detalles.first()
    totales_previos = (rh_mes2.sub_total, rh_mes2.honorarios)

    with pytest.raises(HttpError) as exc_info:
        actualizar_flujo.actualizar(
            rh_mes2.id,
            _payload_actualizar(
                cip=perfil_ingeniero_inspector.cip,
                periodo=2026, mes=2,
                items=[{
                    "liquidacion_categoria_visitas_id": str(liquidacion_visitas.id),
                    "cantidad_visitas": 2,
                    "detalle_id": str(detalle_ajeno.id),
                }],
            ),
        )

    assert exc_info.value.status_code == 400
    rh_mes2.refresh_from_db()
    assert (rh_mes2.sub_total, rh_mes2.honorarios) == totales_previos
    assert rh_mes2.detalles.count() == 1
    # El RH ajeno tampoco se modifica.
    assert rh_mes1.detalles.count() == 1


@pytest.mark.django_db
def test_patch_rh_inspector_revierte_los_cambios_si_la_reconciliacion_falla(
    crear_flujo,
    actualizar_flujo,
    inspector,
    perfil_ingeniero_inspector,
    escala_descuento_15,
    liquidacion_general_io,
    liquidacion_visitas,
    liquidacion_inspector,
    segunda_general_io,
    segunda_visitas_io,
    segunda_liquidacion_inspector,
):
    """
    GIVEN: Dos RH Inspector Mensuales del mismo inspector.
    WHEN: Se hace PATCH sobre el ÚLTIMO RH agregando una IO nueva y usando, en el
           mismo payload, el detalle del RH anterior (400).
    THEN: La transacción se revierte: no queda el detalle agregado ni su fila de
           ledger, y los totales del recibo son los originales.

    El PATCH solo se permite sobre el último RH del inspector (el de mes 2):
    el detalle ajeno es el del RH de mes 1.
    """
    from ninja.errors import HttpError

    crear_flujo.crear(
        _payload(
            cip=perfil_ingeniero_inspector.cip,
            periodo=2026, mes=1,
            items=[{
                "liquidacion_categoria_visitas_id": str(liquidacion_visitas.id),
                "cantidad_visitas": 2,
            }],
        )
    )
    rh_mes1 = ReciboHonorarioInspectorMensual.objects.filter(mes=1).first()

    crear_flujo.crear(
        _payload(
            cip=perfil_ingeniero_inspector.cip,
            periodo=2026, mes=2,
            items=[{
                "liquidacion_categoria_visitas_id": str(liquidacion_visitas.id),
                "cantidad_visitas": 2,
            }],
        )
    )
    rh_mes2 = ReciboHonorarioInspectorMensual.objects.filter(mes=2).first()
    detalle_ajeno = rh_mes1.detalles.first()
    totales_previos = (rh_mes2.sub_total, rh_mes2.honorarios)

    with pytest.raises(HttpError) as exc_info:
        actualizar_flujo.actualizar(
            rh_mes2.id,
            _payload_actualizar(
                cip=perfil_ingeniero_inspector.cip,
                periodo=2026, mes=2,
                items=[
                    {
                        "liquidacion_categoria_visitas_id": str(segunda_visitas_io.id),
                        "cantidad_visitas": 1,
                    },
                    {
                        "liquidacion_categoria_visitas_id": str(liquidacion_visitas.id),
                        "cantidad_visitas": 2,
                        "detalle_id": str(detalle_ajeno.id),
                    },
                ],
            ),
        )

    assert exc_info.value.status_code == 400
    rh_mes2.refresh_from_db()
    assert rh_mes2.detalles.count() == 1
    assert (rh_mes2.sub_total, rh_mes2.honorarios) == totales_previos
    assert RegistroPagoInspector.objects.filter(recibo_mensual_id=rh_mes2.id).count() == 1


@pytest.mark.django_db
def test_patch_rh_inspector_redistribuye_el_descuento_sobre_el_conjunto_final(
    crear_flujo,
    actualizar_flujo,
    inspector,
    perfil_ingeniero_inspector,
    escala_descuento_15,
    liquidacion_general_io,
    liquidacion_visitas,
    liquidacion_inspector,
    segunda_general_io,
    segunda_visitas_io,
    segunda_liquidacion_inspector,
):
    """
    GIVEN: Un RH Inspector Mensual con 2 IOs.
    WHEN: Se hace PATCH con un conjunto final que redistribuye el descuento.
    THEN: La suma de los descuentos por item es exactamente el descuento del
          recibo y los honorarios son el sub total menos ese descuento.
    """
    crear_flujo.crear(
        _payload(
            cip=perfil_ingeniero_inspector.cip,
            periodo=2026, mes=1,
            items=[
                {
                    "liquidacion_categoria_visitas_id": str(liquidacion_visitas.id),
                    "cantidad_visitas": 2,
                },
                {
                    "liquidacion_categoria_visitas_id": str(segunda_visitas_io.id),
                    "cantidad_visitas": 1,
                },
            ],
        )
    )
    rh = ReciboHonorarioInspectorMensual.objects.first()
    detalle_io1 = rh.detalles.filter(
        liquidacion_por_categoria_visitas_id=liquidacion_visitas.id
    ).first()
    detalle_io2 = rh.detalles.filter(
        liquidacion_por_categoria_visitas_id=segunda_visitas_io.id
    ).first()

    resultado = actualizar_flujo.actualizar(
        rh.id,
        _payload_actualizar(
            cip=perfil_ingeniero_inspector.cip,
            periodo=2026, mes=1,
            items=[
                {
                    "liquidacion_categoria_visitas_id": str(liquidacion_visitas.id),
                    "cantidad_visitas": 3,
                    "detalle_id": str(detalle_io1.id),
                },
                {
                    "liquidacion_categoria_visitas_id": str(segunda_visitas_io.id),
                    "cantidad_visitas": 1,
                    "detalle_id": str(detalle_io2.id),
                },
            ],
        ),
    )

    rh.refresh_from_db()
    # IO1: 3 × 100.00 = 300.00 ; IO2: 1 × 200.00 = 200.00 → sub total 500.00
    assert rh.sub_total == Decimal("500.00")
    assert rh.descuento == Decimal("75.00")
    assert rh.honorarios == Decimal("425.00")
    # La suma de los descuentos por item absorbe el resto sin residuo.
    assert sum(item.descuento for item in resultado.items) == rh.descuento
    # El reparto es proporcional al sub total de cada item.
    descuentos = {item.liquidacion_categoria_visitas_id: item.descuento for item in resultado.items}
    assert descuentos[str(liquidacion_visitas.id)] == Decimal("45.00")
    assert descuentos[str(segunda_visitas_io.id)] == Decimal("30.00")


# ── Contrato de datos del listado mensual (Result → Presenter → Schema Out) ────
#
# El listado mensual del RH Inspector calcula en su Result datos que el
# Presenter y el Schema Out descartaban: el número de RH de cabecera, el número
# de revisión de la liquidación y las fechas de revisión/presentación con su
# dictamen. Estos tests fijan el contrato HTTP para que ningún campo calculado
# vuelva a perderse en silencio, y verifican que el RH Delegado no se degrade.
#
# Estos tests se ESCRIBEN pero NO se ejecutan en esta fase del change
# (la ejecución consolidada ocurre en la fase final de verificación).


@pytest.fixture
def listar_flujo(core_service):
    return RHInspectorMensualListFlujo(core=core_service)


@pytest.fixture
def comprobante_activo_io(db, liquidacion_general_io):
    """Comprobante activo (factura) de la liquidación de IO."""
    return LiquidacionComprobante.objects.create(
        liquidacion_general=liquidacion_general_io,
        tipo_comprobante="FACTURA",
        serie="F001",
        numero="0001-45",
        fecha_emision=date(2026, 1, 10),
        activo=True,
    )


def _crear_rh_inspector(crear_flujo, perfil_ingeniero_inspector, liquidacion_visitas):
    """Crea un RH Inspector Mensual con un detalle (IO) y devuelve el recibo."""
    crear_flujo.crear(
        _payload(
            cip=perfil_ingeniero_inspector.cip,
            periodo=2026, mes=1,
            items=[{
                "liquidacion_categoria_visitas_id": str(liquidacion_visitas.id),
                "cantidad_visitas": 2,
            }],
        )
    )
    return ReciboHonorarioInspectorMensual.objects.first()


@pytest.mark.django_db
def test_listado_rh_inspector_filtra_por_cip_periodo_y_mes(
    crear_flujo,
    listar_flujo,
    inspector,
    liquidacion_inspector,
    perfil_ingeniero_inspector,
    liquidacion_visitas,
    escala_descuento_15,
):
    """
    GIVEN: RH Inspectores Mensuales de dos periodos y dos inspectores.
    WHEN: Se lista con los filtros de CIP, año y mes.
    THEN: Solo devuelve los RH que coinciden con el filtro.
    """
    _crear_rh_inspector(
        crear_flujo, perfil_ingeniero_inspector, liquidacion_visitas
    )
    crear_flujo.crear(
        _payload(
            cip=perfil_ingeniero_inspector.cip,
            periodo=2026,
            mes=2,
            items=[{
                "liquidacion_categoria_visitas_id": str(liquidacion_visitas.id),
                "cantidad_visitas": 2,
            }],
        )
    )

    resultados, total = listar_flujo.listar_rh_mensuales_inspectores_proceso(
        page=1,
        page_size=10,
        inspector_cip=perfil_ingeniero_inspector.cip,
        periodo=2026,
        mes=2,
    )

    assert total == 1
    assert resultados[0].mes == 2

    # Un mes que no existe no devuelve nada.
    _, total_sin_coincidencia = (
        listar_flujo.listar_rh_mensuales_inspectores_proceso(
            page=1,
            page_size=10,
            inspector_cip=perfil_ingeniero_inspector.cip,
            periodo=2026,
            mes=7,
        )
    )
    assert total_sin_coincidencia == 0


@pytest.mark.django_db
def test_listado_rh_inspector_expone_el_numero_de_rh_de_cabecera(
    crear_flujo,
    listar_flujo,
    inspector,
    liquidacion_inspector,
    perfil_ingeniero_inspector,
    liquidacion_visitas,
    escala_descuento_15,
):
    """
    GIVEN: Un RH Inspector Mensual con número de cabecera asignado.
    WHEN: Se lista el RH y se mapea con el Presenter.
    THEN: El número del RH viaja en el Result, en el Schema Out y en el JSON.
    """
    rh = _crear_rh_inspector(crear_flujo, perfil_ingeniero_inspector, liquidacion_visitas)
    rh.numero = 7
    rh.save(update_fields=["numero"])

    resultados, total = listar_flujo.listar_rh_mensuales_inspectores_proceso(
        page=1, page_size=10
    )

    assert total == 1
    assert resultados[0].numero == 7

    out = FinanzasPresenter._map_rh_mensual_inspector_out(resultados[0])
    assert out.numero == 7

    payload = json.loads(out.model_dump_json())
    assert payload["numero"] == 7


@pytest.mark.django_db
def test_listado_rh_inspector_expone_fechas_y_dictamen_de_revision(
    crear_flujo,
    listar_flujo,
    perfil_ingeniero_inspector,
    liquidacion_visitas,
    liquidacion_inspector,
    escala_descuento_15,
):
    """
    GIVEN: Una asignación inspector-IO con fecha de revisión, fecha de
           presentación y dictamen de revisión.
    WHEN: Se lista el RH mensual.
    THEN: Las tres fechas/dictamen llegan al Result, al Schema Out y al JSON.
    """
    _crear_rh_inspector(crear_flujo, perfil_ingeniero_inspector, liquidacion_visitas)
    liquidacion_inspector.fecha_revision = date(2026, 1, 15)
    liquidacion_inspector.fecha_presentacion = date(2026, 1, 20)
    liquidacion_inspector.dictamen_revision = "CONFORME"
    liquidacion_inspector.save()

    resultados, _ = listar_flujo.listar_rh_mensuales_inspectores_proceso(
        page=1, page_size=10
    )
    detalle = resultados[0].detalles[0]

    assert detalle.fecha_revision == "2026-01-15"
    assert detalle.fecha_presentacion == "2026-01-20"
    assert detalle.dictamen_revision == "CONFORME"

    out = FinanzasPresenter._map_rh_mensual_inspector_out(resultados[0])
    assert out.detalles[0].fecha_revision == "2026-01-15"
    assert out.detalles[0].fecha_presentacion == "2026-01-20"
    assert out.detalles[0].dictamen_revision == "CONFORME"

    payload = json.loads(out.model_dump_json())
    assert payload["detalles"][0]["fecha_revision"] == "2026-01-15"
    assert payload["detalles"][0]["fecha_presentacion"] == "2026-01-20"
    assert payload["detalles"][0]["dictamen_revision"] == "CONFORME"


@pytest.mark.django_db
def test_listado_rh_inspector_distingue_numero_de_rh_de_revision_y_de_liquidacion(
    crear_flujo,
    listar_flujo,
    inspector,
    liquidacion_inspector,
    perfil_ingeniero_inspector,
    liquidacion_visitas,
    liquidacion_general_io,
    liquidacion_io,
    escala_descuento_15,
):
    """
    GIVEN: Un RH Inspector con nº de RH (7), revisión (3) y una liquidación
           específica con su propio número.
    WHEN: Se lista el RH mensual.
    THEN: Los tres números viajan por separado y sin confundirse entre sí.
    """
    rh = _crear_rh_inspector(crear_flujo, perfil_ingeniero_inspector, liquidacion_visitas)
    rh.numero = 7
    rh.save(update_fields=["numero"])
    liquidacion_general_io.numero_revision = 3
    liquidacion_general_io.save(update_fields=["numero_revision"])

    resultados, _ = listar_flujo.listar_rh_mensuales_inspectores_proceso(
        page=1, page_size=10
    )
    resultado = resultados[0]
    detalle = resultado.detalles[0]

    assert resultado.numero == 7
    assert detalle.numero_revision == 3
    assert detalle.liquidacion_especifica_numero == liquidacion_io.numero
    assert detalle.liquidacion_especifica_numero not in {
        resultado.numero,
        detalle.numero_revision,
    }

    out = FinanzasPresenter._map_rh_mensual_inspector_out(resultado)
    assert out.numero == 7
    assert out.detalles[0].numero_revision == 3
    assert out.detalles[0].liquidacion_especifica_numero == liquidacion_io.numero


@pytest.mark.django_db
def test_listado_rh_inspector_expone_el_comprobante_activo_tipado(
    crear_flujo,
    listar_flujo,
    inspector,
    liquidacion_inspector,
    perfil_ingeniero_inspector,
    liquidacion_visitas,
    comprobante_activo_io,
    escala_descuento_15,
):
    """
    GIVEN: Una liquidación de IO con comprobante activo.
    WHEN: Se lista el RH mensual.
    THEN: El comprobante viaja tipado (tipo, serie, número y fecha de emisión).
    """
    _crear_rh_inspector(crear_flujo, perfil_ingeniero_inspector, liquidacion_visitas)

    resultados, _ = listar_flujo.listar_rh_mensuales_inspectores_proceso(
        page=1, page_size=10
    )
    detalle = resultados[0].detalles[0]

    assert detalle.comprobante_activo is not None
    assert detalle.comprobante_activo.tipo_comprobante == "FACTURA"
    assert detalle.comprobante_activo.serie == "F001"
    assert detalle.comprobante_activo.numero == "0001-45"
    assert detalle.comprobante_activo.fecha_emision == "2026-01-10"

    out = FinanzasPresenter._map_rh_mensual_inspector_out(resultados[0])
    assert out.detalles[0].comprobante_activo is not None
    assert out.detalles[0].comprobante_activo.tipo_comprobante == "FACTURA"
    assert out.detalles[0].comprobante_activo.serie == "F001"
    assert out.detalles[0].comprobante_activo.numero == "0001-45"
    assert out.detalles[0].comprobante_activo.fecha_emision == "2026-01-10"


def test_contrato_delegado_mensual_no_se_degrada():
    """
    GIVEN: Un Result de RH Delegado mensual con todos sus campos poblados.
    WHEN: Se mapea con el Presenter.
    THEN: Ningún campo por fila se pierde (nº de RH, revisión, liquidación
          específica, comprobante, fechas y dictamen).
    """
    resultado = RHDelegadoMensualListItemResult(
        id=str(uuid.uuid4()),
        numero=11,
        periodo=2026,
        mes=1,
        fecha_registro="2026-01-31T10:00:00",
        delegado=DelegadoRHMinimalResult(
            id=str(uuid.uuid4()),
            nombre_completo="Delegado Uno",
            cip="CIP-00001",
            dni="11111111",
        ),
        totales=RHDelegadoMensualTotalesResult(
            sub_total=Decimal("1000.00"),
            renta_cip=Decimal("250.00"),
            aporte_codemu=Decimal("50.00"),
            fondo_comun=Decimal("100.00"),
            neto_honorario=Decimal("600.00"),
        ),
        detalles=[
            RHDelegadoMensualDetalleResult(
                liquidacion_delegado_id=str(uuid.uuid4()),
                detalle_id=str(uuid.uuid4()),
                expediente="EXP-002",
                fecha_revision="2026-01-05",
                numero_revision=3,
                total_liquidacion=Decimal("1180.00"),
                sub_total_liquidacion=Decimal("1000.00"),
                numero_rh="1",
                imp_bruto=Decimal("1000.00"),
                renta_cip=Decimal("250.00"),
                aporte_codemu=Decimal("50.00"),
                fondo_comun=Decimal("100.00"),
                neto_honorario=Decimal("600.00"),
                periodo=2026,
                mes=1,
                dictamen_revision="CONFORME",
                fecha_presentacion="2026-01-10",
                delegado_operacion_id=str(uuid.uuid4()),
                liquidacion_especifica_numero=42,
                comprobante_activo=LiquidacionComprobanteMinimalResult(
                    tipo_comprobante="FACTURA",
                    serie="F001",
                    numero="0001-45",
                    fecha_emision="2026-01-10",
                ),
            )
        ],
        variables_calculo=RHDelegadoVariablesCalculoResult(
            tasa_renta_cip=Decimal("0.25"),
            tasa_aporte_codemu=Decimal("0.05"),
            tasa_fondo_comun=Decimal("0.10"),
        ),
    )

    out = FinanzasPresenter._map_rh_mensual_delegado_out(resultado)
    detalle = out.detalles[0]

    assert out.numero == 11
    assert detalle.expediente == "EXP-002"
    assert detalle.fecha_revision == "2026-01-05"
    assert detalle.fecha_presentacion == "2026-01-10"
    assert detalle.dictamen_revision == "CONFORME"
    assert detalle.numero_revision == 3
    assert detalle.numero_rh == "1"
    assert detalle.liquidacion_especifica_numero == 42
    assert detalle.comprobante_activo is not None
    assert detalle.comprobante_activo.tipo_comprobante == "FACTURA"
    assert detalle.comprobante_activo.serie == "F001"
    assert detalle.comprobante_activo.numero == "0001-45"
    assert detalle.comprobante_activo.fecha_emision == "2026-01-10"


# ── Contrato de datos de las candidatas del inspector ──────────────────────────
#
# Las candidatas del inspector perded el número de la liquidación específica y el
# comprobante activo, datos que las candidatas del delegado SÍ exponen. Además el
# DNI del inspector se declaraba obligatorio en el Result aunque el modelo lo
# permite nulo (ingenieros extranjeros). Estos tests fijan el contrato HTTP para
# que la paridad Inspector/Delegado no vuelva a romperse.
#
# Estos tests se ESCRIBEN pero NO se ejecutan en esta fase del change
# (la ejecución consolidada ocurre en la fase final de verificación).


@pytest.mark.django_db
def test_candidatas_inspector_exponen_numero_especifico_y_comprobante_activo(
    listar_flujo,
    inspector,
    perfil_ingeniero_inspector,
    liquidacion_visitas,
    liquidacion_general_io,
    liquidacion_io,
    liquidacion_inspector,
    comprobante_activo_io,
):
    """
    GIVEN: Un inspector con una IO candidata que tiene liquidación específica
           con número propio y comprobante activo.
    WHEN: Se listan las candidatas del inspector.
    THEN: El número específico y el comprobante tipado viajan en el Result, en el
          Schema Out y en el JSON, y el número específico NO se confunde con el
          número de revisión.
    """
    liquidacion_general_io.numero_revision = 3
    liquidacion_general_io.save(update_fields=["numero_revision"])

    resultado = listar_flujo.list_candidatos_inspector_proceso(
        cip=perfil_ingeniero_inspector.cip,
        periodo="2026-01",
    )

    assert resultado.total == 1
    candidata = resultado.candidatos[0]
    assert candidata.liquidacion_especifica_numero == liquidacion_io.numero
    assert candidata.numero_revision == 3
    assert candidata.liquidacion_especifica_numero != candidata.numero_revision
    assert candidata.comprobante_activo is not None
    assert candidata.comprobante_activo.tipo_comprobante == "FACTURA"
    assert candidata.comprobante_activo.serie == "F001"
    assert candidata.comprobante_activo.numero == "0001-45"
    assert candidata.comprobante_activo.fecha_emision == "2026-01-10"

    out = FinanzasPresenter.present_inspector_candidatos(resultado)
    assert out.candidatos[0].liquidacion_especifica_numero == liquidacion_io.numero
    assert out.candidatos[0].comprobante_activo is not None
    assert out.candidatos[0].comprobante_activo.tipo_comprobante == "FACTURA"
    assert out.candidatos[0].comprobante_activo.serie == "F001"
    assert out.candidatos[0].comprobante_activo.numero == "0001-45"
    assert out.candidatos[0].comprobante_activo.fecha_emision == "2026-01-10"

    payload = json.loads(out.model_dump_json())
    assert payload["candidatos"][0]["liquidacion_especifica_numero"] == liquidacion_io.numero
    assert payload["candidatos"][0]["comprobante_activo"]["serie"] == "F001"
    assert payload["candidatos"][0]["comprobante_activo"]["numero"] == "0001-45"


@pytest.mark.django_db
def test_candidatas_inspector_paginado_exponen_numero_especifico_y_comprobante_activo(
    listar_flujo,
    inspector,
    perfil_ingeniero_inspector,
    liquidacion_visitas,
    liquidacion_general_io,
    liquidacion_io,
    liquidacion_inspector,
    comprobante_activo_io,
):
    """
    GIVEN: Un inspector con una IO candidata con liquidación específica y
           comprobante activo.
    WHEN: Se listan las candidatas del inspector con paginación.
    THEN: La ruta paginada expone los mismos datos que la no paginada.
    """
    resultado = listar_flujo.list_candidatos_inspector_proceso_paginated(
        cip=perfil_ingeniero_inspector.cip,
        page=1,
        page_size=10,
        periodo="2026-01",
    )

    assert resultado.total == 1
    item = resultado.items[0]
    assert item.liquidacion_especifica_numero == liquidacion_io.numero
    assert item.comprobante_activo is not None
    assert item.comprobante_activo.serie == "F001"

    out = FinanzasPresenter.present_inspector_candidatos_paginated(resultado)
    assert out.items[0].liquidacion_especifica_numero == liquidacion_io.numero
    assert out.items[0].comprobante_activo is not None
    assert out.items[0].comprobante_activo.numero == "0001-45"


@pytest.mark.django_db
def test_candidatas_inspector_tolera_inspector_sin_dni(
    listar_flujo,
    inspector,
    perfil_ingeniero_inspector,
    liquidacion_visitas,
    liquidacion_inspector,
):
    """
    GIVEN: Un inspector cuyo PerfilIngeniero no tiene DNI (nullable en el modelo).
    WHEN: Se listan las candidatas del inspector.
    THEN: El endpoint responde con DNI nulo en vez de fallar la validación.
    """
    perfil_ingeniero_inspector.dni = None
    perfil_ingeniero_inspector.save(update_fields=["dni"])

    resultado = listar_flujo.list_candidatos_inspector_proceso(
        cip=perfil_ingeniero_inspector.cip,
        periodo="2026-01",
    )

    assert resultado.inspector_dni is None
    assert resultado.candidatos[0].inspector_dni is None

    out = FinanzasPresenter.present_inspector_candidatos(resultado)
    assert out.inspector_dni is None
    assert out.candidatos[0].inspector_dni is None

    payload = json.loads(out.model_dump_json())
    assert payload["inspector_dni"] is None
    assert payload["candidatos"][0]["inspector_dni"] is None
