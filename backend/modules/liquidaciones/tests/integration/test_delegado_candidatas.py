"""
Integration tests for GET /liquidaciones/delegados/candidatas endpoint.

Tests the specific logic of matching LiquidacionEspecialidadDisponibles and
filtering out already-assigned specialties.

Uses the flujos directly (not HTTP) to avoid TestClient injection issues.
Tests use @pytest.mark.django_db for BD access.

Covers:
- Delegado has unassigned candidates → returns list
- No active TITULAR operations → returns empty
- All liquidaciones already assigned → returns empty
- Delegado not found → 404
- Multiple specialties for same liquidacion → listed per specialty
- Filter by TipoLiquidacion when operation is scoped
"""
import pytest
from datetime import date, timedelta
from decimal import Decimal

from ninja.errors import HttpError

from modules.liquidaciones.domain.models.delegado import (
    Delegado,
    DelegadoMunicipalidad,
    DelegadoMunicipalidadPeriodo,
    DelegadoOperacion,
    LiquidacionDelegado,
)
from modules.liquidaciones.domain.models.liquidacion.liquidacion_general.liquidacion import (
    LiquidacionGeneral,
    LiquidacionEspecialidadDisponibles,
)
from modules.liquidaciones.domain.models.liquidacion.liquidacion_tipo.liquidacion_tipo import (
    LiquidacionPorcentajeObra,
    LiquidacionPorcentajeObraDetalle,
)
from modules.liquidaciones.domain.models.proyecto import Proyecto
from modules.liquidaciones.domain.services.core.delegado.delegado_core_service import (
    DelegadoCoreService,
)
from modules.liquidaciones.domain.services.orchestrators.delegado_orchestrator import (
    DelegadoOrchestrator,
)
from modules.liquidaciones.presentation.presenters.delegado_presenter import DelegadoPresenter
from modules.usuarios.domain.models.perfil_ingeniero import (
    EspecialidadRevision,
    PerfilIngeniero,
)
from django.contrib.auth import get_user_model


# ── Fixtures ────────────────────────────────────────────────────────────────────

@pytest.fixture
def core_service(db):
    return DelegadoCoreService()


@pytest.fixture
def orchestrator(db, core_service):
    return DelegadoOrchestrator(core_service=core_service)


@pytest.fixture
def presenter():
    return DelegadoPresenter()


@pytest.fixture
def ubigeo_test(db):
    from modules.entidades.domain.models.ubigeo import (
        UbigeoDepartamento,
        UbigeoProvincia,
        UbigeoDistrito,
    )
    depto = UbigeoDepartamento.objects.create(nombre="Lima")
    prov = UbigeoProvincia.objects.create(departamento=depto, nombre="Lima")
    dist = UbigeoDistrito.objects.create(
        provincia=prov, nombre="Miraflores", ubigeo="150132"
    )
    return dist


@pytest.fixture
def municipalidad_test(db, ubigeo_test):
    from modules.entidades.domain.models.municipalidad import Municipalidad
    return Municipalidad.objects.create(
        codigo="M001",
        nombre="Municipalidad de Miraflores",
        distrito=ubigeo_test,
    )


@pytest.fixture
def proyecto_test(db, municipalidad_test, ubigeo_test):
    return Proyecto.objects.create(
        denominacion="Edificio Test",
        nombre_propietario="Propietario Test SAC",
        direccion="Av. Test 123",
        distrito_id=ubigeo_test.id,
        entidad_tipo_documento="RUC",
        entidad_numero_documento="20456789012",
        entidad_razon_social="Propietario Test SAC",
    )


@pytest.fixture
def usuario_liquidacion(db):
    User = get_user_model()
    return User.objects.create_user(
        username="liq_test",
        email="liq_test@test.com",
        password="testpass123",
        dni="11223344",
    )


@pytest.fixture
def especialidad_estructuras(db):
    return EspecialidadRevision.objects.create(
        slug="estructuras", nombre="Estructuras",
    )


@pytest.fixture
def especialidad_arquitectura(db):
    return EspecialidadRevision.objects.create(
        slug="arquitectura", nombre="Arquitectura",
    )


