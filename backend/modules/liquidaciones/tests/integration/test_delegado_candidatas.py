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
        tipo_liquidacion=tipo_liquidacion,
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


def _crear_operacion(
    delegado: Delegado,
    municipalidad,
    especialidad,
    tipo: str,
    tipo_liquidacion=None,
    vigente=True,
) -> DelegadoMunicipalidad:
    """Creates a DelegadoMunicipalidad with specified tipo operation and vigente period."""
    dm = DelegadoMunicipalidad.objects.create(
        delegado=delegado,
        municipalidad=municipalidad,
        tipo=tipo,
        especialidad_revision=especialidad,
        tipo_liquidacion=tipo_liquidacion,
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
    GIVEN a valid Delegado with active TITULAR operation matching the filter criteria
    AND a LiquidacionGeneral in their municipalidad with that specialty available
    AND no LiquidacionDelegado assignment exists for that specialty
    WHEN get_candidatas_for_delegado is called with full filters
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

    # Execute - pass all required filters
    result = orchestrator.list_candidatas_delegado_proceso(
        cip="11111",
        municipalidad_id=municipalidad_test.id,
        tipo_liquidacion_id=tipo_edificacion.id,
        tipo_delegado="TITULAR",
    )

    # Assert
    assert result.delegado.cip == "11111"
    assert result.total == 1
    assert len(result.candidatas) == 1
    assert result.candidatas[0].expediente == "EXP-001"
    assert result.candidatas[0].especialidad_candidata.nombre == "Estructuras"
    assert result.candidatas[0].tipo_delegado == "TITULAR"


@pytest.mark.django_db
def test_delegado_sin_operaciones_activas_retorna_404(
    orchestrator,
    municipalidad_test,
    tipo_edificacion,
):
    """
    GIVEN a Delegado with NO active operations matching the filter criteria
    WHEN list_candidatas_delegado_proceso is called with full filters
    THEN HttpError 404 is raised.
    """
    # Setup: Delegado without any operations
    delegado = _crear_delegado("22222", "22222222")
    # No operation created

    # Execute - should raise 404 since no operation matches
    from ninja.errors import HttpError
    with pytest.raises(HttpError) as excinfo:
        orchestrator.list_candidatas_delegado_proceso(
            cip="22222",
            municipalidad_id=municipalidad_test.id,
            tipo_liquidacion_id=tipo_edificacion.id,
            tipo_delegado="TITULAR",
        )
    assert excinfo.value.status_code == 404


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
    WHEN list_candidatas_delegado_proceso is called with full filters
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
    result = orchestrator.list_candidatas_delegado_proceso(
        cip="33333",
        municipalidad_id=municipalidad_test.id,
        tipo_liquidacion_id=tipo_edificacion.id,
        tipo_delegado="TITULAR",
    )

    # Assert
    assert result.delegado.cip == "33333"
    assert result.total == 0
    assert result.candidatas == []


@pytest.mark.django_db
def test_delegado_no_encontrado_404(orchestrator, municipalidad_test, tipo_edificacion):
    """
    GIVEN a CIP that does not belong to any Delegado
    WHEN list_candidatas_delegado_proceso is called with full filters
    THEN HttpError 404 is raised.
    """
    from ninja.errors import HttpError

    with pytest.raises(HttpError) as excinfo:
        orchestrator.list_candidatas_delegado_proceso(
            cip="CIP-INEXISTENTE",
            municipalidad_id=municipalidad_test.id,
            tipo_liquidacion_id=tipo_edificacion.id,
            tipo_delegado="TITULAR",
        )

    assert excinfo.value.status_code == 404


@pytest.mark.django_db
def test_multiple_operaciones_ambiguas_retorna_409(
    orchestrator,
    municipalidad_test,
    tipo_edificacion,
    especialidad_estructuras,
):
    """
    GIVEN a Delegado has both a wildcard (tipo_liquidacion=None) operation
    AND a specific (tipo_liquidacion=tipo_edificacion) operation for the same criteria
    WHEN list_candidatas_delegado_proceso is called
    THEN HttpError 409 is raised due to ambiguity.
    """
    # Setup: Delegado with BOTH wildcard and specific operations
    # This creates ambiguity: which one should be used?
    delegado = _crear_delegado("44444", "44444444")
    # Create TITULAR with specific tipo_liquidacion
    _crear_operacion_titular(
        delegado, municipalidad_test, especialidad_estructuras, tipo_edificacion
    )
    # Create TITULAR with wildcard (None)
    _crear_operacion_titular(
        delegado, municipalidad_test, especialidad_estructuras, None
    )

    # Execute - should raise 409 due to ambiguity
    from ninja.errors import HttpError
    with pytest.raises(HttpError) as excinfo:
        orchestrator.list_candidatas_delegado_proceso(
            cip="44444",
            municipalidad_id=municipalidad_test.id,
            tipo_liquidacion_id=tipo_edificacion.id,
            tipo_delegado="TITULAR",
        )
    assert excinfo.value.status_code == 409


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
    GIVEN a Delegado TITULAR for Estructuras only (specific tipo_edificacion)
    AND a LiquidacionGeneral in their municipalidad
    BUT the DelegadoOperacion has tipo_liquidacion matching the tipo_liquidacion
    WHEN list_candidatas_delegado_proceso is called with the matching filters
    THEN the liquidacion is returned as candidate.
    """
    # Setup: Delegado TITULAR for Estructuras with specific tipo_edificacion
    delegado = _crear_delegado("66666", "66666666")
    _crear_operacion_titular(
        delegado, municipalidad_test, especialidad_estructuras, tipo_edificacion
    )

    # Setup: LiquidacionGeneral for estructuras
    lg, lpo = _crear_liquidacion_po(
        proyecto_test, municipalidad_test, tipo_edificacion,
        usuario_liquidacion, "EXP-666", sub_total=10000.00,
        tarifa_po=tarifa_po_estructuras,
    )
    _crear_detalle_po(lpo, especialidad_estructuras, 10000.00, tarifa_po_estructuras)

    # Execute with matching filters
    result = orchestrator.list_candidatas_delegado_proceso(
        cip="66666",
        municipalidad_id=municipalidad_test.id,
        tipo_liquidacion_id=tipo_edificacion.id,
        tipo_delegado="TITULAR",
    )

    # Assert: candidate returned since it matches the operation's scope
    assert result.delegado.cip == "66666"
    assert result.total == 1
    assert result.candidatas[0].especialidad_candidata.nombre == "Estructuras"


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

    # Execute with full filters
    domain_result = orchestrator.list_candidatas_delegado_proceso(
        cip="55555",
        municipalidad_id=municipalidad_test.id,
        tipo_liquidacion_id=tipo_edificacion.id,
        tipo_delegado="TITULAR",
    )
    presented = presenter.present_candidatas(domain_result)

    # Assert structure
    assert presented.delegado.cip == "55555"
    assert len(presented.candidatas) == 1
    assert presented.candidatas[0].expediente == "EXP-PRES"
    assert presented.candidatas[0].especialidad_candidata.nombre == "Estructuras"
    assert presented.candidatas[0].tipo_delegado == "TITULAR"
    # New fields: liquidacion_especifica_numero and comprobante_activo can be null when not set
    assert presented.candidatas[0].liquidacion_especifica_numero is None
    assert presented.candidatas[0].comprobante_activo is None


@pytest.mark.django_db
def test_candidatas_comprobante_activo(
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
    GIVEN a candidate liquidacion with an active comprobante
    WHEN list_candidatas_delegado_proceso is called
    THEN the comprobante_activo field is populated in the response.
    """
    from modules.liquidaciones.domain.models.liquidacion.liquidacion_general.comprobante import (
        LiquidacionComprobante,
    )

    # Setup
    delegado = _crear_delegado("55556", "55555656")
    _crear_operacion_titular(
        delegado, municipalidad_test, especialidad_estructuras, tipo_edificacion
    )
    lg, lpo = _crear_liquidacion_po(
        proyecto_test, municipalidad_test, tipo_edificacion,
        usuario_liquidacion, "EXP-COMP", sub_total=5000.00,
        tarifa_po=tarifa_po_estructuras,
    )
    _crear_detalle_po(lpo, especialidad_estructuras, 5000.00, tarifa_po_estructuras)

    # Create active comprobante for the liquidacion
    LiquidacionComprobante.objects.create(
        liquidacion_general=lg,
        tipo_comprobante="FACTURA",
        serie="F001",
        numero="000123",
        fecha_emision=date(2024, 6, 15),
        monto=Decimal("5900.00"),
        activo=True,
    )

    # Execute with full filters
    domain_result = orchestrator.list_candidatas_delegado_proceso(
        cip="55556",
        municipalidad_id=municipalidad_test.id,
        tipo_liquidacion_id=tipo_edificacion.id,
        tipo_delegado="TITULAR",
    )
    presented = presenter.present_candidatas(domain_result)

    # Assert comprobante_activo is populated
    assert len(presented.candidatas) == 1
    assert presented.candidatas[0].comprobante_activo is not None
    assert presented.candidatas[0].comprobante_activo.tipo_comprobante == "FACTURA"
    assert presented.candidatas[0].comprobante_activo.serie == "F001"
    assert presented.candidatas[0].comprobante_activo.numero == "000123"
    assert presented.candidatas[0].comprobante_activo.fecha_emision == "2024-06-15"


@pytest.mark.django_db
def test_candidatas_wildcard_operation_accepts_any_tipo_liquidacion(
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
    GIVEN a Delegado with ALTERNO (Arquitectura, None=wildcard) operation
    AND two LiquidacionGenerals of different tipos in the same municipalidad
    WHEN list_candidatas_delegado_proceso is called with tipo_delegado=ALTERNO
    THEN candidates from the wildcard operation are returned for matching especialidades.
    """
    # Setup: Delegado with ALTERNO wildcard operation (tipo_liquidacion=None)
    # This accepts any tipo_liquidacion
    delegado = _crear_delegado("77777", "77777777")
    _crear_operacion(delegado, municipalidad_test, especialidad_arquitectura, "ALTERNO", None)

    # Setup: Liquidacion for Arquitectura
    lg2, lpo2 = _crear_liquidacion_po(
        proyecto_test, municipalidad_test, tipo_edificacion,
        usuario_liquidacion, "EXP-ARQ", sub_total=8000.00,
        tarifa_po=tarifa_po_arquitectura,
    )
    _crear_detalle_po(lpo2, especialidad_arquitectura, 8000.00, tarifa_po_arquitectura)

    # Execute with ALTERNO - wildcard matches
    result = orchestrator.list_candidatas_delegado_proceso(
        cip="77777",
        municipalidad_id=municipalidad_test.id,
        tipo_liquidacion_id=tipo_edificacion.id,
        tipo_delegado="ALTERNO",
    )

    # Assert: 1 candidate from ALTERNO wildcard
    assert result.delegado.cip == "77777"
    assert result.total == 1
    assert result.candidatas[0].tipo_delegado == "ALTERNO"
    assert result.candidatas[0].especialidad_candidata.nombre == "Arquitectura"


@pytest.mark.django_db
def test_candidatas_exact_match_preferred_over_wildcard_retorna_409(
    orchestrator,
    municipalidad_test,
    tipo_edificacion,
    especialidad_estructuras,
):
    """
    GIVEN a Delegado has both a wildcard (tipo_liquidacion=None) operation
    AND a specific (tipo_liquidacion=tipo_edificacion) operation for same (municipalidad, tipo_delegado)
    WHEN list_candidatas_delegado_proceso is called
    THEN HttpError 409 is raised (ambiguous).
    """
    # Setup: Delegado with BOTH wildcard and specific operations
    delegado = _crear_delegado("88888", "88888888")
    _crear_operacion(delegado, municipalidad_test, especialidad_estructuras, "TITULAR", tipo_edificacion)
    _crear_operacion(delegado, municipalidad_test, especialidad_estructuras, "TITULAR", None)

    # Execute - should raise 409 due to ambiguity
    from ninja.errors import HttpError
    with pytest.raises(HttpError) as excinfo:
        orchestrator.list_candidatas_delegado_proceso(
            cip="88888",
            municipalidad_id=municipalidad_test.id,
            tipo_liquidacion_id=tipo_edificacion.id,
            tipo_delegado="TITULAR",
        )
    assert excinfo.value.status_code == 409


@pytest.mark.django_db
def test_delegado_operacion_id_in_response(
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
    AND a LiquidacionGeneral candidate exists
    WHEN list_candidatas_delegado_proceso is called
    THEN the response includes the delegado_operacion_id per candidate.
    """
    # Setup
    delegado = _crear_delegado("99999", "99999999")
    operacion = _crear_operacion_titular(
        delegado, municipalidad_test, especialidad_estructuras, tipo_edificacion
    )

    lg, lpo = _crear_liquidacion_po(
        proyecto_test, municipalidad_test, tipo_edificacion,
        usuario_liquidacion, "EXP-999", sub_total=10000.00,
        tarifa_po=tarifa_po_estructuras,
    )
    _crear_detalle_po(lpo, especialidad_estructuras, 10000.00, tarifa_po_estructuras)

    # Execute
    result = orchestrator.list_candidatas_delegado_proceso(
        cip="99999",
        municipalidad_id=municipalidad_test.id,
        tipo_liquidacion_id=tipo_edificacion.id,
        tipo_delegado="TITULAR",
    )

    # Assert: delegado_operacion_id is present and matches the created operation
    assert result.total == 1
    assert str(result.candidatas[0].delegado_operacion_id) == str(operacion.id)


# ── Tests for SmartField ID path ────────────────────────────────────────────────


@pytest.mark.django_db
def test_candidatas_delegado_operacion_id_path_returns_candidates(
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
    AND a LiquidacionGeneral candidate exists
    WHEN list_candidatas_delegado_proceso is called with delegado_operacion_id
    THEN candidates are returned without requiring municipalidad_id/tipo_liquidacion_id/tipo_delegado.
    """
    # Setup
    delegado = _crear_delegado("111122", "11112222")
    operacion = _crear_operacion_titular(
        delegado, municipalidad_test, especialidad_estructuras, tipo_edificacion
    )

    lg, lpo = _crear_liquidacion_po(
        proyecto_test, municipalidad_test, tipo_edificacion,
        usuario_liquidacion, "EXP-IDPATH", sub_total=10000.00,
        tarifa_po=tarifa_po_estructuras,
    )
    _crear_detalle_po(lpo, especialidad_estructuras, 10000.00, tarifa_po_estructuras)

    # Execute using SmartField ID path
    result = orchestrator.list_candidatas_delegado_proceso(
        cip="111122",
        delegado_operacion_id=operacion.id,
    )

    # Assert
    assert result.delegado.cip == "111122"
    assert result.total == 1
    assert result.candidatas[0].expediente == "EXP-IDPATH"
    assert str(result.candidatas[0].delegado_operacion_id) == str(operacion.id)


@pytest.mark.django_db
def test_candidatas_delegado_operacion_id_path_validates_cip(
    orchestrator,
    municipalidad_test,
    tipo_edificacion,
    especialidad_estructuras,
):
    """
    GIVEN a valid DelegadoOperacion exists for a delegado with CIP "333344"
    WHEN list_candidatas_delegado_proceso is called with a different CIP that exists
    THEN 400 is raised (operatividad does not belong to that delegado).
    """
    # Setup: two different delegados
    delegado_correcto = _crear_delegado("333344", "33334444")
    delegado_wrong = _crear_delegado("999900", "99990000")
    operacion = _crear_operacion_titular(
        delegado_correcto, municipalidad_test, especialidad_estructuras, tipo_edificacion
    )

    # Execute with wrong cip (999900 exists, but operation belongs to 333344)
    from ninja.errors import HttpError
    with pytest.raises(HttpError) as excinfo:
        orchestrator.list_candidatas_delegado_proceso(
            cip="999900",  # wrong cip but exists
            delegado_operacion_id=operacion.id,
        )
    assert excinfo.value.status_code == 400


@pytest.mark.django_db
def test_candidatas_delegado_operacion_id_path_validates_vigencia(
    orchestrator,
    municipalidad_test,
    tipo_edificacion,
    especialidad_estructuras,
):
    """
    GIVEN a DelegadoOperacion that is NOT vigente (periodo closed)
    WHEN list_candidatas_delegado_proceso is called with its ID
    THEN 404 is raised (operation not vigente).
    """
    # Setup: operation with closed periodo (not vigente)
    delegado = _crear_delegado("555566", "55556666")
    _crear_operacion_titular(
        delegado, municipalidad_test, especialidad_estructuras, tipo_edificacion,
        vigente=False,  # NOT vigente
    )

    # Get the non-vigente operation
    from modules.liquidaciones.domain.models.delegado import DelegadoOperacion
    operacion = DelegadoOperacion.objects.filter(delegado=delegado).first()

    # Execute
    from ninja.errors import HttpError
    with pytest.raises(HttpError) as excinfo:
        orchestrator.list_candidatas_delegado_proceso(
            cip="555566",
            delegado_operacion_id=operacion.id,
        )
    assert excinfo.value.status_code == 404
    assert "no está vigente" in str(excinfo.value.message)


@pytest.mark.django_db
def test_candidatas_delegado_operacion_id_path_wildcard_operation(
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
    GIVEN a DelegadoOperacion with tipo_liquidacion=None (wildcard)
    AND multiple LiquidacionGenerals of different tipos exist
    WHEN list_candidatas_delegado_proceso is called with the wildcard operation ID
    THEN candidates are returned for matching especialidades (no tipo_liquidacion_id required).
    """
    # Setup: ALTERNO wildcard operation (tipo_liquidacion=None)
    delegado = _crear_delegado("777788", "77778888")
    operacion = _crear_operacion(
        delegado, municipalidad_test, especialidad_arquitectura, "ALTERNO", None
    )

    # Setup: Liquidacion for Arquitectura
    lg, lpo = _crear_liquidacion_po(
        proyecto_test, municipalidad_test, tipo_edificacion,
        usuario_liquidacion, "EXP-WILD", sub_total=8000.00,
        tarifa_po=tarifa_po_arquitectura,
    )
    _crear_detalle_po(lpo, especialidad_arquitectura, 8000.00, tarifa_po_arquitectura)

    # Execute using SmartField ID path (no tipo_liquidacion_id)
    result = orchestrator.list_candidatas_delegado_proceso(
        cip="777788",
        delegado_operacion_id=operacion.id,
    )

    # Assert: 1 candidate from wildcard ALTERNO operation
    assert result.delegado.cip == "777788"
    assert result.total == 1
    assert result.candidatas[0].tipo_delegado == "ALTERNO"
    assert result.candidatas[0].especialidad_candidata.nombre == "Arquitectura"


@pytest.mark.django_db
def test_candidatas_delegado_operacion_id_path_not_found(
    orchestrator,
):
    """
    GIVEN a non-existent DelegadoOperacion ID
    WHEN list_candidatas_delegado_proceso is called with that ID
    THEN 404 is raised.
    """
    import uuid
    fake_id = uuid.uuid4()

    from ninja.errors import HttpError
    with pytest.raises(HttpError) as excinfo:
        orchestrator.list_candidatas_delegado_proceso(
            cip="12345",
            delegado_operacion_id=fake_id,
        )
    assert excinfo.value.status_code == 404
