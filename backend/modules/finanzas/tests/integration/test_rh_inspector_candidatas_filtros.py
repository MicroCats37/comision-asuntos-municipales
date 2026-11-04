"""
Integration tests for the RH INSPECTOR candidates filters: active receipt
(serie / numero) and entity document.

"Comprobante vigente" = a `LiquidacionComprobante` row with `activo=True` for
that liquidacion (at most one, enforced by the partial unique constraint
`unique_liquidacion_comprobante_activo`). Replaced receipts stay in the
history with `activo=False` and must NEVER match the filter.

The filter is implemented with `Exists` (not a JOIN) so a liquidacion with
several receipts is NOT duplicated and `total` stays truthful.

Covers:
- serie / numero filters match the ACTIVE receipt only
- a liquidation with an active + a replaced receipt appears exactly once
- the entity-document filter applies (icontains on the project snapshot)
"""
import pytest
from datetime import date
from decimal import Decimal

from django.contrib.auth import get_user_model

from modules.entidades.domain.models.municipalidad import Municipalidad
from modules.entidades.domain.models.ubigeo import (
    UbigeoDepartamento,
    UbigeoDistrito,
    UbigeoProvincia,
)
from modules.liquidaciones.domain.constants import TipoLiquidacion as TipoLiquidacionConst
from modules.liquidaciones.domain.models.inspector import (
    Inspector,
    LiquidacionInspector,
)
from modules.liquidaciones.domain.models.liquidacion.liquidacion_general.comprobante import (
    LiquidacionComprobante,
)
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
from modules.liquidaciones.domain.models.proyecto import Proyecto
from modules.liquidaciones.domain.models.tipo_liquidacion import (
    TipoLiquidacion as TipoLiquidacionModel,
)
from modules.usuarios.domain.models.perfil_ingeniero import (
    EspecialidadRevision,
    PerfilIngeniero,
)
from modules.finanzas.domain.services.flujos.rh_inspector_mensual_flujo import (
    RHInspectorMensualListFlujo,
)
from modules.finanzas.domain.services.finanzas_core_service import FinanzasCoreService


# ── Fixtures ────────────────────────────────────────────────────────────────────

@pytest.fixture
def ubigeo_test(db):
    depto = UbigeoDepartamento.objects.create(nombre="LIMA")
    prov = UbigeoProvincia.objects.create(departamento=depto, nombre="LIMA")
    return UbigeoDistrito.objects.create(
        provincia=prov, nombre="MIRAFLORES", ubigeo="150132"
    )


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
def usuario_liquidacion(db):
    User = get_user_model()
    return User.objects.create_user(
        username="liq_candidatas",
        email="liq_candidatas@test.com",
        password="testpass123",
        dni="11223344",
    )


