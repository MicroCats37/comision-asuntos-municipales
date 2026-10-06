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
)
from modules.finanzas.domain.schemas import RHInspectorCotizarIn, RHInspectorCotizarItemIn
from django.contrib.auth import get_user_model


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

