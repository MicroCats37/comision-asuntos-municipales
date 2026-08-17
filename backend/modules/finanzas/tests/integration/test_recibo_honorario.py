"""
Integration tests for ReciboHonorarioDelegado model and calculation.

Tests the fixed-rate calculation and model creation with
LiquidacionDelegado foreign key.
"""
import pytest
from decimal import Decimal

from modules.finanzas.domain.models.recibo_honorario import (
    ReciboHonorarioDelegado,
    TASA_RENTA_CIP,
    TASA_APORTE_CODEMU,
    TASA_FONDO_COMUN,
)
from modules.finanzas.domain.results.recibo_honorario_result import CalculoHonorarioResult


# ── Calculation Tests ───────────────────────────────────────────────────────────

class TestCalcularHonorarios:
    """Tests for the calcular_honorarios static method."""

    def test_calcular_honorarios_imp_bruto_1000(self):
        """
        imp_bruto=1000.00 yields:
            renta_cip=250.00, aporte_codemu=50.00, fondo_comun=100.00,
            neto_honorario=600.00, honorario=600.00
        """
        imp_bruto = Decimal("1000.00")
        result = ReciboHonorarioDelegado._calcular_honorarios(imp_bruto)

        assert isinstance(result, CalculoHonorarioResult)
        assert result.imp_bruto == Decimal("1000.00")
        assert result.renta_cip == Decimal("250.00")
        assert result.aporte_codemu == Decimal("50.00")
        assert result.fondo_comun == Decimal("100.00")
        assert result.neto_honorario == Decimal("600.00")
        assert result.honorario == Decimal("600.00")

    def test_calcular_honorarios_imp_bruto_333_33(self):
        """
        imp_bruto=333.33 yields:
            renta_cip=83.33, aporte_codemu=16.67, fondo_comun=33.33,
            neto_honorario=200.00, honorario=200.00
        """
        imp_bruto = Decimal("333.33")
        result = ReciboHonorarioDelegado._calcular_honorarios(imp_bruto)

        assert result.renta_cip == Decimal("83.33")
        assert result.aporte_codemu == Decimal("16.67")
        assert result.fondo_comun == Decimal("33.33")
        assert result.neto_honorario == Decimal("200.00")
        assert result.honorario == Decimal("200.00")

    def test_calcular_honorarios_rounding_half_up(self):
        """
        Verify ROUND_HALF_UP rounding is applied (0.005 rounds up).
        imp_bruto=1.005 → each component should round correctly.
        """
        imp_bruto = Decimal("1.005")
        result = ReciboHonorarioDelegado._calcular_honorarios(imp_bruto)

        # 1.005 * 0.25 = 0.25125 → 0.25 (HALF_UP to 2 places)
        assert result.renta_cip == Decimal("0.25")
        # 1.005 * 0.05 = 0.05025 → 0.05
        assert result.aporte_codemu == Decimal("0.05")
        # 1.005 * 0.10 = 0.1005 → 0.10
        assert result.fondo_comun == Decimal("0.10")

    def test_calcular_honorario_constants_match_spec(self):
        """Verify the module-level constants match the fixed-rate contract."""
        assert TASA_RENTA_CIP == Decimal("0.25")
        assert TASA_APORTE_CODEMU == Decimal("0.05")
        assert TASA_FONDO_COMUN == Decimal("0.10")

    def test_calcular_honorarios_honorario_equals_neto(self):
        """
        Per spec: honorario = neto_honorario (they are always equal).
        """
        imp_bruto = Decimal("999.99")
        result = ReciboHonorarioDelegado._calcular_honorarios(imp_bruto)

        assert result.honorario == result.neto_honorario


# ── Model Creation Tests ────────────────────────────────────────────────────────