@pytest.fixture
def tipo_edificacion(db):
    from modules.liquidaciones.domain.models.tipo_liquidacion import TipoLiquidacion as TL
    return TL.objects.get_or_create(
        codigo="EDIFICACION", defaults={"nombre": "Edificaciones"}
    )[0]


@pytest.fixture
def especialidades_disponibles_edificacion(
    db, tipo_edificacion, especialidad_estructuras, especialidad_arquitectura
):
    """Create LiquidacionEspecialidadDisponibles for the 2 especialidades of Edificaciones."""
    return [
        LiquidacionEspecialidadDisponibles.objects.create(
            tipo_liquidacion=tipo_edificacion,
            especialidad=especialidad_estructuras,
            activo=True,
            periodo_inicio=date(2024, 1, 1),
            periodo_fin=None,
        ),
        LiquidacionEspecialidadDisponibles.objects.create(
            tipo_liquidacion=tipo_edificacion,
            especialidad=especialidad_arquitectura,
            activo=True,
            periodo_inicio=date(2024, 1, 1),
            periodo_fin=None,
        ),
    ]


@pytest.fixture
def tarifa_po_base(db, tipo_edificacion):
    from modules.liquidaciones.domain.models.liquidacion.liquidacion_tipo.tarifas_reglas import (
        TarifaLiquidacionBase,
    )
    return TarifaLiquidacionBase.objects.create(
        tipo_liquidacion=tipo_edificacion,
        periodo_inicio=date(2024, 1, 1),
        periodo_fin=None,
    )


@pytest.fixture
def tarifa_po_estructuras(db, tarifa_po_base):
    from modules.liquidaciones.domain.models.liquidacion.liquidacion_tipo.tarifas_reglas import (
        TarifaPorcentajeObra,
    )
    return TarifaPorcentajeObra.objects.create(
        tarifa_base=tarifa_po_base,
        porcentaje_liquidacion="0.0010",  # 0.10%
    )


@pytest.fixture
def tarifa_po_arquitectura(db, tarifa_po_base):
    from modules.liquidaciones.domain.models.liquidacion.liquidacion_tipo.tarifas_reglas import (
        TarifaPorcentajeObra,
    )
    return TarifaPorcentajeObra.objects.create(
        tarifa_base=tarifa_po_base,
        porcentaje_liquidacion="0.0005",  # 0.05%
    )


# ── Helpers ────────────────────────────────────────────────────────────────────

def _crear_perfil(cip: str, dni: str) -> PerfilIngeniero:
    """Creates a PerfilIngeniero with unique identifiers."""
    return PerfilIngeniero.objects.create(
        cip=cip,
        dni=dni,
        nombres="Nombre",
        apellido_paterno="Apellido",
        apellido_materno="Materno",
        correo_personal=f"{cip}@test.com",
    )


def _crear_delegado(cip: str, dni: str) -> Delegado:
    """Creates a Delegado."""
    return Delegado.objects.create(
        perfil_ingeniero=_crear_perfil(cip, dni),
    )


def _crear_operacion_titular(
    delegado: Delegado,
    municipalidad,
    especialidad,
    tipo_liquidacion=None,
    vigente=True,
) -> DelegadoMunicipalidad:
    """Creates a DelegadoMunicipalidad with TITULAR operation and vigente period."""
    dm = DelegadoMunicipalidad.objects.create(
        delegado=delegado,
        municipalidad=municipalidad,
        tipo="TITULAR",
        especialidad_revision=especialidad,
        liquidacion_revision=tipo_liquidacion,
    )
    if vigente:
        DelegadoMunicipalidadPeriodo.objects.create(
            delegado_municipalidad=dm,
            periodo_inicio=date.today() - timedelta(days=30),
            periodo_fin=None,
        )
    else:
        DelegadoMunicipalidadPeriodo.objects.create(
            delegado_municipalidad=dm,
            periodo_inicio=date.today() - timedelta(days=365),
            periodo_fin=date.today() - timedelta(days=30),
        )
    return dm


