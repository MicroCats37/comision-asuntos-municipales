# -*- coding: utf-8 -*-
"""
Integration tests for Reparticion Estacional flows.

Tests:
- Cotizar: preview calculation without persisting
- Crear: persist snapshot with atomic transaction
- Overlap validation: reject overlapping month ranges for same specialty/period
- Math precision: 4 decimal places for share, residual captured correctly
- Soft delete: reparticion can be soft-deleted

Fixtures are defined locally following the finanzas test pattern.
"""
import pytest
from datetime import date
from decimal import Decimal

from ninja.testing import TestClient
from ninja_jwt.tokens import AccessToken
from django.contrib.auth import get_user_model

from config.api import api
from modules.usuarios.domain.models.perfil_ingeniero import (
    EspecialidadRevision,
    EspecialidadRevisionCapitulo,
    Capitulo,
    PerfilIngeniero,
)
from modules.liquidaciones.domain.models.delegado import Delegado
from modules.finanzas.domain.models.rh_reparticion_estacional import (
    RHReparticionEstacional,
    RHReparticionEstacionalDelegado,
    RHReparticionEstacionalCapitulo,
)
from modules.finanzas.domain.models.detalle_honorario_delegado import DetalleHonorarioDelegado
from modules.finanzas.domain.models.recibo_honorario_delegado_mensual import ReciboHonorarioDelegadoMensual
from modules.finanzas.domain.services.core.rh_reparticion_estacional_core_service import (
    RHReparticionEstacionalCoreService,
)
from modules.finanzas.domain.services.flujos.rh_reparticion_estacional_flujo import (
    RHReparticionEstacionalFlujo,
)
from modules.finanzas.domain.services.orchestrators.rh_reparticion_estacional_orchestrator import (
    RHReparticionEstacionalOrchestrator,
)


# ── Fixtures ────────────────────────────────────────────────────────────────────

@pytest.fixture
def api_client(db):
    """Ninja TestClient for testing Ninja endpoints."""
    return TestClient(api)


@pytest.fixture
def create_user(db):
    """Create a test user."""
    User = get_user_model()
    return User.objects.create_user(
        username="test_user_re",
        email="test_re@example.com",
        password="testpass123",
        dni="12345671",
    )


@pytest.fixture
def auth_client(api_client, create_user):
    """JWT-authenticated test client."""
    user = create_user
    token = AccessToken.for_user(user)
    api_client.headers.update({"Authorization": f"Bearer {token}"})
    api_client.user = user
    return api_client


@pytest.fixture
def capitulo_civil(db):
    """Capítulo CIVIL (registro_id=02)."""
    return Capitulo.objects.create(
        registro_id="02",
        abreviacion="CIVIL",
        nombre="Ingeniería Civil",
    )


@pytest.fixture
def capitulo_sanitaria(db):
    """Capítulo SANITARIA (registro_id=09)."""
    return Capitulo.objects.create(
        registro_id="09",
        abreviacion="SANITARIA",
        nombre="Ingeniería Sanitaria",
    )


@pytest.fixture
def capitulo_electrica(db):
    """Capítulo ELÉCTRICA (registro_id=15)."""
    return Capitulo.objects.create(
        registro_id="15",
        abreviacion="ELECTRICA",
        nombre="Ingeniería Eléctrica",
    )


@pytest.fixture
def especialidad_revision_civil(db):
    """EspecialidadRevision for Civil."""
    return EspecialidadRevision.objects.create(
        slug="ingenieria-civil",
        nombre="Ingeniería Civil",
    )


@pytest.fixture
def especialidad_revision_sanitaria(db):
    """EspecialidadRevision for Sanitaria."""
    return EspecialidadRevision.objects.create(
        slug="ingenieria-sanitaria",
        nombre="Ingeniería Sanitaria",
    )


@pytest.fixture
def especialidad_revision_electrica(db):
    """EspecialidadRevision for Electrical/Mechanical."""
    return EspecialidadRevision.objects.create(
        slug="ingenieria-electrica-y-mecanica-electrica",
        nombre="Ingeniería Eléctrica y Mecánica",
    )


@pytest.fixture
def especialidad_capitulo_mapping_civil(db, especialidad_revision_civil, capitulo_civil):
    """Map Civil especialidad to CIVIL chapter."""
    return EspecialidadRevisionCapitulo.objects.create(
        especialidad_revision=especialidad_revision_civil,
        capitulo=capitulo_civil,
    )