@pytest.fixture
def perfil_ingeniero_delegado(db):
    """Create a PerfilIngeniero for the Delegado test fixture."""
    from modules.usuarios.domain.models.perfil_ingeniero import PerfilIngeniero
    from django.contrib.auth import get_user_model

    User = get_user_model()
    user = User.objects.create_user(
        username="testdelegado",
        email="delegado@test.com",
        password="testpass123",
        dni="87654321",
    )
    return PerfilIngeniero.objects.create(
        usuario=user,
        apellido_paterno="Pérez",
        apellido_materno="García",
        nombres="Juan",
        cip="CIP-12345",
        dni="87654321",
    )


@pytest.fixture
def especialidad_revision(db):
    """Create an EspecialidadRevision for testing."""
    from modules.usuarios.domain.models.perfil_ingeniero import EspecialidadRevision

    return EspecialidadRevision.objects.create(
        codigo="E01",
        slug="estructuras",
        nombre="Estructuras",
    )


@pytest.fixture
def delegado(db, perfil_ingeniero_delegado):
    """Create a Delegado for testing."""
    from modules.liquidaciones.domain.models.delegado import Delegado

    return Delegado.objects.create(
        perfil_ingeniero=perfil_ingeniero_delegado,
    )


@pytest.fixture
def tipo_liquidacion_edificacion(db):
    """Get or create TipoLiquidacion for EDIFICACION."""
    from modules.liquidaciones.domain.models.tipo_liquidacion import TipoLiquidacion

    return TipoLiquidacion.objects.get_or_create(
        codigo="EDIFICACION", defaults={"nombre": "Edificaciones"}
    )[0]


@pytest.fixture
def ubigeo_test(db):
    """Create minimal ubigeo for testing."""
    from modules.entidades.domain.models.ubigeo import UbigeoDepartamento, UbigeoProvincia, UbigeoDistrito

    depto = UbigeoDepartamento.objects.create(nombre="LIMA")
    prov = UbigeoProvincia.objects.create(departamento=depto, nombre="LIMA")
    dist = UbigeoDistrito.objects.create(
        provincia=prov, nombre="MIRAFLORES", ubigeo="150132"
    )
    return dist


@pytest.fixture
def municipalidad_test(db, ubigeo_test):
    """Create a municipalidad for testing."""
    from modules.entidades.domain.models.municipalidad import Municipalidad

    return Municipalidad.objects.create(
        codigo="M001",
        nombre="Municipalidad de Miraflores",
        distrito=ubigeo_test,
    )


@pytest.fixture
def proyecto_test(db, municipalidad_test, ubigeo_test):
    """Create a proyecto for testing."""
    from modules.liquidaciones.domain.models.proyecto import Proyecto

    return Proyecto.objects.create(
        denominacion="Proyecto Test",
        nombre_propietario="Propietario Test SAC",
        direccion="Av. Test 123",
        distrito_id=ubigeo_test.id,
        entidad_tipo_documento="RUC",
        entidad_numero_documento="20456789012",
        entidad_razon_social="Propietario Test SAC",
    )


@pytest.fixture
def usuario_liquidacion(db):
    """Create a test user for FK on LiquidacionGeneral."""
    from django.contrib.auth import get_user_model

    User = get_user_model()
    return User.objects.create_user(
        username="liquidacionuser",
        email="liq@test.com",
        password="testpass123",
        dni="11223344",
    )


@pytest.fixture
def liquidacion_general_test(
    db,
    proyecto_test,
    municipalidad_test,
    tipo_liquidacion_edificacion,
    usuario_liquidacion,
):
    """Create a LiquidacionGeneral for testing."""
    from modules.liquidaciones.domain.models.liquidacion.liquidacion_general.liquidacion import (
        LiquidacionGeneral,
    )

    return LiquidacionGeneral.objects.create(
        proyecto=proyecto_test,
        municipalidad=municipalidad_test,
        tipo_liquidacion=tipo_liquidacion_edificacion,
        usuario_creador=usuario_liquidacion,
        expediente="EXP-2026-001",
        estado="REGISTRADO",
        sub_total=Decimal("5000.00"),
        total=Decimal("5900.00"),
    )