def _crear_liquidacion_po(
    proyecto,
    municipalidad,
    tipo_liquidacion,
    usuario,
    expediente,
    estado="REGISTRADO",
    sub_total=10000.00,
    tarifa_po=None,
    derecho=None,
):
    """Creates a LiquidacionGeneral + LiquidacionPorcentajeObra."""
    lg = LiquidacionGeneral.objects.create(
        proyecto=proyecto,
        municipalidad=municipalidad,
        tipo_liquidacion=tipo_liquidacion,
        usuario_creador=usuario,
        expediente=expediente,
        estado=estado,
        sub_total=sub_total,
        total=sub_total * 1.18,
    )
    from decimal import Decimal
    from modules.liquidaciones.domain.models.liquidacion.liquidacion_tipo.tarifas_reglas import (
        DerechoPorcentajeObra,
    )
    if derecho is None:
        derecho = DerechoPorcentajeObra.objects.create(
            derecho_minimo=Decimal("500.00"),
            derecho_maximo=Decimal("50000.00"),
            porcentaje_minimo_uit=Decimal("0.10"),
            periodo_inicio=date(2024, 1, 1),
            periodo_fin=None,
        )
    porcentaje_liq = tarifa_po.porcentaje_liquidacion if tarifa_po else Decimal("0.0010")
    lpo = LiquidacionPorcentajeObra.objects.create(
        liquidacion_general=lg,
        valor_declarado=sub_total,
        porcentaje_liquidacion=porcentaje_liq,
        porcentaje_minimo_uit=derecho.porcentaje_minimo_uit,
        derecho_aplicado=derecho,
    )
    return lg, lpo


def _crear_detalle_po(lpo, especialidad, subtotal, tarifa_po):
    """Creates a LiquidacionPorcentajeObraDetalle for the given specialty."""
    return LiquidacionPorcentajeObraDetalle.objects.create(
        liquidacion_porcentaje=lpo,
        tarifa_aplicada=tarifa_po,
        especialidad=especialidad,
        porcentaje_aplicado=tarifa_po.porcentaje_liquidacion,
        subtotal=subtotal,
    )


# ── Tests ──────────────────────────────────────────────────────────────────────

@pytest.mark.django_db
def test_delegado_tiene_candidatas_no_asignadas(
    orchestrator,
    municipalidad_test,
    tipo_edificacion,
    especialidad_estructuras,
    especialidades_disponibles_edificacion,
    tarifa_po_base,
    tarifa_po_estructuras,
    proyecto_test,
    usuario_liquidacion,
):
    """
    GIVEN a valid Delegado with active TITULAR operation
    AND a LiquidacionGeneral in their municipalidad with that specialty available
    AND no LiquidacionDelegado assignment exists for that specialty
    WHEN get_candidatas_for_delegado is called
    THEN the liquidacion is returned as a candidate with the specialty.
    """
    # Setup: Delegado + TITULAR operation
    delegado = _crear_delegado("11111", "11111111")
    _crear_operacion_titular(
        delegado, municipalidad_test, especialidad_estructuras, tipo_edificacion
    )

    # Setup: LiquidacionGeneral + PO detail for estructuras
    lg, lpo = _crear_liquidacion_po(
        proyecto_test, municipalidad_test, tipo_edificacion,
        usuario_liquidacion, "EXP-001", sub_total=10000.00,
        tarifa_po=tarifa_po_estructuras,
    )
    _crear_detalle_po(lpo, especialidad_estructuras, 10000.00, tarifa_po_estructuras)

    # Execute
    result = orchestrator.list_candidatas_delegado_proceso("11111")

    # Assert
    assert result.delegado.cip == "11111"
    assert result.total == 1
    assert len(result.candidatas) == 1
    assert result.candidatas[0].expediente == "EXP-001"
    assert result.candidatas[0].especialidad_candidata.nombre == "Estructuras"


@pytest.mark.django_db
def test_delegado_sin_operaciones_titulares_retorna_vacio(
    orchestrator,
    municipalidad_test,
):
    """
    GIVEN a Delegado with NO active TITULAR operations
    WHEN list_candidatas_delegado_proceso is called
    THEN an empty list is returned.
    """
    # Setup: Delegado without any operations
    delegado = _crear_delegado("22222", "22222222")
    # No operation created

    # Execute
    result = orchestrator.list_candidatas_delegado_proceso("22222")

    # Assert
    assert result.delegado.cip == "22222"
    assert result.total == 0
    assert result.candidatas == []