@pytest.fixture
def especialidad_capitulo_mapping_sanitaria(db, especialidad_revision_sanitaria, capitulo_sanitaria):
    """Map Sanitaria especialidad to SANITARIA chapter."""
    return EspecialidadRevisionCapitulo.objects.create(
        especialidad_revision=especialidad_revision_sanitaria,
        capitulo=capitulo_sanitaria,
    )


@pytest.fixture
def especialidad_capitulo_mapping_electrica(db, especialidad_revision_electrica, capitulo_electrica):
    """Map Electrical/Mechanical especialidad to ELECTRICA chapter."""
    return EspecialidadRevisionCapitulo.objects.create(
        especialidad_revision=especialidad_revision_electrica,
        capitulo=capitulo_electrica,
    )


@pytest.fixture
def perfil_ingeniero_delegado_1(db):
    """PerfilIngeniero for delegate 1."""
    return PerfilIngeniero.objects.create(
        cip="DELEGADO-CIP-001",
        dni="11111111",
        nombres="Carlos",
        apellido_paterno="Ramirez",
        apellido_materno="Lopez",
    )


@pytest.fixture
def perfil_ingeniero_delegado_2(db):
    """PerfilIngeniero for delegate 2."""
    return PerfilIngeniero.objects.create(
        cip="DELEGADO-CIP-002",
        dni="22222222",
        nombres="Ana",
        apellido_paterno="Torres",
        apellido_materno="Meza",
    )


@pytest.fixture
def delegado_1(db, perfil_ingeniero_delegado_1):
    """Delegado 1."""
    return Delegado.objects.create(
        perfil_ingeniero=perfil_ingeniero_delegado_1,
    )


@pytest.fixture
def delegado_2(db, perfil_ingeniero_delegado_2):
    """Delegado 2."""
    return Delegado.objects.create(
        perfil_ingeniero=perfil_ingeniero_delegado_2,
    )


@pytest.fixture
def recibo_mensual(db, delegado_1):
    """ReciboHonorarioDelegadoMensual for testing."""
    return ReciboHonorarioDelegadoMensual.objects.create(
        delegado=delegado_1,
        periodo=2026,
        mes=1,
        sub_total=Decimal("1000.00"),
        renta_cip=Decimal("250.00"),
        aporte_codemu=Decimal("50.00"),
        fondo_comun=Decimal("100.00"),
        neto_honorario=Decimal("600.00"),
    )


# ── Tests ──────────────────────────────────────────────────────────────────────

@pytest.mark.django_db
def test_core_service_get_capitulos_for_especialidad(
    especialidad_revision_civil,
    especialidad_capitulo_mapping_civil,
    capitulo_civil,
):
    """
    Core service returns capitulo IDs linked to an EspecialidadRevision.
    """
    core = RHReparticionEstacionalCoreService()
    capitulo_ids = core.get_capitulos_for_especialidad(
        especialidad_revision_id=int(especialidad_revision_civil.id),
    )
    assert capitulo_civil.id in capitulo_ids


@pytest.mark.django_db
def test_core_service_check_overlap_no_overlap(
    especialidad_revision_civil,
):
    """
    No overlap detected when ranges don't intersect.
    """
    core = RHReparticionEstacionalCoreService()
    # First reparticion: months 1-3
    RHReparticionEstacional.objects.create(
        especialidad_revision=especialidad_revision_civil,
        periodo=2026,
        total_fondo_comun=Decimal("1000.00"),
        numero_capitulos=1,
        numero_delegados=2,
        monto_por_participacion=Decimal("333.3333"),
        residual=Decimal("0.00"),
        mes_desde=1,
        mes_hasta=3,
    )
    # Check overlap with months 5-7 — no overlap
    has_overlap = core.check_overlapping_reparticion(
        especialidad_revision_id=int(especialidad_revision_civil.id),
        periodo=2026,
        mes_desde=5,
        mes_hasta=7,
    )
    assert has_overlap is False


@pytest.mark.django_db
def test_core_service_check_overlap_with_overlap(
    especialidad_revision_civil,
):
    """
    Overlap detected when ranges intersect.
    """
    core = RHReparticionEstacionalCoreService()
    # First reparticion: months 1-5
    RHReparticionEstacional.objects.create(
        especialidad_revision=especialidad_revision_civil,
        periodo=2026,
        total_fondo_comun=Decimal("1000.00"),
        numero_capitulos=1,
        numero_delegados=2,
        monto_por_participacion=Decimal("333.3333"),
        residual=Decimal("0.00"),
        mes_desde=1,
        mes_hasta=5,
    )
    # Check overlap with months 3-7 — overlap (3-5 intersects with 1-5)
    has_overlap = core.check_overlapping_reparticion(
        especialidad_revision_id=int(especialidad_revision_civil.id),
        periodo=2026,
        mes_desde=3,
        mes_hasta=7,
    )
    assert has_overlap is True