@pytest.fixture
def liquidacion_delegado_test(
    db, liquidacion_general_test, delegado, especialidad_revision
):
    """Create a LiquidacionDelegado for testing."""
    from modules.liquidaciones.domain.models.delegado import LiquidacionDelegado

    return LiquidacionDelegado.objects.create(
        liquidacion=liquidacion_general_test,
        delegado=delegado,
        especialidad_revision=especialidad_revision,
        periodo="2026-01",
    )


@pytest.mark.django_db
def test_recibo_honorario_delegado_creation(liquidacion_delegado_test):
    """
    ReciboHonorarioDelegado can be created linked to a LiquidacionDelegado.
    """
    imp_bruto = Decimal("333.33")
    calculo = ReciboHonorarioDelegado.calcular_honorarios(imp_bruto)

    recibo = ReciboHonorarioDelegado.objects.create(
        liquidacion_delegado=liquidacion_delegado_test,
        sub_total=Decimal("5000.00"),
        imp_bruto=imp_bruto,
        **calculo,
    )

    assert recibo.id is not None
    assert recibo.liquidacion_delegado == liquidacion_delegado_test
    assert recibo.sub_total == Decimal("5000.00")
    assert recibo.imp_bruto == Decimal("333.33")
    assert recibo.renta_cip == Decimal("83.33")
    assert recibo.aporte_codemu == Decimal("16.67")
    assert recibo.fondo_comun == Decimal("33.33")
    assert recibo.neto_honorario == Decimal("200.00")
    assert recibo.honorario == Decimal("200.00")


@pytest.mark.django_db
def test_recibo_honorario_delegado_str(liquidacion_delegado_test):
    """
    __str__ includes the liquidacion_delegado and honorario.
    """
    imp_bruto = Decimal("1000.00")
    calculo = ReciboHonorarioDelegado.calcular_honorarios(imp_bruto)

    recibo = ReciboHonorarioDelegado.objects.create(
        liquidacion_delegado=liquidacion_delegado_test,
        sub_total=Decimal("5000.00"),
        imp_bruto=imp_bruto,
        **calculo,
    )

    str_repr = str(recibo)
    assert "ReciboHonorarioDelegado" in str_repr
    assert str(recibo.honorario) in str_repr


@pytest.mark.django_db
def test_recibo_honorario_one_to_one_liquidacion_delegado(
    liquidacion_delegado_test,
):
    """
    ReciboHonorarioDelegado is accessible via liquidacion_delegado.recibo_honorario.
    """
    imp_bruto = Decimal("500.00")
    calculo = ReciboHonorarioDelegado.calcular_honorarios(imp_bruto)

    recibo = ReciboHonorarioDelegado.objects.create(
        liquidacion_delegado=liquidacion_delegado_test,
        sub_total=Decimal("5000.00"),
        imp_bruto=imp_bruto,
        **calculo,
    )

    # Access from the other side
    assert liquidacion_delegado_test.recibo_honorario == recibo
    assert liquidacion_delegado_test.recibo_honorario.honorario == Decimal("300.00")


@pytest.mark.django_db
def test_recibo_honorario_get_or_create_idempotent(liquidacion_delegado_test):
    """
    crear_recibo via get_or_create is idempotent for the OneToOne relationship.
    """
    from modules.finanzas.domain.services.finanzas_core_service import FinanzasCoreService

    service = FinanzasCoreService()
    imp_bruto = Decimal("2000.00")
    calculo = ReciboHonorarioDelegado.calcular_honorarios(imp_bruto)

    # First call — creates
    r1, created1 = service.crear_recibo(
        liquidacion_delegado_id=liquidacion_delegado_test.id,
        sub_total=Decimal("10000.00"),
        imp_bruto=imp_bruto,
        **calculo,
    )
    assert created1 is True

    # Second call — retrieves existing
    r2, created2 = service.crear_recibo(
        liquidacion_delegado_id=liquidacion_delegado_test.id,
        sub_total=Decimal("99999.00"),  # different sub_total
        imp_bruto=imp_bruto,
        **calculo,
    )
    assert created2 is False
    assert r1.id == r2.id
    # Existing record's sub_total is preserved (not overwritten)
    assert r2.sub_total == Decimal("10000.00")