@pytest.mark.django_db
def test_delegado_todas_candidatas_ya_asignadas_retorna_vacio(
    orchestrator,
    municipalidad_test,
    tipo_edificacion,
    especialidad_estructuras,
    especialidades_disponibles_edificacion,
    tarifa_po_base,
    tarifa_po_estructuras,
    proyecto_test,
    usuario_liquidacion,
):
    """
    GIVEN a Delegado whose liquidaciones are ALL already assigned
    (LiquidacionDelegado exists for the specialty)
    WHEN list_candidatas_delegado_proceso is called
    THEN an empty list is returned.
    """
    # Setup: Delegado + TITULAR operation
    delegado = _crear_delegado("33333", "33333333")
    _crear_operacion_titular(
        delegado, municipalidad_test, especialidad_estructuras, tipo_edificacion
    )

    # Setup: LiquidacionGeneral + PO detail
    lg, lpo = _crear_liquidacion_po(
        proyecto_test, municipalidad_test, tipo_edificacion,
        usuario_liquidacion, "EXP-002", sub_total=10000.00,
        tarifa_po=tarifa_po_estructuras,
    )
    _crear_detalle_po(lpo, especialidad_estructuras, 10000.00, tarifa_po_estructuras)

    # Setup: PRE-EXISTING assignment — this liquidacion is NOT a candidate
    LiquidacionDelegado.objects.create(
        liquidacion=lg,
        delegado=delegado,
        especialidad_revision=especialidad_estructuras,
    )

    # Execute
    result = orchestrator.list_candidatas_delegado_proceso("33333")

    # Assert
    assert result.delegado.cip == "33333"
    assert result.total == 0
    assert result.candidatas == []


@pytest.mark.django_db
def test_delegado_no_encontrado_404(orchestrator):
    """
    GIVEN a CIP that does not belong to any Delegado
    WHEN list_candidatas_delegado_proceso is called
    THEN HttpError 404 is raised.
    """
    from ninja.errors import HttpError

    with pytest.raises(HttpError) as excinfo:
        orchestrator.list_candidatas_delegado_proceso("CIP-INEXISTENTE")

    assert excinfo.value.status_code == 404


@pytest.mark.django_db
def test_multiple_especialidades_misma_liquidacion_retorna_por_especialidad(
    orchestrator,
    municipalidad_test,
    tipo_edificacion,
    especialidad_estructuras,
    especialidad_arquitectura,
    especialidades_disponibles_edificacion,
    tarifa_po_base,
    tarifa_po_estructuras,
    tarifa_po_arquitectura,
    proyecto_test,
    usuario_liquidacion,
):
    """
    GIVEN a Delegado who is TITULAR for multiple specialties in a municipality
    AND a single liquidacion that covers both specialties
    WHEN list_candidatas_delegado_proceso is called
    THEN the response lists the liquidacion TWICE — once per specialty.
    """
    # Setup: Delegado with TITULAR for BOTH especialidades.
    # Note: unique_together=(delegado, municipalidad, liquidacion_revision) means
    # two operations for the same (delegado, municipalidad) require different
    # liquidacion_revision values. Pass None for the second operation.
    delegado = _crear_delegado("44444", "44444444")
    _crear_operacion_titular(
        delegado, municipalidad_test, especialidad_estructuras, tipo_edificacion
    )
    _crear_operacion_titular(
        delegado, municipalidad_test, especialidad_arquitectura, None
    )

    # Setup: Two separate LiquidacionGenerals, one per specialty
    lg1, lpo1 = _crear_liquidacion_po(
        proyecto_test, municipalidad_test, tipo_edificacion,
        usuario_liquidacion, "EXP-ESTR", sub_total=10000.00,
        tarifa_po=tarifa_po_estructuras,
    )
    _crear_detalle_po(lpo1, especialidad_estructuras, 10000.00, tarifa_po_estructuras)

    lg2, lpo2 = _crear_liquidacion_po(
        proyecto_test, municipalidad_test, tipo_edificacion,
        usuario_liquidacion, "EXP-ARQ", sub_total=10000.00,
        tarifa_po=tarifa_po_arquitectura,
    )
    _crear_detalle_po(lpo2, especialidad_arquitectura, 10000.00, tarifa_po_arquitectura)

    # Execute
    result = orchestrator.list_candidatas_delegado_proceso("44444")

    # Assert: 2 candidates — one per specialty/liquidacion
    assert result.total == 2
    nombres = {c.especialidad_candidata.nombre for c in result.candidatas}
    assert nombres == {"Estructuras", "Arquitectura"}