@pytest.mark.django_db
def test_core_service_soft_delete(
    especialidad_revision_civil,
):
    """
    Soft delete sets is_deleted=True and deleted_at.
    """
    core = RHReparticionEstacionalCoreService()
    rep = RHReparticionEstacional.objects.create(
        especialidad_revision=especialidad_revision_civil,
        periodo=2026,
        total_fondo_comun=Decimal("1000.00"),
        numero_capitulos=1,
        numero_delegados=2,
        monto_por_participacion=Decimal("333.3333"),
        residual=Decimal("0.00"),
        mes_desde=1,
        mes_hasta=3,
    )
    core.soft_delete_reparticion(rep)
    rep.refresh_from_db()
    assert rep.is_deleted is True
    assert rep.deleted_at is not None


# ── Endpoint Tests ─────────────────────────────────────────────────────────────────

@pytest.mark.django_db
def test_endpoint_list_returns_active(
    auth_client,
    especialidad_revision_civil,
):
    """
    GET /finanzas/reparticiones-estacionales returns active reparticiones.
    """
    # Create an active reparticion
    RHReparticionEstacional.objects.create(
        especialidad_revision=especialidad_revision_civil,
        periodo=2026,
        total_fondo_comun=Decimal("1000.00"),
        numero_capitulos=1,
        numero_delegados=2,
        monto_por_participacion=Decimal("333.3333"),
        residual=Decimal("0.00"),
        mes_desde=1,
        mes_hasta=3,
    )
    # Create a deleted reparticion
    RHReparticionEstacional.objects.create(
        especialidad_revision=especialidad_revision_civil,
        periodo=2025,
        total_fondo_comun=Decimal("500.00"),
        numero_capitulos=1,
        numero_delegados=1,
        monto_por_participacion=Decimal("250.0000"),
        residual=Decimal("0.00"),
        mes_desde=1,
        mes_hasta=6,
        is_deleted=True,
    )
    response = auth_client.get("/finanzas/reparticiones-estacionales")
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    results = data["data"]
    # Only active (non-deleted) should be returned
    assert len(results) == 1
    assert results[0]["periodo"] == 2026


@pytest.mark.django_db
def test_endpoint_delete_soft_deletes(
    auth_client,
    especialidad_revision_civil,
):
    """
    DELETE /finanzas/reparticiones-estacionales/{id} soft-deletes.
    """
    rep = RHReparticionEstacional.objects.create(
        especialidad_revision=especialidad_revision_civil,
        periodo=2026,
        total_fondo_comun=Decimal("1000.00"),
        numero_capitulos=1,
        numero_delegados=2,
        monto_por_participacion=Decimal("333.3333"),
        residual=Decimal("0.00"),
        mes_desde=1,
        mes_hasta=3,
    )
    response = auth_client.delete(f"/finanzas/reparticiones-estacionales/{rep.id}")
    assert response.status_code == 200
    rep.refresh_from_db()
    assert rep.is_deleted is True
    assert rep.deleted_at is not None


@pytest.mark.django_db
def test_endpoint_cotizar_validates_especialidad_not_found(
    auth_client,
):
    """
    POST /finanzas/reparticiones-estacionales/cotizar returns 404 for unknown especialidad.
    """
    import uuid
    payload = {
        "especialidad_revision_id": str(uuid.uuid4()),
        "periodo": 2026,
        "mes_desde": 1,
        "mes_hasta": 3,
        "delegado_ids": [],
    }
    response = auth_client.post(
        "/finanzas/reparticiones-estacionales/cotizar",
        json=payload,
    )
    assert response.status_code == 404


@pytest.mark.django_db
def test_endpoint_crear_validates_delegate_not_found(
    auth_client,
    especialidad_revision_civil,
):
    """
    POST /finanzas/reparticiones-estacionales returns 404 for unknown delegate.
    """
    import uuid
    payload = {
        "especialidad_revision_id": str(especialidad_revision_civil.id),
        "periodo": 2026,
        "mes_desde": 1,
        "mes_hasta": 3,
        "delegado_ids": [str(uuid.uuid4())],
    }
    response = auth_client.post(
        "/finanzas/reparticiones-estacionales",
        json=payload,
    )
    assert response.status_code == 404