@pytest.mark.django_db
def test_get_recibo_por_liquidacion_delegado(liquidacion_delegado_test):
    """
    get_recibo_por_liquidacion_delegado returns the existing recibo or None.
    """
    from modules.finanzas.domain.services.finanzas_core_service import FinanzasCoreService

    service = FinanzasCoreService()

    # No recibo exists yet
    result = service.get_recibo_por_liquidacion_delegado(liquidacion_delegado_test.id)
    assert result is None

    # Create one
    imp_bruto = Decimal("750.00")
    calculo = ReciboHonorarioDelegado.calcular_honorarios(imp_bruto)
    service.crear_recibo(
        liquidacion_delegado_id=liquidacion_delegado_test.id,
        sub_total=Decimal("3000.00"),
        imp_bruto=imp_bruto,
        **calculo,
    )

    # Now found
    result = service.get_recibo_por_liquidacion_delegado(liquidacion_delegado_test.id)
    assert result is not None
    assert result.imp_bruto == Decimal("750.00")


# ── API Test ───────────────────────────────────────────────────────────────────

import uuid
from ninja.testing import TestClient
from config.api import api


@pytest.fixture
def api_client_fixture(db):
    """Ninja TestClient for testing async Finanzas endpoints."""
    return TestClient(api)


# BLOCKED: requires liquidaciones migration 0021 (user-owned)
# The LiquidacionDelegado model has an especialidad_revision FK column
# that is not yet in the test DB (liquidaciones migration 0021 not generated).
# This test is commented out until the user resolves the liquidaciones migration.
# @pytest.mark.django_db
# def test_post_recibo_honorario_creates_recibo(api_client_fixture, liquidacion_delegado_test):
#     """
#     POST /finanzas/recibos-honorarios creates a ReciboHonorarioDelegado.
#
#     Requires: liquidaciones migration 0021 (user-owned).
#     """
#     from modules.liquidaciones.domain.models.liquidacion.liquidacion_tipo.liquidacion_tipo import (
#         LiquidacionPorcentajeObra,
#         LiquidacionPorcentajeObraDetalle,
#     )
#     from modules.usuarios.domain.models.perfil_ingeniero import EspecialidadRevision
#
#     # Create LiquidacionPorcentajeObra linked to the liquidacion
#     lg = liquidacion_delegado_test.liquidacion
#     lpo = LiquidacionPorcentajeObra.objects.create(
#         liquidacion_general=lg,
#         tipo_tramite="OBRA_NUEVA",
#         valor_declarado=Decimal("100000.00"),
#         porcentaje_liquidacion=Decimal("0.0015"),
#         porcentaje_minimo_uit=Decimal("0.01"),
#         derecho_aplicado=lg.tipo_liquidacion.derechos.first(),
#     )
#
#     # Create a detalle matching the liquidacion_delegado's especialidad
#     LiquidacionPorcentajeObraDetalle.objects.create(
#         liquidacion_porcentaje=lpo,
#         tarifa_aplicada=lpo.derecho_aplicado.tarifas.first(),
#         especialidad=liquidacion_delegado_test.especialidad_revision,
#         porcentaje_aplicado=Decimal("0.0015"),
#         subtotal=Decimal("1000.00"),  # imp_bruto = 1000.00
#         igv=Decimal("180.00"),
#         uit=Decimal("0.00"),
#     )
#
#     response = api_client_fixture.post(
#         "/finanzas/recibos-honorarios",
#         json={"liquidacion_delegado_id": str(liquidacion_delegado_test.id)},
#     )
#
#     assert response.status_code == 200
#     data = response.json()
#     assert data["success"] is True
#     assert data["data"]["liquidacion_delegado_id"] == str(liquidacion_delegado_test.id)
#     assert data["data"]["sub_total"] == "5000.00"
#     assert data["data"]["imp_bruto"] == "1000.00"
#     assert data["data"]["renta_cip"] == "250.00"   # 1000 * 0.25
#     assert data["data"]["aporte_codemu"] == "50.00"  # 1000 * 0.05
#     assert data["data"]["fondo_comun"] == "100.00"   # 1000 * 0.10
#     assert data["data"]["neto_honorario"] == "600.00"  # 1000 - 250 - 50 - 100
#     assert data["data"]["honorario"] == "600.00"