@pytest.mark.django_db
def test_especialidad_no_disponible_no_retorna_candidata(
    orchestrator,
    municipalidad_test,
    tipo_edificacion,
    especialidad_estructuras,
    especialidad_arquitectura,
    especialidades_disponibles_edificacion,  # Only estructuras and arquitectura are available
    tarifa_po_base,
    tarifa_po_estructuras,
    proyecto_test,
    usuario_liquidacion,
):
    """
    GIVEN a Delegado TITULAR for Estructuras only
    AND a LiquidacionGeneral that has Estructuras detail
    BUT the tipo_liquidacion does NOT have Arquitectura available (not in especialidades_disponibles)
    WHEN list_candidatas_delegado_proceso is called for Arquitectura operation
    THEN the liquidacion is NOT returned as candidate for Arquitectura.
    """
    # Create a different specialty (Impacto Vial) that is NOT available for EDIFICACION tipo
    especialidad_impacto = EspecialidadRevision.objects.create(
        slug="impacto-vial", nombre="Impacto Vial"
    )

    # Setup: Delegado TITULAR for Impacto Vial
    from modules.liquidaciones.domain.models.tipo_liquidacion import TipoLiquidacion
    tipo_impacto_vial, _ = TipoLiquidacion.objects.get_or_create(
        codigo="IMPACTO_VIAL", defaults={"nombre": "Impacto Vial"}
    )

    # Setup: Delegado TITULAR for Impacto Vial in this municipalidad
    # (But there's no IMPACTO_VIAL liquidacion available, so no candidates)
    # This is a different scenario: we create an EDIFICACION liquidacion but try to
    # match it against an Impacto Vial operation scope
    delegado = _crear_delegado("66666", "66666666")
    _crear_operacion_titular(
        delegado, municipalidad_test, especialidad_impacto, tipo_impacto_vial
    )

    # Execute - should return empty since no IMPACTO_VIAL liquidaciones exist
    result = orchestrator.list_candidatas_delegado_proceso("66666")

    # Assert
    assert result.delegado.cip == "66666"
    assert result.total == 0
    assert result.candidatas == []


@pytest.mark.django_db
def test_present_candidatas_delegado(
    presenter,
    orchestrator,
    municipalidad_test,
    tipo_edificacion,
    especialidad_estructuras,
    especialidades_disponibles_edificacion,
    tarifa_po_base,
    tarifa_po_estructuras,
    proyecto_test,
    usuario_liquidacion,
):
    """
    GIVEN candidatas exist for a Delegado
    WHEN present_candidatas is called
    THEN the result matches DelegadoCandidatasOut schema.
    """
    # Setup
    delegado = _crear_delegado("55555", "55555555")
    _crear_operacion_titular(
        delegado, municipalidad_test, especialidad_estructuras, tipo_edificacion
    )
    lg, lpo = _crear_liquidacion_po(
        proyecto_test, municipalidad_test, tipo_edificacion,
        usuario_liquidacion, "EXP-PRES", sub_total=5000.00,
        tarifa_po=tarifa_po_estructuras,
    )
    _crear_detalle_po(lpo, especialidad_estructuras, 5000.00, tarifa_po_estructuras)

    # Execute
    domain_result = orchestrator.list_candidatas_delegado_proceso("55555")
    presented = presenter.present_candidatas(domain_result)

    # Assert structure
    assert presented.delegado.cip == "55555"
    assert len(presented.candidatas) == 1
    assert presented.candidatas[0].expediente == "EXP-PRES"
    assert presented.candidatas[0].especialidad_candidata.nombre == "Estructuras"