# ── Exact-Cent Distribution Tests ─────────────────────────────────────────────────

from modules.finanzas.domain.services.core.rh_reparticion_estacional_core_service import (
    distribute_fondo_comun_cents,
)


class TestDistributeFondoComunCents:
    """Pure helper tests for distribute_fondo_comun_cents — no DB required."""

    def test_100_over_3_chapter_priority(self):
        """
        100.00 / 3: 1 chapter + 2 delegates.
        Expected: chapter=33.34, delegates=33.33, 33.33.
        Sum: 33.34 + 33.33 + 33.33 = 100.00. Residual: 0.00.
        """
        total = Decimal("100.00")
        capitulo_ids = [5]
        delegado_ids = [10, 20]

        capitulo_amounts, delegado_amounts, base, residual = distribute_fondo_comun_cents(
            total, capitulo_ids, delegado_ids
        )

        assert base == Decimal("33.33")
        assert capitulo_amounts[5] == Decimal("33.34")
        assert delegado_amounts[10] == Decimal("33.33")
        assert delegado_amounts[20] == Decimal("33.33")

        sum_cents = (
            int(capitulo_amounts[5] * 100)
            + int(delegado_amounts[10] * 100)
            + int(delegado_amounts[20] * 100)
        )
        assert sum_cents == 10000
        assert residual == Decimal("0.00")

    def test_403_over_4_chapters_and_delegados(self):
        """
        4.03 / 4: 2 chapters + 2 delegates.
        Total cents = 403. base_cents = 403 // 4 = 100.
        leftover = 403 % 4 = 3.
        extra_per_chapter = 3 // 2 = 1.
        remainder = 3 % 2 = 1.
        Chapter[0] (sorted ID=1): 100+1+1=102 → 1.02.
        Chapter[1] (sorted ID=2): 100+1=101 → 1.01.
        Delegados: 100 cents = 1.00 each.
        Sum: 102+101+100+100 = 403 cents = 4.03. Residual: 0.00.
        """
        total = Decimal("4.03")
        capitulo_ids = [1, 2]
        delegado_ids = [10, 11]

        capitulo_amounts, delegado_amounts, base, residual = distribute_fondo_comun_cents(
            total, capitulo_ids, delegado_ids
        )

        assert base == Decimal("1.00")
        assert capitulo_amounts[1] == Decimal("1.02")
        assert capitulo_amounts[2] == Decimal("1.01")
        assert delegado_amounts[10] == Decimal("1.00")
        assert delegado_amounts[11] == Decimal("1.00")

        sum_cents = (
            int(capitulo_amounts[1] * 100)
            + int(capitulo_amounts[2] * 100)
            + int(delegado_amounts[10] * 100)
            + int(delegado_amounts[11] * 100)
        )
        assert sum_cents == 403
        assert residual == Decimal("0.00")

    def test_delegados_never_get_extra_cents(self):
        """
        Even when leftover >> number of chapters, delegates always get base.
        10.00 / 4: 1 chapter + 3 delegates.
        """
        total = Decimal("10.00")
        capitulo_ids = [1]
        delegado_ids = [10, 20, 30]

        capitulo_amounts, delegado_amounts, base, residual = distribute_fondo_comun_cents(
            total, capitulo_ids, delegado_ids
        )

        assert base == Decimal("2.50")
        assert capitulo_amounts[1] == Decimal("2.50")
        assert delegado_amounts[10] == Decimal("2.50")
        assert delegado_amounts[20] == Decimal("2.50")
        assert delegado_amounts[30] == Decimal("2.50")
        assert residual == Decimal("0.00")

    def test_all_leftover_goes_to_chapters(self):
        """
        1.00 / 3: 1 chapter + 2 delegates.
        Total cents = 100. base_cents = 33. leftover = 1.
        Chapter: 33+1=34 → 0.34. Delegados: 0.33 each.
        Sum: 34+33+33 = 100 cents = 1.00.
        """
        total = Decimal("1.00")
        capitulo_ids = [1]
        delegado_ids = [10, 20]

        capitulo_amounts, delegado_amounts, base, residual = distribute_fondo_comun_cents(
            total, capitulo_ids, delegado_ids
        )

        assert base == Decimal("0.33")
        assert capitulo_amounts[1] == Decimal("0.34")
        assert delegado_amounts[10] == Decimal("0.33")
        assert delegado_amounts[20] == Decimal("0.33")

        sum_cents = int(capitulo_amounts[1] * 100) + int(delegado_amounts[10] * 100) + int(delegado_amounts[20] * 100)
        assert sum_cents == 100
        assert residual == Decimal("0.00")

    def test_deterministic_chapter_ordering_for_remainder(self):
        """
        Results are keyed by original ID; amounts are deterministic regardless of input order.
        1.05 / 5: 3 chapters + 2 delegates (evenly divisible).
        """
        total = Decimal("1.05")
        capitulo_ids = [3, 1, 2]    # unsorted input
        delegado_ids = [20, 10]

        capitulo_amounts, _, base, residual = distribute_fondo_comun_cents(
            total, capitulo_ids, delegado_ids
        )

        assert base == Decimal("0.21")
        assert residual == Decimal("0.00")
        assert capitulo_amounts[1] == Decimal("0.21")
        assert capitulo_amounts[2] == Decimal("0.21")
        assert capitulo_amounts[3] == Decimal("0.21")

    def test_empty_inputs(self):
        """Empty capitulo and delegado lists — residual is the whole amount."""
        capitulo_amounts, delegado_amounts, base, residual = distribute_fondo_comun_cents(
            Decimal("100.00"), [], []
        )
        assert capitulo_amounts == {}
        assert delegado_amounts == {}
        assert base == Decimal("0.00")
        assert residual == Decimal("100.00")