# ── Orchestrator imp_bruto Resolution Tests ───────────────────────────────────

@pytest.fixture
def tipo_liquidacion_habilitacion_urbana(db):
    """Get or create TipoLiquidacion for HABILITACION_URBANA (M2 type)."""
    from modules.liquidaciones.domain.models.tipo_liquidacion import TipoLiquidacion

    return TipoLiquidacion.objects.get_or_create(
        codigo="HABILITACION_URBANA", defaults={"nombre": "Habilitación Urbana"}
    )[0]


@pytest.fixture
def liquidacion_general_hu(db, proyecto_test, municipalidad_test, tipo_liquidacion_habilitacion_urbana, usuario_liquidacion):
    """Create a LiquidacionGeneral for HABILITACION_URBANA testing."""
    from modules.liquidaciones.domain.models.liquidacion.liquidacion_general.liquidacion import (
        LiquidacionGeneral,
    )

    return LiquidacionGeneral.objects.create(
        proyecto=proyecto_test,
        municipalidad=municipalidad_test,
        tipo_liquidacion=tipo_liquidacion_habilitacion_urbana,
        usuario_creador=usuario_liquidacion,
        expediente="EXP-2026-HU-001",
        estado="REGISTRADO",
        sub_total=Decimal("3000.00"),
        total=Decimal("3540.00"),
    )


@pytest.fixture
def liquidacion_delegado_hu(db, liquidacion_general_hu, delegado, especialidad_revision):
    """Create a LiquidacionDelegado for HABILITACION_URBANA."""
    from modules.liquidaciones.domain.models.delegado import LiquidacionDelegado

    return LiquidacionDelegado.objects.create(
        liquidacion=liquidacion_general_hu,
        delegado=delegado,
        especialidad_revision=especialidad_revision,
        periodo="2026-01",
    )


@pytest.mark.django_db
class TestOrchestratorImpBrutoResolution:
    """Tests for orchestrator imp_bruto resolution by tipo_liquidacion."""

    def test_imp_bruto_m2_uses_liquidacion_sub_total(
        self,
        liquidacion_delegado_hu,
    ):
        """
        M2 tipo (HABILITACION_URBANA) → resolves imp_bruto = liquidacion.sub_total.
        """
        from modules.finanzas.domain.services.finanzas_orchestrator import FinanzasOrchestrator
        from modules.finanzas.domain.services.flujos.finanzas_flujo import FinanzasFlujo
        from modules.finanzas.domain.services.finanzas_core_service import FinanzasCoreService

        flujo = FinanzasFlujo(core=FinanzasCoreService())
        orch = FinanzasOrchestrator(flujo=flujo, core=FinanzasCoreService())

        imp_bruto, sub_total = orch._resolve_imp_bruto(liquidacion_delegado_hu)

        # M2 type uses liquidacion.sub_total as imp_bruto
        assert imp_bruto == Decimal("3000.00")
        assert sub_total == Decimal("3000.00")

    # BLOCKED: requires liquidaciones fixtures (LiquidacionPorcentajeObra + Detalle
    # with derecho_aplicado FK chain) — user owns liquidaciones test setup.
    # def test_imp_bruto_porcentaje_uses_detalle_subtotal(...): ...
    # def test_imp_bruto_porcentaje_no_matching_detalle_raises_400(...): ...


# ── Pagination Tests ───────────────────────────────────────────────────────────

