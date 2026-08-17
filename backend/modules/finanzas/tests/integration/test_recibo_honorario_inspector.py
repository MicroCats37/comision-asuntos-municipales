"""
Integration tests for ReciboHonorarioInspector — escala de descuento, cálculo
y endpoints /finanzas/recibos-inspectores.
"""
import uuid
from datetime import date
from decimal import Decimal

import pytest
from ninja.testing import TestClient
from config.api import api

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
from modules.liquidaciones.domain.models.inspector import (
    Inspector,
    LiquidacionInspector,
)
from modules.liquidaciones.domain.models.tipo_liquidacion import TipoLiquidacion
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
    ReciboHonorarioInspector,
)
from django.contrib.auth import get_user_model


# ── Escala fixtures ────────────────────────────────────────────────────────────

@pytest.fixture
def escala_descuento(db):
    """Escala vigente con los rangos iniciales del seed."""
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


# ── Common fixtures ────────────────────────────────────────────────────────────

@pytest.fixture
def api_client(db):
    return TestClient(api)


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
        denominacion="Proyecto IO Test",
        nombre_propietario="Propietario IO SAC",
        direccion="Av. Test 123",
        distrito_id=ubigeo_test.id,
        entidad_tipo_documento="RUC",
        entidad_numero_documento="20456789012",
        entidad_razon_social="Propietario IO SAC",
    )


@pytest.fixture
def usuario_test(db):
    User = get_user_model()
    return User.objects.create_user(
        username="inspector_io",
        email="inspector_io@test.com",
        password="testpass123",
        dni="76543210",
    )


@pytest.fixture
def perfil_ingeniero_inspector(db, usuario_test):
    return PerfilIngeniero.objects.create(
        usuario=usuario_test,
        apellido_paterno="Quispe",
        apellido_materno="Rojas",
        nombres="María",
        cip="CIP-77777",
        dni="76543210",
    )


@pytest.fixture
def especialidad_revision(db):
    return EspecialidadRevision.objects.create(
        codigo="E01",
        slug="estructuras",
        nombre="Estructuras",
    )


@pytest.fixture
def inspector(db, perfil_ingeniero_inspector):
    return Inspector.objects.create(perfil_ingeniero=perfil_ingeniero_inspector)


@pytest.fixture
def tipo_inspeccion_obra(db):
    return TipoLiquidacion.objects.get_or_create(
        codigo=TipoLiquidacionConst.INSPECCION_OBRA,
        defaults={"nombre": "Inspección de Obra"},
    )[0]


@pytest.fixture
def usuario_liquidacion(db):
    User = get_user_model()
    return User.objects.create_user(
        username="liq_io",
        email="liq_io@test.com",
        password="testpass123",
        dni="11223344",
    )


@pytest.fixture
def liquidacion_general_io(
    db, proyecto_test, municipalidad_test, tipo_inspeccion_obra, usuario_liquidacion
):
    """LiquidacionGeneral de tipo INSPECCION_OBRA."""
    return LiquidacionGeneral.objects.create(
        proyecto=proyecto_test,
        municipalidad=municipalidad_test,
        tipo_liquidacion=tipo_inspeccion_obra,
        usuario_creador=usuario_liquidacion,
        expediente="EXP-IO-2026-001",
        estado="REGISTRADO",
        sub_total=Decimal("1000.00"),
        total=Decimal("1180.00"),
    )