# ── Integration Tests for Cotizar Exact Distribution ──────────────────────────────────────────────


from unittest.mock import patch


@pytest.mark.django_db
def test_cotizar_exact_100_over_3_chapter_priority(
    especialidad_revision_civil,
    especialidad_capitulo_mapping_civil,
    capitulo_civil,
    perfil_ingeniero_delegado_1,
    perfil_ingeniero_delegado_2,
    delegado_1,
    delegado_2,
):
    """
    cotizar: 100.00 total, 1 chapter + 2 delegates.
    chapter → 33.34, each delegado → 33.33.
    sum = 100.00, residual = 0.00.
    """
    core = RHReparticionEstacionalCoreService()

    with patch.object(core, "get_fondo_comun_total", return_value=Decimal("100.00")):
        with patch.object(
            core,
            "get_capitulos_for_especialidad",
            return_value=[int(capitulo_civil.id)],
        ):
            flujo = RHReparticionEstacionalFlujo(core=core)
            result = flujo._cotizar(
                especialidad_revision_id=int(especialidad_revision_civil.id),
                periodo=2026,
                mes_desde=1,
                mes_hasta=3,
                delegado_ids=[int(delegado_1.id), int(delegado_2.id)],
            )

    assert len(result.detalles_capitulos) == 1
    chapter_monto = result.detalles_capitulos[0].monto
    assert chapter_monto == Decimal("33.34")

    assert len(result.detalles_delegados) == 2
    delegado_montos = [d.monto for d in result.detalles_delegados]
    assert all(m == Decimal("33.33") for m in delegado_montos)

    total_sum = chapter_monto + sum(delegado_montos)
    assert total_sum == Decimal("100.00")
    assert result.residual == Decimal("0.00")
    assert result.monto_por_participacion == Decimal("33.33")


@pytest.mark.django_db
def test_cotizar_exact_403_over_4_chapters_and_delegados(
    especialidad_revision_civil,
    especialidad_capitulo_mapping_civil,
    capitulo_civil,
    capitulo_sanitaria,
    especialidad_capitulo_mapping_sanitaria,
    perfil_ingeniero_delegado_1,
    perfil_ingeniero_delegado_2,
    delegado_1,
    delegado_2,
):
    """
    cotizar: 4.03 total, 2 chapters + 2 delegates.
    chapters → 1.02 and 1.01, delegados → 1.00 and 1.00.
    sum = 4.03, residual = 0.00.
    """
    core = RHReparticionEstacionalCoreService()

    with patch.object(core, "get_fondo_comun_total", return_value=Decimal("4.03")):
        with patch.object(
            core,
            "get_capitulos_for_especialidad",
            return_value=[int(capitulo_civil.id), int(capitulo_sanitaria.id)],
        ):
            flujo = RHReparticionEstacionalFlujo(core=core)
            result = flujo._cotizar(
                especialidad_revision_id=int(especialidad_revision_civil.id),
                periodo=2026,
                mes_desde=1,
                mes_hasta=3,
                delegado_ids=[int(delegado_1.id), int(delegado_2.id)],
            )

    capitulo_montos = sorted([d.monto for d in result.detalles_capitulos])
    assert capitulo_montos == [Decimal("1.01"), Decimal("1.02")]

    delegado_montos = [d.monto for d in result.detalles_delegados]
    assert all(m == Decimal("1.00") for m in delegado_montos)

    total_sum = sum(d.monto for d in result.detalles_delegados) + sum(d.monto for d in result.detalles_capitulos)
    assert total_sum == Decimal("4.03")
    assert result.residual == Decimal("0.00")
    assert result.monto_por_participacion == Decimal("1.00")