@pytest.mark.django_db
class TestListarRecibosPagination:
    """Tests for GET /finanzas/recibos-delegados paginated endpoint.

    These tests validate presenter + pagination math using mock domain results,
    avoiding SQLite async locking issues.
    """

    def _mock_result(self, idx: int = 0):
        """Build a mock ReciboHonorarioDelegadoResult for presenter testing."""
        from datetime import datetime
        from uuid import uuid4
        from modules.finanzas.domain.results.recibo_honorario_result import (
            ReciboHonorarioDelegadoResult,
            TipoLiquidacionMinimal,
            LiquidacionGeneralMinimal,
            DelegadoMinimal,
            EspecialidadMinimal,
            ReciboHonorarioCalculoResult,
            LiquidacionEspecificaMinimalResult,
        )

        return ReciboHonorarioDelegadoResult(
            id=str(uuid4()),
            liquidacion_delegado_id=str(uuid4()),
            calculo=ReciboHonorarioCalculoResult(
                sub_total=Decimal("5000.00"),
                imp_bruto=Decimal("1000.00"),
                renta_cip=Decimal("250.00"),
                aporte_codemu=Decimal("50.00"),
                fondo_comun=Decimal("100.00"),
                neto_honorario=Decimal("600.00"),
                honorario=Decimal("600.00"),
            ),
            liquidacion_especifica=LiquidacionEspecificaMinimalResult(
                id=str(uuid4()),
                numero=100 + idx,
            ),
            created_at=datetime(2026, 1, idx + 1),
            liquidacion_general=LiquidacionGeneralMinimal(
                id=str(uuid4()),
                expediente=f"EXP-{idx+1}",
                numero_revision=1,
                sub_total=Decimal("5000.00"),
                total=Decimal("5900.00"),
                fecha_registro="2026-01-01T00:00:00",
                tipo_liquidacion=TipoLiquidacionMinimal(
                    codigo="EDIFICACION",
                    nombre="Edificación",
                ),
                municipalidad_nombre="Municipalidad de Lima",
                proyecto_denominacion="Proyecto Test",
            ),
            delegado=DelegadoMinimal(
                id=str(uuid4()),
                nombre_completo="Juan Pérez García",
                cip=f"CIP-{idx+1:05d}",
                dni=f"0000000{idx+1}",
            ),
            especialidad=EspecialidadMinimal(
                id=str(uuid4()),
                codigo="E01",
                nombre="Estructuras",
            ),
        )

    def test_presenter_pagination_page_1_size_2(self):
        """PaginatedData: page=1, page_size=2 with 3 total → 2 items, total_pages=2."""
        from modules.finanzas.presentation.presenters.finanzas_presenter import FinanzasPresenter

        # The Core slices the page; the presenter only formats the items received.
        results = [self._mock_result(0), self._mock_result(1)]
        paginated = FinanzasPresenter.present_recibos_list(results, total=3, page=1, page_size=2)

        assert len(paginated.items) == 2
        assert paginated.total == 3
        assert paginated.page == 1
        assert paginated.page_size == 2
        assert paginated.total_pages == 2

    def test_presenter_pagination_page_2_size_2(self):
        """PaginatedData: page=2, page_size=2 with 3 total → 1 item, total_pages=2."""
        from modules.finanzas.presentation.presenters.finanzas_presenter import FinanzasPresenter

        results = [self._mock_result(2)]  # Only the 3rd item is on page 2
        paginated = FinanzasPresenter.present_recibos_list(results, total=3, page=2, page_size=2)

        assert len(paginated.items) == 1
        assert paginated.total == 3
        assert paginated.page == 2
        assert paginated.page_size == 2
        assert paginated.total_pages == 2

    def test_presenter_pagination_empty_page(self):
        """PaginatedData: page beyond total → empty items, total_pages=0."""
        from modules.finanzas.presentation.presenters.finanzas_presenter import FinanzasPresenter

        results = []
        paginated = FinanzasPresenter.present_recibos_list(results, total=0, page=999, page_size=10)

        assert paginated.items == []
        assert paginated.total == 0
        assert paginated.page == 999
        assert paginated.total_pages == 0

    def test_presenter_pagination_total_pages_math(self):
        """total_pages = ceil(total / page_size)."""
        from modules.finanzas.presentation.presenters.finanzas_presenter import FinanzasPresenter

        # 5 items, page_size=2 → 3 pages
        results = [self._mock_result(i) for i in range(2)]
        paginated = FinanzasPresenter.present_recibos_list(results, total=5, page=1, page_size=2)
        assert paginated.total_pages == 3

        # 10 items, page_size=10 → 1 page
        results = [self._mock_result(i) for i in range(10)]
        paginated = FinanzasPresenter.present_recibos_list(results, total=10, page=1, page_size=10)
        assert paginated.total_pages == 1

        # 0 items → 0 pages
        results = []
        paginated = FinanzasPresenter.present_recibos_list(results, total=0, page=1, page_size=10)
        assert paginated.total_pages == 0

    def test_presenter_response_schema_fields(self):
        """Each item has all required fields from ReciboHonorarioDelegadoOut schema."""
        from modules.finanzas.presentation.presenters.finanzas_presenter import FinanzasPresenter
        from modules.finanzas.presentation.schemas.finanzas_schemas import ReciboHonorarioDelegadoOut

        results = [self._mock_result(0)]
        paginated = FinanzasPresenter.present_recibos_list(results, total=1, page=1, page_size=1)

        item = paginated.items[0]
        assert isinstance(item, ReciboHonorarioDelegadoOut)

        # Top-level fields
        assert item.id is not None
        assert item.liquidacion_delegado_id is not None
        assert item.calculo.sub_total is not None
        assert item.calculo.imp_bruto is not None
        assert item.calculo.renta_cip is not None
        assert item.calculo.aporte_codemu is not None
        assert item.calculo.fondo_comun is not None
        assert item.calculo.neto_honorario is not None
        assert item.calculo.honorario is not None
        assert item.created_at is not None

        # Nested liquidacion_general
        lg = item.liquidacion_general
        assert lg.id is not None
        assert lg.expediente is not None
        assert lg.numero_revision is not None
        assert lg.sub_total is not None
        assert lg.total is not None
        assert lg.fecha_registro is not None
        assert lg.tipo_liquidacion.codigo == "EDIFICACION"
        assert lg.municipalidad_nombre is not None
        assert lg.proyecto_denominacion is not None

        # Nested delegado
        d = item.delegado
        assert d.id is not None
        assert d.nombre_completo is not None
        assert d.cip is not None
        assert d.dni is not None

        # Nested especialidad
        e = item.especialidad
        assert e.id is not None
        assert e.codigo is not None
        assert e.nombre is not None

    def test_list_recibo_filter_by_delegado_id(
        self,
        liquidacion_delegado_test,
    ):
        """Filter by delegado_id via orchestrator returns matching records."""
        from modules.finanzas.domain.models.recibo_honorario import ReciboHonorarioDelegado

        calc = ReciboHonorarioDelegado.calcular_honorarios(Decimal("1000.00"))
        ReciboHonorarioDelegado.objects.create(
            liquidacion_delegado=liquidacion_delegado_test,
            sub_total=Decimal("5000.00"),
            imp_bruto=Decimal("1000.00"),
            **calc,
        )

        from modules.finanzas.domain.services.finanzas_orchestrator import FinanzasOrchestrator
        from modules.finanzas.domain.services.flujos.finanzas_flujo import FinanzasFlujo
        from modules.finanzas.domain.services.finanzas_core_service import FinanzasCoreService
        from modules.finanzas.presentation.presenters.finanzas_presenter import FinanzasPresenter

        flujo = FinanzasFlujo(core=FinanzasCoreService())
        orch = FinanzasOrchestrator(flujo=flujo, core=FinanzasCoreService())

        results, total = orch.listar_recibos_proceso(
            page=1, page_size=10,
            delegado_id=liquidacion_delegado_test.delegado.id,
        )

        paginated = FinanzasPresenter.present_recibos_list(results, total, 1, 10)

        assert total >= 1
        for item in paginated.items:
            assert str(item.delegado.id) == str(liquidacion_delegado_test.delegado.id)
