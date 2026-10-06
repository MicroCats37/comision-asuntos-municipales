"""
Integration tests for RH Detalle Inspector — list detail rows with CIP filtering.

Tests the core service and orchestrator for the flat detail list endpoint:
GET /finanzas/recibos-inspectores/detalle

Covers:
- list_detalle_honorario_inspector_paginated with inspector_cip filter
- list_rh_detalle_inspectores_proceso with inspector_cip filter
- Precedence: inspector_cip wins over inspector_id when both are provided
- Filter chip display in frontend uses CIP
"""
import pytest
import uuid
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
from modules.liquidaciones.domain.models.inspector import Inspector
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
from modules.finanzas.domain.services.finanzas_core_service import FinanzasCoreService
from modules.finanzas.domain.services.finanzas_orchestrator import FinanzasOrchestrator
from modules.finanzas.domain.services.flujos.finanzas_flujo import FinanzasFlujo
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
    """Second proyecto for the second inspector's liquidacion."""
    return Proyecto.objects.create(
        nombre_propietario="Propietario Dos IO SAC",
        direccion="Av. Segunda 456",
        distrito=ubigeo_test,
        entidad_tipo_documento="RUC",
        entidad_numero_documento="20456789013",
        entidad_razon_social="Propietario Dos IO SAC",
    )


@pytest.fixture
def usuario_inspector(db):
    User = get_user_model()
    return User.objects.create_user(
        username="inspector_detalle",
        email="inspector_detalle@test.com",
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
def segundo_usuario_inspector(db):
    User = get_user_model()
    return User.objects.create_user(
        username="inspector_detalle_2",
        email="inspector_detalle_2@test.com",
        password="testpass123",
        dni="11223344",
    )


@pytest.fixture
def segundo_perfil_ingeniero_inspector(db, segundo_usuario_inspector):
    return PerfilIngeniero.objects.create(
        usuario=segundo_usuario_inspector,
        apellido_paterno="López",
        apellido_materno="Pérez",
        nombres="Carlos",
        cip="CIP-99999",
        dni="11223344",
    )


@pytest.fixture
def segundo_inspector(db, segundo_perfil_ingeniero_inspector):
    return Inspector.objects.create(perfil_ingeniero=segundo_perfil_ingeniero_inspector)


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
        username="liq_inspector_detalle",
        email="liq_inspector_detalle@test.com",
        password="testpass123",
        dni="99887766",
    )


@pytest.fixture
def liquidacion_general_io(
    db, proyecto_test, municipalidad_test, tipo_inspeccion_obra, usuario_liquidacion
):
    return LiquidacionGeneral.objects.create(
        proyecto=proyecto_test,
        municipalidad=municipalidad_test,
        tipo_liquidacion=tipo_inspeccion_obra,
        usuario_creador=usuario_liquidacion,
        expediente="EXP-INS-DET-001",
        estado="REGISTRADO",
        sub_total=Decimal("1000.00"),
        total=Decimal("1000.00"),
        numero_revision=1,
    )