@pytest.fixture
def perfil_ingeniero_inspector(db):
    User = get_user_model()
    usuario = User.objects.create_user(
        username="inspector_candidatas",
        email="inspector_candidatas@test.com",
        password="testpass123",
        dni="76543210",
    )
    return PerfilIngeniero.objects.create(
        usuario=usuario,
        apellido_paterno="Quispe",
        apellido_materno="Rojas",
        nombres="María",
        cip="CIP-99999",
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
def liquidacion_general_io(
    db, proyecto_test, municipalidad_test, tipo_inspeccion_obra, usuario_liquidacion
):
    return LiquidacionGeneral.objects.create(
        proyecto=proyecto_test,
        municipalidad=municipalidad_test,
        tipo_liquidacion=tipo_inspeccion_obra,
        usuario_creador=usuario_liquidacion,
        expediente="EXP-CAND-FILT-001",
        estado="REGISTRADO",
        sub_total=Decimal("1000.00"),
        total=Decimal("1180.00"),
    )


@pytest.fixture
def liquidacion_visitas(db, liquidacion_general_io, tarifa_visitas_io):
    return LiquidacionPorCategoriaVisitas.objects.create(
        liquidacion_general=liquidacion_general_io,
        cantidad_visitas=10,
        porcentaje_uit=Decimal("0.05"),
        categoria="A",
        tarifa_aplicada=tarifa_visitas_io,
    )


@pytest.fixture
def liquidacion_inspector(
    db, liquidacion_visitas, inspector, especialidad_revision
):
    return LiquidacionInspector.objects.create(
        liquidacion=liquidacion_visitas,
        inspector=inspector,
        especialidad_revision=especialidad_revision,
    )


@pytest.fixture
def rh_inspector_mensual_flujo():
    return RHInspectorMensualListFlujo(core=FinanzasCoreService())


@pytest.fixture
def liquidacion_con_comprobantes(liquidacion_general_io):
    """
    Añade DOS comprobantes a la liquidación:
    - F001 / 000123 → ACTIVO (el vigente)
    - F002 / 000456 → histórico (reemplazado, activo=False)
    """
    LiquidacionComprobante.objects.create(
        liquidacion_general=liquidacion_general_io,
        tipo_comprobante="FACTURA",
        serie="F002",
        numero="000456",
        fecha_emision=date(2026, 8, 10),
        monto=Decimal("1180.00"),
        activo=False,
        motivo_reemplazo="Comprobante reemplazado",
    )
    LiquidacionComprobante.objects.create(
        liquidacion_general=liquidacion_general_io,
        tipo_comprobante="FACTURA",
        serie="F001",
        numero="000123",
        fecha_emision=date(2026, 9, 20),
        monto=Decimal("1180.00"),
        activo=True,
    )
    return liquidacion_general_io


# ── Tests ──────────────────────────────────────────────────────────────────────

@pytest.mark.django_db
def test_candidatas_filtra_por_serie_del_comprobante_vigente(
    rh_inspector_mensual_flujo,
    inspector,
    perfil_ingeniero_inspector,
    liquidacion_inspector,
    liquidacion_visitas,
    liquidacion_general_io,
    liquidacion_con_comprobantes,
):
    """
    GIVEN: una candidata con un comprobante vigente (F001) y uno histórico (F002)
    WHEN: se filtra por la serie del comprobante vigente
    THEN: la candidata aparece; la serie del comprobante histórico no la devuelve.
    """
    vigente = rh_inspector_mensual_flujo.list_candidatos_inspector_proceso_paginated(
        cip=perfil_ingeniero_inspector.cip,
        page=1,
        page_size=10,
        comprobante_serie="F001",
    )
    assert vigente.total == 1
    assert len(vigente.items) == 1
    assert vigente.items[0].expediente == "EXP-CAND-FILT-001"

    historico = rh_inspector_mensual_flujo.list_candidatos_inspector_proceso_paginated(
        cip=perfil_ingeniero_inspector.cip,
        page=1,
        page_size=10,
        comprobante_serie="F002",
    )
    assert historico.total == 0
    assert historico.items == []


@pytest.mark.django_db
def test_candidatas_filtra_por_numero_del_comprobante_vigente(
    rh_inspector_mensual_flujo,
    inspector,
    perfil_ingeniero_inspector,
    liquidacion_inspector,
    liquidacion_visitas,
    liquidacion_general_io,
    liquidacion_con_comprobantes,
):
    """
    El filtro por número del comprobante también resuelve contra el ACTIVO.
    """
    vigente = rh_inspector_mensual_flujo.list_candidatos_inspector_proceso_paginated(
        cip=perfil_ingeniero_inspector.cip,
        page=1,
        page_size=10,
        comprobante_numero="000123",
    )
    assert vigente.total == 1

    historico = rh_inspector_mensual_flujo.list_candidatos_inspector_proceso_paginated(
        cip=perfil_ingeniero_inspector.cip,
        page=1,
        page_size=10,
        comprobante_numero="000456",
    )
    assert historico.total == 0


@pytest.mark.django_db
def test_candidatas_filtra_por_documento_de_entidad(
    rh_inspector_mensual_flujo,
    inspector,
    perfil_ingeniero_inspector,
    liquidacion_inspector,
    liquidacion_visitas,
    liquidacion_general_io,
):
    """
    El filtro por N.º de documento de la entidad (snapshot del proyecto) aplica
    con icontains.
    """
    match = rh_inspector_mensual_flujo.list_candidatos_inspector_proceso_paginated(
        cip=perfil_ingeniero_inspector.cip,
        page=1,
        page_size=10,
        documento="20456789012",
    )
    assert match.total == 1

    sin_match = rh_inspector_mensual_flujo.list_candidatos_inspector_proceso_paginated(
        cip=perfil_ingeniero_inspector.cip,
        page=1,
        page_size=10,
        documento="00000000",
    )
    assert sin_match.total == 0


@pytest.mark.django_db
def test_candidatas_no_se_duplican_con_historial_de_comprobantes(
    rh_inspector_mensual_flujo,
    inspector,
    perfil_ingeniero_inspector,
    liquidacion_inspector,
    liquidacion_visitas,
    liquidacion_general_io,
    liquidacion_con_comprobantes,
):
    """
    GIVEN: una candidata con 2 comprobantes (1 vigente + 1 reemplazado)
    WHEN: se listan las candidatas con el filtro de comprobante vigente
    THEN: la candidata aparece UNA sola vez y `total` no se infla.
    """
    result = rh_inspector_mensual_flujo.list_candidatos_inspector_proceso_paginated(
        cip=perfil_ingeniero_inspector.cip,
        page=1,
        page_size=50,
        comprobante_serie="F001",
    )

    assert result.total == 1
    assert len(result.items) == 1