@pytest.fixture
def liquidacion_visitas(db, liquidacion_general_io, tipo_inspeccion_obra):
    """LiquidacionPorCategoriaVisitas con 10 visitas programadas."""
    tarifa_base = TarifaLiquidacionBase.objects.create(
        tipo_liquidacion=tipo_inspeccion_obra,
        periodo_inicio=date(2024, 1, 1),
        periodo_fin=None,
    )
    tarifa_visitas = TarifaPorCategoriaVisitas.objects.create(
        tarifa_base=tarifa_base,
        porcentaje_uit=Decimal("0.05"),
        categoria_visitas="INSPECCION",
    )
    return LiquidacionPorCategoriaVisitas.objects.create(
        liquidacion_general=liquidacion_general_io,
        cantidad_visitas=10,
        porcentaje_uit=Decimal("0.05"),
        categoria="A",
        tarifa_aplicada=tarifa_visitas,
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


# ── Escala / Rango logic tests ─────────────────────────────────────────────────

@pytest.mark.django_db
class TestGetRangoParaMonto:
    """Tests de la resolución de rango según monto."""

    def test_rango_15_por_ciento(self, escala_descuento):
        from modules.finanzas.domain.services.finanzas_core_service import (
            FinanzasCoreService,
        )

        service = FinanzasCoreService()
        rango = service.get_rango_para_monto(escala_descuento, Decimal("7999.99"))
        assert rango.porcentaje_descuento == Decimal("0.15")

    def test_rango_20_por_ciento(self, escala_descuento):
        from modules.finanzas.domain.services.finanzas_core_service import (
            FinanzasCoreService,
        )

        service = FinanzasCoreService()
        rango = service.get_rango_para_monto(escala_descuento, Decimal("8000.00"))
        assert rango.porcentaje_descuento == Decimal("0.20")
        rango = service.get_rango_para_monto(escala_descuento, Decimal("14999.99"))
        assert rango.porcentaje_descuento == Decimal("0.20")

    def test_rango_30_por_ciento(self, escala_descuento):
        from modules.finanzas.domain.services.finanzas_core_service import (
            FinanzasCoreService,
        )

        service = FinanzasCoreService()
        rango = service.get_rango_para_monto(escala_descuento, Decimal("15000.00"))
        assert rango.porcentaje_descuento == Decimal("0.30")

    def test_rango_40_por_ciento_sin_tope(self, escala_descuento):
        from modules.finanzas.domain.services.finanzas_core_service import (
            FinanzasCoreService,
        )

        service = FinanzasCoreService()
        rango = service.get_rango_para_monto(escala_descuento, Decimal("30000.00"))
        assert rango.porcentaje_descuento == Decimal("0.40")
        rango = service.get_rango_para_monto(escala_descuento, Decimal("999999.00"))
        assert rango.porcentaje_descuento == Decimal("0.40")

    def test_escala_vigente(self, escala_descuento):
        from modules.finanzas.domain.services.finanzas_core_service import (
            FinanzasCoreService,
        )

        service = FinanzasCoreService()
        escala = service.get_escala_descuento_vigente(fecha=date(2026, 6, 1))
        assert escala is not None
        assert escala.nombre == "Escala 2026"
        assert escala.rangos.count() == 4


# ── Flow / Orchestrator tests ──────────────────────────────────────────────────

@pytest.mark.django_db
class TestCrearReciboInspector:
    """Tests del cálculo del ReciboHonorarioInspector."""

    def test_calculo_correcto(
        self, liquidacion_inspector, liquidacion_visitas, escala_descuento
    ):
        """
        sub_total=1000.00, visitas=10, inspecciones_mes=4:
            costo_por_inspeccion = 100.00
            monto_bruto = 400.00
            saldo = 6
            sub_total = 400.00 → 15% → descuento 60.00, honorarios 340.00
        """
        from modules.finanzas.domain.services.finanzas_core_service import (
            FinanzasCoreService,
        )
        from modules.finanzas.domain.services.recibo_honorario_flujo import (
            ReciboHonorarioInspectorFlujo,
        )

        flujo = ReciboHonorarioInspectorFlujo(core_service=FinanzasCoreService())
        recibo = flujo.crear_recibo_inspector(
            liquidacion_inspector_id=liquidacion_inspector.id,
            inspecciones_mes=4,
        )

        assert isinstance(recibo, ReciboHonorarioInspector)
        assert recibo.inspecciones_programadas == 10
        assert recibo.costo_por_inspeccion == Decimal("100.00")
        assert recibo.inspecciones_mes == 4
        assert recibo.monto_bruto == Decimal("400.00")
        assert recibo.inspecciones_pagadas == 0
        assert recibo.saldo_inspecciones == 6
        assert recibo.sub_total == Decimal("400.00")
        assert recibo.tasa_descuento_aplicada == Decimal("0.1500")
        assert recibo.descuento == Decimal("60.00")
        assert recibo.honorarios == Decimal("340.00")

    def test_rango_20_por_ciento(
        self, liquidacion_general_io, liquidacion_visitas, inspector,
        especialidad_revision, escala_descuento,
    ):
        """
        Con sub_total=10000.00 el descuento cae en el rango de 20%.
        """
        liquidacion_general_io.sub_total = Decimal("10000.00")
        liquidacion_general_io.save()

        li = LiquidacionInspector.objects.create(
            liquidacion=liquidacion_visitas,
            inspector=inspector,
            especialidad_revision=especialidad_revision,
        )

        from modules.finanzas.domain.services.finanzas_core_service import (
            FinanzasCoreService,
        )
        from modules.finanzas.domain.services.recibo_honorario_flujo import (
            ReciboHonorarioInspectorFlujo,
        )

        flujo = ReciboHonorarioInspectorFlujo(core_service=FinanzasCoreService())
        recibo = flujo.crear_recibo_inspector(
            liquidacion_inspector_id=li.id,
            inspecciones_mes=10,
        )

        assert recibo.sub_total == Decimal("10000.00")
        assert recibo.tasa_descuento_aplicada == Decimal("0.2000")
        assert recibo.descuento == Decimal("2000.00")
        assert recibo.honorarios == Decimal("8000.00")

    def test_404_sin_liquidacion_inspector(self, escala_descuento):
        from modules.finanzas.domain.services.finanzas_core_service import (
            FinanzasCoreService,
        )
        from modules.finanzas.domain.services.recibo_honorario_flujo import (
            ReciboHonorarioInspectorFlujo,
        )
        from ninja.errors import HttpError

        flujo = ReciboHonorarioInspectorFlujo(core_service=FinanzasCoreService())
        with pytest.raises(HttpError) as excinfo:
            flujo.crear_recibo_inspector(
                liquidacion_inspector_id=uuid.uuid4(),
                inspecciones_mes=1,
            )
        assert excinfo.value.status_code == 404

    def test_400_sin_escala_vigente(self, liquidacion_inspector):
        """
        Sin escala vigente → HttpError 400.
        """
        from modules.finanzas.domain.services.finanzas_core_service import (
            FinanzasCoreService,
        )
        from modules.finanzas.domain.services.recibo_honorario_flujo import (
            ReciboHonorarioInspectorFlujo,
        )
        from ninja.errors import HttpError

        flujo = ReciboHonorarioInspectorFlujo(core_service=FinanzasCoreService())
        with pytest.raises(HttpError) as excinfo:
            flujo.crear_recibo_inspector(
                liquidacion_inspector_id=liquidacion_inspector.id,
                inspecciones_mes=1,
            )
        assert excinfo.value.status_code == 400


# ── Orchestrator result test ────────────────────────────────────────────────────

@pytest.mark.django_db
def test_orchestrator_result_anidados(
    liquidacion_inspector, liquidacion_general_io, liquidacion_io,
    inspector, especialidad_revision, escala_descuento,
):
    """
    crear_recibo_inspector_proceso construye el Result con anidados
    (liquidacion_general, liquidacion_especifica de la IO, inspector, especialidad).
    """
    from modules.finanzas.domain.services.finanzas_orchestrator import (
        FinanzasOrchestrator,
    )
    from modules.finanzas.domain.services.flujos.finanzas_flujo import FinanzasFlujo
    from modules.finanzas.domain.services.finanzas_core_service import (
        FinanzasCoreService,
    )

    flujo = FinanzasFlujo(core=FinanzasCoreService())
    orch = FinanzasOrchestrator(flujo=flujo, core=FinanzasCoreService())

    result = orch.crear_recibo_inspector_proceso(
        liquidacion_inspector_id=liquidacion_inspector.id,
        inspecciones_mes=2,
    )

    assert result.liquidacion_inspector_id == str(liquidacion_inspector.id)
    assert result.liquidacion_general.id == str(liquidacion_general_io.id)
    assert result.liquidacion_general.tipo_liquidacion.codigo == "INSPECCION_OBRA"
    # liquidacion_especifica es la IO (id + numero)
    assert result.liquidacion_especifica.id == str(liquidacion_io.id)
    assert result.liquidacion_especifica.numero == liquidacion_io.numero
    assert result.inspector.id == str(inspector.id)
    assert result.inspector.cip == inspector.perfil_ingeniero.cip
    assert result.inspector.dni == inspector.perfil_ingeniero.dni
    assert result.especialidad.id == str(especialidad_revision.id)
    # cálculo: costo=100, mes=2 → monto_bruto=200 → 15% → 30/170
    assert result.calculo.monto_bruto == Decimal("200.00")
    assert result.calculo.descuento == Decimal("30.00")
    assert result.calculo.honorarios == Decimal("170.00")


# ── API E2E tests ──────────────────────────────────────────────────────────────

@pytest.mark.django_db
def test_e2e_post_recibo_inspector(
    api_client, liquidacion_inspector, liquidacion_general_io, liquidacion_io,
    inspector, especialidad_revision, escala_descuento,
):
    """
    POST /finanzas/recibos-inspectores crea el recibo y responde el schema completo.
    """
    response = api_client.post(
        "/finanzas/recibos-inspectores",
        json={
            "liquidacion_inspector_id": str(liquidacion_inspector.id),
            "inspecciones_mes": 4,
        },
    )

    assert response.status_code == 200, (
        f"Expected 200, got {response.status_code}: {response.content}"
    )
    data = response.json()
    assert data["success"] is True

    recibo = data["data"]
    assert recibo["liquidacion_inspector_id"] == str(liquidacion_inspector.id)
    calculo = recibo["calculo"]
    assert calculo["inspecciones_programadas"] == 10
    assert calculo["costo_por_inspeccion"] == "100.00"
    assert calculo["inspecciones_mes"] == 4
    assert calculo["monto_bruto"] == "400.00"
    assert calculo["inspecciones_pagadas"] == 0
    assert calculo["saldo_inspecciones"] == 6
    assert calculo["sub_total"] == "400.00"
    assert calculo["tasa_descuento_aplicada"] == "0.1500"
    assert calculo["descuento"] == "60.00"
    assert calculo["honorarios"] == "340.00"

    # Anidados homogéneos al listado
    assert recibo["liquidacion_general"]["id"] == str(liquidacion_general_io.id)
    assert recibo["liquidacion_general"]["tipo_liquidacion"]["codigo"] == "INSPECCION_OBRA"
    assert recibo["liquidacion_especifica"]["id"] == str(liquidacion_io.id)
    assert recibo["liquidacion_especifica"]["numero"] == liquidacion_io.numero
    assert recibo["inspector"]["id"] == str(inspector.id)
    assert recibo["inspector"]["cip"] == inspector.perfil_ingeniero.cip
    assert recibo["inspector"]["dni"] == inspector.perfil_ingeniero.dni
    assert recibo["inspector"]["nombre_completo"] == (
        inspector.perfil_ingeniero.nombre_completo
    )
    assert recibo["especialidad"]["id"] == str(especialidad_revision.id)


@pytest.mark.django_db
def test_e2e_post_recibo_inspector_404(api_client, escala_descuento):
    """
    POST con liquidacion_inspector_id inexistente → 404.
    """
    fake_id = uuid.uuid4()
    response = api_client.post(
        "/finanzas/recibos-inspectores",
        json={
            "liquidacion_inspector_id": str(fake_id),
            "inspecciones_mes": 1,
        },
    )

    assert response.status_code == 404, (
        f"Expected 404, got {response.status_code}: {response.content}"
    )


@pytest.mark.django_db
def test_e2e_get_recibos_inspectores_paginated(
    api_client, liquidacion_inspector, liquidacion_general_io, liquidacion_io,
    escala_descuento,
):
    """
    GET /finanzas/recibos-inspectores devuelve PaginatedData.
    """
    for mes in (1, 2, 3):
        api_client.post(
            "/finanzas/recibos-inspectores",
            json={
                "liquidacion_inspector_id": str(liquidacion_inspector.id),
                "inspecciones_mes": mes,
            },
        )

    response = api_client.get("/finanzas/recibos-inspectores?page=1&page_size=2")
    assert response.status_code == 200, (
        f"Expected 200, got {response.status_code}: {response.content}"
    )
    data = response.json()
    assert data["success"] is True

    paginated = data["data"]
    assert len(paginated["items"]) == 2
    assert paginated["total"] == 3
    assert paginated["page"] == 1
    assert paginated["page_size"] == 2
    assert paginated["total_pages"] == 2


@pytest.mark.django_db
def test_e2e_get_recibos_inspectores_filters(
    api_client, liquidacion_inspector, liquidacion_general_io, liquidacion_io,
    inspector, escala_descuento,
):
    """
    GET con ?inspector_id= y ?liquidacion_id= filtra correctamente.
    """
    api_client.post(
        "/finanzas/recibos-inspectores",
        json={
            "liquidacion_inspector_id": str(liquidacion_inspector.id),
            "inspecciones_mes": 2,
        },
    )

    # Filtro por inspector
    response = api_client.get(
        f"/finanzas/recibos-inspectores?inspector_id={inspector.id}"
    )
    assert response.status_code == 200
    items = response.json()["data"]["items"]
    assert all(str(item["inspector"]["id"]) == str(inspector.id) for item in items)

    # Filtro por liquidacion general
    response2 = api_client.get(
        f"/finanzas/recibos-inspectores?liquidacion_id={liquidacion_general_io.id}"
    )
    assert response2.status_code == 200
    items2 = response2.json()["data"]["items"]
    assert all(
        str(item["liquidacion_general"]["id"]) == str(liquidacion_general_io.id)
        for item in items2
    )


@pytest.mark.django_db
def test_e2e_get_recibos_inspectores_empty(api_client):
    """
    GET sin datos → items=[], total=0.
    """
    response = api_client.get("/finanzas/recibos-inspectores?page=1&page_size=10")
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert data["data"]["items"] == []
    assert data["data"]["total"] == 0
    assert data["data"]["total_pages"] == 0