@pytest.fixture
def segunda_liquidacion_general_io(
    db, segundo_proyecto_test, municipalidad_test, tipo_inspeccion_obra, usuario_liquidacion
):
    """Second liquidacion for the second inspector."""
    return LiquidacionGeneral.objects.create(
        proyecto=segundo_proyecto_test,
        municipalidad=municipalidad_test,
        tipo_liquidacion=tipo_inspeccion_obra,
        usuario_creador=usuario_liquidacion,
        expediente="EXP-INS-DET-002",
        estado="REGISTRADO",
        sub_total=Decimal("2000.00"),
        total=Decimal("2000.00"),
        numero_revision=1,
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
    """LiquidacionPorCategoriaVisitas con 10 visitas."""
    return LiquidacionPorCategoriaVisitas.objects.create(
        liquidacion_general=liquidacion_general_io,
        cantidad_visitas=10,
        porcentaje_uit=Decimal("0.05"),
        categoria="A",
        tarifa_aplicada=tarifa_visitas_io,
    )


@pytest.fixture
def segunda_liquidacion_visitas(db, segunda_liquidacion_general_io, tarifa_visitas_io):
    """Second LiquidacionPorCategoriaVisitas for the second inspector."""
    return LiquidacionPorCategoriaVisitas.objects.create(
        liquidacion_general=segunda_liquidacion_general_io,
        cantidad_visitas=8,
        porcentaje_uit=Decimal("0.05"),
        categoria="B",
        tarifa_aplicada=tarifa_visitas_io,
    )


@pytest.fixture
def core_service(db):
    return FinanzasCoreService()


@pytest.fixture
def orquestador(core_service):
    flujo = FinanzasFlujo(core=core_service)
    return FinanzasOrchestrator(flujo=flujo, core=core_service)


# ── Tests ────────────────────────────────────────────────────────────────────────

@pytest.mark.django_db
def test_detalle_inspector_filtro_por_cip(
    db,
    core_service,
    perfil_ingeniero_inspector,
    segundo_perfil_ingeniero_inspector,
    inspector,
    segundo_inspector,
    liquidacion_visitas,
    segunda_liquidacion_visitas,
    escala_descuento_15,
):
    """
    GIVEN: Two inspector records with different CIPs, each with DetalleHonorarioInspector rows
    WHEN:  list_detalle_honorario_inspector_paginated is called with inspector_cip="CIP-88888"
    THEN:  Only rows belonging to the CIP-88888 inspector are returned
    """
    # Create a ReciboHonorarioInspectorMensual for each inspector
    recibo1 = ReciboHonorarioInspectorMensual.objects.create(
        inspector=inspector,
        periodo=2026,
        mes=1,
        escala_descuento=escala_descuento_15,
        sub_total=Decimal("1000.00"),
        descuento=Decimal("150.00"),
        honorarios=Decimal("850.00"),
    )
    recibo2 = ReciboHonorarioInspectorMensual.objects.create(
        inspector=segundo_inspector,
        periodo=2026,
        mes=1,
        escala_descuento=escala_descuento_15,
        sub_total=Decimal("2000.00"),
        descuento=Decimal("300.00"),
        honorarios=Decimal("1700.00"),
    )

    # Create detalle rows
    detalle1 = DetalleHonorarioInspector.objects.create(
        recibo_mensual=recibo1,
        liquidacion_por_categoria_visitas=liquidacion_visitas,
        inspecciones_programadas=5,
        inspecciones_liquidadas=3,
        inspecciones_pagadas_hasta_mes_anterior=0,
        saldo_restante=2,
        importe_bruto=Decimal("1500.00"),
        costo_por_inspeccion=Decimal("500.00"),
        monto_contribuido=Decimal("750.00"),
        sub_total=Decimal("1500.00"),
        descuento=Decimal("225.00"),
        honorarios=Decimal("1275.00"),
    )
    detalle2 = DetalleHonorarioInspector.objects.create(
        recibo_mensual=recibo2,
        liquidacion_por_categoria_visitas=segunda_liquidacion_visitas,
        inspecciones_programadas=8,
        inspecciones_liquidadas=5,
        inspecciones_pagadas_hasta_mes_anterior=0,
        saldo_restante=3,
        importe_bruto=Decimal("2500.00"),
        costo_por_inspeccion=Decimal("500.00"),
        monto_contribuido=Decimal("1250.00"),
        sub_total=Decimal("2500.00"),
        descuento=Decimal("375.00"),
        honorarios=Decimal("2125.00"),
    )

    # Filter by CIP CIP-88888
    rows, total = core_service.list_detalle_honorario_inspector_paginated(
        page=1,
        page_size=20,
        inspector_cip="CIP-88888",
    )

    assert total == 1
    assert len(rows) == 1
    assert rows[0].id == detalle1.id


@pytest.mark.django_db
def test_detalle_inspector_cip_toma_precedencia_sobre_inspector_id(
    db,
    core_service,
    perfil_ingeniero_inspector,
    segundo_perfil_ingeniero_inspector,
    inspector,
    segundo_inspector,
    liquidacion_visitas,
    segunda_liquidacion_visitas,
    escala_descuento_15,
):
    """
    GIVEN: Two inspector records with different CIPs and UUIDs
    WHEN:  list_detalle_honorario_inspector_paginated is called with BOTH inspector_cip and inspector_id
           (but the UUID corresponds to the OTHER inspector)
    THEN:  The CIP filter takes precedence and rows for the other inspector are returned
    """
    # Create a ReciboHonorarioInspectorMensual for each inspector
    recibo1 = ReciboHonorarioInspectorMensual.objects.create(
        inspector=inspector,
        periodo=2026,
        mes=1,
        escala_descuento=escala_descuento_15,
        sub_total=Decimal("1000.00"),
        descuento=Decimal("150.00"),
        honorarios=Decimal("850.00"),
    )
    recibo2 = ReciboHonorarioInspectorMensual.objects.create(
        inspector=segundo_inspector,
        periodo=2026,
        mes=1,
        escala_descuento=escala_descuento_15,
        sub_total=Decimal("2000.00"),
        descuento=Decimal("300.00"),
        honorarios=Decimal("1700.00"),
    )

    detalle1 = DetalleHonorarioInspector.objects.create(
        recibo_mensual=recibo1,
        liquidacion_por_categoria_visitas=liquidacion_visitas,
        inspecciones_programadas=5,
        inspecciones_liquidadas=3,
        inspecciones_pagadas_hasta_mes_anterior=0,
        saldo_restante=2,
        importe_bruto=Decimal("1500.00"),
        costo_por_inspeccion=Decimal("500.00"),
        monto_contribuido=Decimal("750.00"),
        sub_total=Decimal("1500.00"),
        descuento=Decimal("225.00"),
        honorarios=Decimal("1275.00"),
    )
    detalle2 = DetalleHonorarioInspector.objects.create(
        recibo_mensual=recibo2,
        liquidacion_por_categoria_visitas=segunda_liquidacion_visitas,
        inspecciones_programadas=8,
        inspecciones_liquidadas=5,
        inspecciones_pagadas_hasta_mes_anterior=0,
        saldo_restante=3,
        importe_bruto=Decimal("2500.00"),
        costo_por_inspeccion=Decimal("500.00"),
        monto_contribuido=Decimal("1250.00"),
        sub_total=Decimal("2500.00"),
        descuento=Decimal("375.00"),
        honorarios=Decimal("2125.00"),
    )

    # Call with both params — CIP takes precedence
    rows, total = core_service.list_detalle_honorario_inspector_paginated(
        page=1,
        page_size=20,
        inspector_id=int(segundo_inspector.id),  # This is the OTHER inspector
        inspector_cip="CIP-88888",              # CIP CIP-88888 = inspector1
    )

    # Should return rows for CIP CIP-88888, NOT for segundo_inspector
    assert total == 1
    assert rows[0].id == detalle1.id


@pytest.mark.django_db
def test_detalle_inspector_orchestrator_filtro_cip(
    db,
    orquestador,
    perfil_ingeniero_inspector,
    segundo_perfil_ingeniero_inspector,
    inspector,
    segundo_inspector,
    liquidacion_visitas,
    segunda_liquidacion_visitas,
    escala_descuento_15,
):
    """
    GIVEN: Two inspectors with different CIPs, each with detalle rows
    WHEN:  list_rh_detalle_inspectores_proceso is called with inspector_cip
    THEN:  Only rows matching the CIP are returned, with correct CIP in output
    """
    # Create a ReciboHonorarioInspectorMensual for each inspector
    recibo1 = ReciboHonorarioInspectorMensual.objects.create(
        inspector=inspector,
        periodo=2026,
        mes=2,
        escala_descuento=escala_descuento_15,
        sub_total=Decimal("1000.00"),
        descuento=Decimal("150.00"),
        honorarios=Decimal("850.00"),
    )
    recibo2 = ReciboHonorarioInspectorMensual.objects.create(
        inspector=segundo_inspector,
        periodo=2026,
        mes=2,
        escala_descuento=escala_descuento_15,
        sub_total=Decimal("2000.00"),
        descuento=Decimal("300.00"),
        honorarios=Decimal("1700.00"),
    )

    DetalleHonorarioInspector.objects.create(
        recibo_mensual=recibo1,
        liquidacion_por_categoria_visitas=liquidacion_visitas,
        inspecciones_programadas=5,
        inspecciones_liquidadas=3,
        inspecciones_pagadas_hasta_mes_anterior=0,
        saldo_restante=2,
        importe_bruto=Decimal("1500.00"),
        costo_por_inspeccion=Decimal("500.00"),
        monto_contribuido=Decimal("750.00"),
        sub_total=Decimal("1500.00"),
        descuento=Decimal("225.00"),
        honorarios=Decimal("1275.00"),
    )
    DetalleHonorarioInspector.objects.create(
        recibo_mensual=recibo2,
        liquidacion_por_categoria_visitas=segunda_liquidacion_visitas,
        inspecciones_programadas=8,
        inspecciones_liquidadas=5,
        inspecciones_pagadas_hasta_mes_anterior=0,
        saldo_restante=3,
        importe_bruto=Decimal("2500.00"),
        costo_por_inspeccion=Decimal("500.00"),
        monto_contribuido=Decimal("1250.00"),
        sub_total=Decimal("2500.00"),
        descuento=Decimal("375.00"),
        honorarios=Decimal("2125.00"),
    )

    results, total = orquestador.list_rh_detalle_inspectores_proceso(
        page=1,
        page_size=20,
        inspector_cip="CIP-88888",
    )

    assert total == 1
    assert len(results) == 1
    assert results[0].inspector_liquidacion.inspector.cip == "CIP-88888"
    assert results[0].inspector_liquidacion.inspector.nombre_completo == "María Quispe Rojas"


@pytest.mark.django_db
def test_detalle_inspector_filtro_cip_sin_resultados(
    db,
    core_service,
    perfil_ingeniero_inspector,
    inspector,
    liquidacion_visitas,
    escala_descuento_15,
):
    """
    GIVEN: DetalleHonorarioInspector rows exist for CIP CIP-88888
    WHEN:  list_detalle_honorario_inspector_paginated is called with non-existent CIP
    THEN:  Empty result is returned
    """
    # Create a ReciboHonorarioInspectorMensual
    recibo1 = ReciboHonorarioInspectorMensual.objects.create(
        inspector=inspector,
        periodo=2026,
        mes=3,
        escala_descuento=escala_descuento_15,
        sub_total=Decimal("1000.00"),
        descuento=Decimal("150.00"),
        honorarios=Decimal("850.00"),
    )

    DetalleHonorarioInspector.objects.create(
        recibo_mensual=recibo1,
        liquidacion_por_categoria_visitas=liquidacion_visitas,
        inspecciones_programadas=5,
        inspecciones_liquidadas=3,
        inspecciones_pagadas_hasta_mes_anterior=0,
        saldo_restante=2,
        importe_bruto=Decimal("1500.00"),
        costo_por_inspeccion=Decimal("500.00"),
        monto_contribuido=Decimal("750.00"),
        sub_total=Decimal("1500.00"),
        descuento=Decimal("225.00"),
        honorarios=Decimal("1275.00"),
    )

    rows, total = core_service.list_detalle_honorario_inspector_paginated(
        page=1,
        page_size=20,
        inspector_cip="NONEXISTENT",
    )

    assert total == 0
    assert len(rows) == 0