@pytest.mark.django_db
def test_cotizar_delegados_uniform_regardless_of_leftover(
    especialidad_revision_civil,
    especialidad_capitulo_mapping_civil,
    capitulo_civil,
    perfil_ingeniero_delegado_1,
    perfil_ingeniero_delegado_2,
    delegado_1,
    delegado_2,
):
    """
    Even when leftover cents exist, all delegados receive the same base amount.
    Chapter receives extra; delegates never do.
    """
    core = RHReparticionEstacionalCoreService()

    with patch.object(core, "get_fondo_comun_total", return_value=Decimal("1.01")):
        with patch.object(
            core,
            "get_capitulos_for_especialidad",
            return_value=[int(capitulo_civil.id)],
        ):
            flujo = RHReparticionEstacionalFlujo(core=core)
            result = flujo._cotizar(
                especialidad_revision_id=int(especialidad_revision_civil.id),
                periodo=2026,
                mes_desde=1,
                mes_hasta=3,
                delegado_ids=[int(delegado_1.id), int(delegado_2.id)],
            )

    assert len(result.detalles_delegados) == 2
    assert len(result.detalles_capitulos) == 1

    montos = [d.monto for d in result.detalles_delegados]
    assert len(set(montos)) == 1, f"Delegados must be uniform, got {montos}"

    chapter_monto = result.detalles_capitulos[0].monto
    delegate_monto = result.detalles_delegados[0].monto
    assert chapter_monto > delegate_monto, "Chapter must receive more than delegate"

    total_sum = sum(d.monto for d in result.detalles_delegados) + chapter_monto
    assert total_sum == Decimal("1.01")
    assert result.residual == Decimal("0.00")


@pytest.mark.django_db
def test_cotizar_returns_delegado_profile_fields(
    especialidad_revision_civil,
    especialidad_capitulo_mapping_civil,
    capitulo_civil,
    perfil_ingeniero_delegado_1,
    perfil_ingeniero_delegado_2,
    delegado_1,
    delegado_2,
):
    """
    cotizar returns delegated profile fields (cip, dni, nombre_completo)
    in the detalle_delegados response, not just amounts.

    The orchestrator resolves string UUIDs from the HTTP payload to actual
    Delegado UUID objects and passes them to _cotizar. Here we replicate
    that by passing the UUID objects directly (delegado_1.id, delegado_2.id),
    which are the actual PKs stored as keys in delegados_map.
    """
    core = RHReparticionEstacionalCoreService()

    with patch.object(core, "get_fondo_comun_total", return_value=Decimal("100.00")):
        with patch.object(
            core,
            "get_capitulos_for_especialidad",
            return_value=[int(capitulo_civil.id)],
        ):
            flujo = RHReparticionEstacionalFlujo(core=core)
            result = flujo._cotizar(
                especialidad_revision_id=int(especialidad_revision_civil.id),
                periodo=2026,
                mes_desde=1,
                mes_hasta=3,
                # Pass UUID objects — matching what the orchestrator passes to _cotizar
                # (it does Delegado.objects.filter(...).first() then deleg.id which is UUID)
                delegado_ids=[delegado_1.id, delegado_2.id],
            )

    assert len(result.detalles_delegados) == 2

    # Collect all profile fields across both delegates
    cip_values = {d.delegado.cip for d in result.detalles_delegados}
    dni_values = {d.delegado.dni for d in result.detalles_delegados}
    nombre_values = {d.delegado.nombre_completo for d in result.detalles_delegados}

    assert cip_values == {"DELEGADO-CIP-001", "DELEGADO-CIP-002"}
    assert dni_values == {"11111111", "22222222"}
    assert nombre_values == {"Carlos Ramirez Lopez", "Ana Torres Meza"}

    # All montos are present and non-zero
    assert all(d.monto > 0 for d in result.detalles_delegados)
