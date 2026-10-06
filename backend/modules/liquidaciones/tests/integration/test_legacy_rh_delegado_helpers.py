"""
Tests for Phase 2 RH Delegado helpers in import_legacy_edificaciones.

Tests the helper functions outside the Command class:
- _resolve_slot_especialidad_revision
- _ensure_perfil_ingeniero_by_cip
- _ensure_delegado_for_perfil
- _ensure_delegado_operacion
- _get_existing_delegado_operacion

Coverage:
1. PerfilIngeniero is created/reused by normalized CIP
2. Delegado is created/reused for a profile
3. DelegadoOperacion is created with default tipo=TITULAR
4. DelegadoOperacionPeriodo is NOT created
5. Existing operation is reused idempotently
6. Specialty conflict is reported/reused without overwriting
7. Dry-run does not write profile/delegado/operation
8. Slot specialty mapping includes slot 4 Electrónica

Fixtures:
- Domain model fixtures (especialidad_revision, municipalidad, tipo_edificacion)
  created inline within tests — unique to this file's domain scope.
- Row fixtures use make_row() and make_full_row() from test_legacy_rh_parser.py
  (same patterns).

Test strategy: integration tests with @pytest.mark.django_db — real DB,
real ORM, no mocks.
"""

import pytest
from decimal import Decimal

from modules.liquidaciones.management.commands.import_legacy_edificaciones import (
    _resolve_slot_especialidad_revision,
    _ensure_perfil_ingeniero_by_cip,
    _ensure_delegado_for_perfil,
    _ensure_delegado_operacion,
    _get_existing_delegado_operacion,
    _SLOT_SPECIALTY_DB_MAP,
)
from modules.liquidaciones.domain.constants import TipoDelegado
from modules.liquidaciones.domain.models.delegado import (
    Delegado,
    DelegadoOperacion,
    DelegadoOperacionPeriodo,
)
from modules.usuarios.domain.models.perfil_ingeniero import (
    EspecialidadRevision,
    PerfilIngeniero,
)


# ── Fixtures ────────────────────────────────────────────────────────────────────

@pytest.fixture
def especialidad_civil(db):
    """EspecialidadRevision for Ingeniería Civil (slot 1)."""
    return EspecialidadRevision.objects.create(
        slug="civil",
        nombre="Ingeniería Civil",
    )


@pytest.fixture
def especialidad_sanitaria(db):
    """EspecialidadRevision for Ingeniería Sanitaria (slot 2)."""
    return EspecialidadRevision.objects.create(
        slug="sanitaria",
        nombre="Ingeniería Sanitaria",
    )


@pytest.fixture
def especialidad_electrica(db):
    """EspecialidadRevision for Ingeniería Eléctrica y Mecánica Eléctrica (slot 3)."""
    return EspecialidadRevision.objects.create(
        slug="electrica",
        nombre="Ingeniería Eléctrica y Mecánica Eléctrica",
    )


@pytest.fixture
def especialidad_electronica(db):
    """EspecialidadRevision for Ingeniería Electrónica (slot 4)."""
    return EspecialidadRevision.objects.create(
        slug="electronica",
        nombre="Ingeniería Electrónica",
    )


# ── Tests: _resolve_slot_especialidad_revision ───────────────────────────────────

class TestResolveSlotEspecialidadRevision:
    """Tests for slot -> EspecialidadRevision resolution."""

    def test_slot1_resolves_to_ingenieria_civil(self, db, especialidad_civil):
        """Slot 1 resolves to Ingeniería Civil."""
        result = _resolve_slot_especialidad_revision(1)
        assert result is not None
        assert result.nombre == "Ingeniería Civil"

    def test_slot2_resolves_to_ingenieria_sanitaria(self, db, especialidad_sanitaria):
        """Slot 2 resolves to Ingeniería Sanitaria."""
        result = _resolve_slot_especialidad_revision(2)
        assert result is not None
        assert result.nombre == "Ingeniería Sanitaria"

    def test_slot3_resolves_to_ingenieria_electrica(self, db, especialidad_electrica):
        """Slot 3 resolves to Ingeniería Eléctrica y Mecánica Eléctrica."""
        result = _resolve_slot_especialidad_revision(3)
        assert result is not None
        assert result.nombre == "Ingeniería Eléctrica y Mecánica Eléctrica"

    def test_slot4_resolves_to_ingenieria_electronica(self, db, especialidad_electronica):
        """Slot 4 resolves to Ingeniería Electrónica (Electrónica specialty)."""
        result = _resolve_slot_especialidad_revision(4)
        assert result is not None
        assert result.nombre == "Ingeniería Electrónica"
        # Verify the DB constant matches
        assert _SLOT_SPECIALTY_DB_MAP[4] == "Ingeniería Electrónica"

    def test_invalid_slot_returns_none(self, db):
        """Slot number outside 1..4 returns None."""
        assert _resolve_slot_especialidad_revision(0) is None
        assert _resolve_slot_especialidad_revision(5) is None
        assert _resolve_slot_especialidad_revision(99) is None

    def test_missing_especialidad_in_db_returns_none(self, db):
        """Slot resolves to None when the EspecialidadRevision is not in DB."""
        # No especialidad_electronica created — slot 4 should return None
        result = _resolve_slot_especialidad_revision(4)
        assert result is None


# ── Tests: _ensure_perfil_ingeniero_by_cip ─────────────────────────────────────

class TestEnsurePerfilIngenieroByCip:
    """Tests for PerfilIngeniero creation/reuse by normalized CIP."""

    def test_creates_new_perfil_from_cendpoint(self, db):
        """First call with a simulator CIP creates a new PerfilIngeniero hydrated from CIP."""
        # Use simulator CIP — endpoint returns valid identity data
        perfil, status = _ensure_perfil_ingeniero_by_cip("000001", dry_run=False)

        assert perfil is not None
        assert status == "CREADO_DESDE_CIP"
        assert perfil.cip == "000001"
        # Hydrated from simulator data: GUTIERREZ TORRES JORGE
        assert perfil.apellido_paterno == "GUTIERREZ"
        assert perfil.apellido_materno == "TORRES"
        assert perfil.dni == "12345678"
        assert perfil.correo_personal == "jorge.gutierrez@example.com"

    def test_reuses_existing_perfil_by_normalized_cip(self, db):
        """Second call with same CIP returns existing PerfilIngeniero without calling endpoint."""
        cip = "000002"
        perfil1, status1 = _ensure_perfil_ingeniero_by_cip(cip, dry_run=False)
        assert status1 == "CREADO_DESDE_CIP"

        perfil2, status2 = _ensure_perfil_ingeniero_by_cip(cip, dry_run=False)
        assert status2 == "YA_EXISTE"
        assert perfil2.id == perfil1.id

    def test_missing_cip_returns_sin_colegiado(self, db):
        """CIP not in simulator and not in DB returns SIN_COLEGIADO — no profile created."""
        # Non-simulator CIP, no local profile
        perfil, status = _ensure_perfil_ingeniero_by_cip("099999", dry_run=False)

        assert perfil is None
        assert status == "SIN_COLEGIADO"
        assert PerfilIngeniero.objects.filter(cip="099999").count() == 0

    def test_dry_run_does_not_create(self, db):
        """dry_run=True does not write to DB; reports what would happen."""
        cip = "099999"
        perfil, status = _ensure_perfil_ingeniero_by_cip(cip, dry_run=True)

        assert perfil is None
        assert status == "SIN_COLEGIADO"  # No endpoint data for this CIP

        # Verify nothing was written
        assert PerfilIngeniero.objects.filter(cip="099999").count() == 0

    def test_dry_run_returns_existing_without_writing(self, db):
        """dry_run=True returns existing record without writing."""
        cip = "000003"
        # Create first
        _ensure_perfil_ingeniero_by_cip(cip, dry_run=False)

        # Dry run sees it — no endpoint call made
        perfil, status = _ensure_perfil_ingeniero_by_cip(cip, dry_run=True)
        assert status == "YA_EXISTE"
        assert perfil is not None
        assert perfil.cip == "000003"

    def test_invalid_cip_returns_error(self, db):
        """Non-numeric CIP (empty after normalization) returns ERROR."""
        # Empty string normalizes to "" (all chars filtered) -> ERROR
        perfil, status = _ensure_perfil_ingeniero_by_cip("", dry_run=False)
        assert perfil is None
        assert status == "ERROR"

    def test_cero_cip_not_in_simulator_returns_sin_colegiado(self, db):
        """cip=0 normalizes to 000000 — not in simulator, no local profile -> SIN_COLEGIADO."""
        # 000000 is not in CipClientSimulator.SIMULATED_DATA
        perfil, status = _ensure_perfil_ingeniero_by_cip(0, dry_run=False)
        assert perfil is None
        assert status == "SIN_COLEGIADO"
        assert PerfilIngeniero.objects.filter(cip="000000").count() == 0


# ── Tests: _ensure_delegado_for_perfil ────────────────────────────────────────

class TestEnsureDelegadoForPerfil:
    """Tests for Delegado creation/reuse for a PerfilIngeniero."""

    def test_creates_new_delegado_for_perfil(self, db, especialidad_civil):
        """First call creates a new Delegado for the perfil."""
        # Use simulator CIP so perfil is created from CIP endpoint
        perfil, _ = _ensure_perfil_ingeniero_by_cip("000001", dry_run=False)
        assert perfil is not None  # sanity check: CIP hydration succeeded

        delegado, status = _ensure_delegado_for_perfil(perfil, dry_run=False)

        assert delegado is not None
        assert status == "CREADO"
        assert delegado.perfil_ingeniero_id == perfil.id

    def test_reuses_existing_delegado_by_perfil(self, db, especialidad_civil):
        """Second call with same perfil returns existing Delegado."""
        perfil, _ = _ensure_perfil_ingeniero_by_cip("000002", dry_run=False)

        del1, status1 = _ensure_delegado_for_perfil(perfil, dry_run=False)
        assert status1 == "CREADO"

        del2, status2 = _ensure_delegado_for_perfil(perfil, dry_run=False)
        assert status2 == "YA_EXISTE"
        assert del2.id == del1.id

    def test_dry_run_does_not_create_delegado(self, db, especialidad_civil):
        """dry_run=True does not write Delegado to DB."""
        perfil, _ = _ensure_perfil_ingeniero_by_cip("000003", dry_run=False)

        delegado, status = _ensure_delegado_for_perfil(perfil, dry_run=True)

        assert delegado is None
        assert status == "CREADO"
        assert Delegado.objects.filter(perfil_ingeniero=perfil).count() == 0

    def test_dry_run_returns_existing_delegado_without_writing(self, db, especialidad_civil):
        """dry_run=True returns existing Delegado without additional writes."""
        perfil, _ = _ensure_perfil_ingeniero_by_cip("000001", dry_run=False)
        _ensure_delegado_for_perfil(perfil, dry_run=False)

        # Now dry run
        delegado, status = _ensure_delegado_for_perfil(perfil, dry_run=True)
        assert status == "YA_EXISTE"
        assert delegado is not None

    def test_different_perfiles_get_different_delegados(self, db, especialidad_civil):
        """Two different PerfilIngeniero instances get two different Delegado records."""
        perfil1, _ = _ensure_perfil_ingeniero_by_cip("000001", dry_run=False)
        perfil2, _ = _ensure_perfil_ingeniero_by_cip("000002", dry_run=False)

        del1, _ = _ensure_delegado_for_perfil(perfil1, dry_run=False)
        del2, _ = _ensure_delegado_for_perfil(perfil2, dry_run=False)

        assert del1.id != del2.id
        assert del1.perfil_ingeniero_id != del2.perfil_ingeniero_id


# ── Tests: _ensure_delegado_operacion ─────────────────────────────────────────

class TestEnsureDelegadoOperacion:
    """Tests for DelegadoOperacion creation/reuse with conflict handling."""

    @pytest.fixture
    def perfil_delegado(self, db, especialidad_civil):
        """Create a PerfilIngeniero + Delegado for tests (using simulator CIP)."""
        perfil, _ = _ensure_perfil_ingeniero_by_cip("000001", dry_run=False)
        assert perfil is not None, "Simulator CIP 000001 should always hydrate successfully"
        delegado, _ = _ensure_delegado_for_perfil(perfil, dry_run=False)
        return perfil, delegado

    def test_creates_new_operacion(
        self, db, perfil_delegado, municipalidad, tipo_edificacion, especialidad_civil
    ):
        """First call creates a new DelegadoOperacion."""
        _, delegado = perfil_delegado

        operacion, status = _ensure_delegado_operacion(
            delegado=delegado,
            municipalidad=municipalidad,
            tipo_liquidacion=tipo_edificacion,
            especialidad_revision=especialidad_civil,
            dry_run=False,
        )

        assert operacion is not None
        assert status == "CREADO"
        assert operacion.delegado_id == delegado.id
        assert operacion.municipalidad_id == municipalidad.id
        assert operacion.tipo_liquidacion_id == tipo_edificacion.id
        assert operacion.especialidad_revision_id == especialidad_civil.id
        assert operacion.tipo == TipoDelegado.TITULAR  # default tipo

    def test_reuses_existing_operacion_same_specialty(
        self, db, perfil_delegado, municipalidad, tipo_edificacion, especialidad_civil
    ):
        """Second call with same params returns existing DelegadoOperacion."""
        _, delegado = perfil_delegado

        op1, status1 = _ensure_delegado_operacion(
            delegado=delegado,
            municipalidad=municipalidad,
            tipo_liquidacion=tipo_edificacion,
            especialidad_revision=especialidad_civil,
            dry_run=False,
        )
        assert status1 == "CREADO"

        op2, status2 = _ensure_delegado_operacion(
            delegado=delegado,
            municipalidad=municipalidad,
            tipo_liquidacion=tipo_edificacion,
            especialidad_revision=especialidad_civil,
            dry_run=False,
        )
        assert status2 == "YA_EXISTE"
        assert op2.id == op1.id

    def test_conflict_returns_existing_with_conflict_status(
        self, db, perfil_delegado, municipalidad, tipo_edificacion,
        especialidad_civil, especialidad_sanitaria
    ):
        """Same (delegado, municipalidad, tipo_liquidacion) but different specialty
        returns CONFLICTO and reuses existing record (does not overwrite)."""
        _, delegado = perfil_delegado

        # First: create with Civil
        op1, status1 = _ensure_delegado_operacion(
            delegado=delegado,
            municipalidad=municipalidad,
            tipo_liquidacion=tipo_edificacion,
            especialidad_revision=especialidad_civil,
            dry_run=False,
        )
        assert status1 == "CREADO"

        # Second: same delegate/municipalidad/tipo but different specialty
        op2, status2 = _ensure_delegado_operacion(
            delegado=delegado,
            municipalidad=municipalidad,
            tipo_liquidacion=tipo_edificacion,
            especialidad_revision=especialidad_sanitaria,
            dry_run=False,
        )

        assert status2 == "CONFLICTO"
        assert op2.id == op1.id  # returns existing
        # specialty is unchanged
        op1.refresh_from_db()
        assert op1.especialidad_revision_id == especialidad_civil.id

    def test_dry_run_does_not_create_operacion(
        self, db, perfil_delegado, municipalidad, tipo_edificacion, especialidad_civil
    ):
        """dry_run=True does not write DelegadoOperacion to DB."""
        _, delegado = perfil_delegado

        operacion, status = _ensure_delegado_operacion(
            delegado=delegado,
            municipalidad=municipalidad,
            tipo_liquidacion=tipo_edificacion,
            especialidad_revision=especialidad_civil,
            dry_run=True,
        )

        assert operacion is None
        assert status == "CREADO"
        assert DelegadoOperacion.objects.filter(
            delegado=delegado,
            municipalidad=municipalidad,
            tipo_liquidacion=tipo_edificacion,
        ).count() == 0

    def test_dry_run_reports_existing_with_ya_existe(
        self, db, perfil_delegado, municipalidad, tipo_edificacion, especialidad_civil
    ):
        """dry_run=True returns existing record as YA_EXISTE without writing."""
        _, delegado = perfil_delegado

        # Create first
        _ensure_delegado_operacion(
            delegado=delegado,
            municipalidad=municipalidad,
            tipo_liquidacion=tipo_edificacion,
            especialidad_revision=especialidad_civil,
            dry_run=False,
        )

        # Dry run sees it
        operacion, status = _ensure_delegado_operacion(
            delegado=delegado,
            municipalidad=municipalidad,
            tipo_liquidacion=tipo_edificacion,
            especialidad_revision=especialidad_civil,
            dry_run=True,
        )

        assert status == "YA_EXISTE"
        assert operacion is not None

    def test_dry_run_conflict_returns_existing_with_conflicto(
        self, db, perfil_delegado, municipalidad, tipo_edificacion,
        especialidad_civil, especialidad_sanitaria
    ):
        """dry_run=True on conflict returns existing with CONFLICTO status."""
        _, delegado = perfil_delegado

        # Create with Civil
        _ensure_delegado_operacion(
            delegado=delegado,
            municipalidad=municipalidad,
            tipo_liquidacion=tipo_edificacion,
            especialidad_revision=especialidad_civil,
            dry_run=False,
        )

        # Dry run with different specialty
        operacion, status = _ensure_delegado_operacion(
            delegado=delegado,
            municipalidad=municipalidad,
            tipo_liquidacion=tipo_edificacion,
            especialidad_revision=especialidad_sanitaria,
            dry_run=True,
        )

        assert status == "CONFLICTO"
        assert operacion is not None  # returns the existing one

    def test_no_delegado_operacion_periodo_created(
        self, db, perfil_delegado, municipalidad, tipo_edificacion, especialidad_civil
    ):
        """Creating a DelegadoOperacion does NOT create a DelegadoOperacionPeriodo."""
        _, delegado = perfil_delegado

        before_count = DelegadoOperacionPeriodo.objects.count()

        _ensure_delegado_operacion(
            delegado=delegado,
            municipalidad=municipalidad,
            tipo_liquidacion=tipo_edificacion,
            especialidad_revision=especialidad_civil,
            dry_run=False,
        )

        after_count = DelegadoOperacionPeriodo.objects.count()
        assert after_count == before_count  # No new period records

    def test_default_tipo_is_titular(
        self, db, perfil_delegado, municipalidad, tipo_edificacion, especialidad_civil
    ):
        """DelegadoOperacion is created with default tipo=TITULAR."""
        _, delegado = perfil_delegado

        operacion, _ = _ensure_delegado_operacion(
            delegado=delegado,
            municipalidad=municipalidad,
            tipo_liquidacion=tipo_edificacion,
            especialidad_revision=especialidad_civil,
            dry_run=False,
        )

        assert operacion.tipo == TipoDelegado.TITULAR

    def test_different_municipalidades_create_separate_operaciones(
        self, db, perfil_delegado, municipalidad, tipo_edificacion, especialidad_civil,
        ubigeo_departamento, ubigeo_provincia, ubigeo_distrito
    ):
        """Different municipalidad values create separate DelegadoOperacion records."""
        _, delegado = perfil_delegado

        # Create first with one municipalidad
        op1, status1 = _ensure_delegado_operacion(
            delegado=delegado,
            municipalidad=municipalidad,
            tipo_liquidacion=tipo_edificacion,
            especialidad_revision=especialidad_civil,
            dry_run=False,
        )
        assert status1 == "CREADO"

        # Second municipalidad
        from modules.entidades.domain.models.municipalidad import Municipalidad
        otra_municipalidad = Municipalidad.objects.create(
            codigo="M999",
            nombre="Otra Municipalidad",
            distrito=ubigeo_distrito,
        )

        op2, status2 = _ensure_delegado_operacion(
            delegado=delegado,
            municipalidad=otra_municipalidad,
            tipo_liquidacion=tipo_edificacion,
            especialidad_revision=especialidad_civil,
            dry_run=False,
        )

        assert status2 == "CREADO"
        assert op1.id != op2.id
        assert op1.municipalidad_id != op2.municipalidad_id


# ── Tests: _get_existing_delegado_operacion ─────────────────────────────────────

class TestGetExistingDelegadoOperacion:
    """Tests for the internal existing operation lookup helper."""

    def test_returns_none_when_no_existing(
        self, db, perfil_delegado, municipalidad, tipo_edificacion, especialidad_civil
    ):
        """Returns None when no matching DelegadoOperacion exists."""
        _, delegado = perfil_delegado

        result = _get_existing_delegado_operacion(
            delegado=delegado,
            municipalidad=municipalidad,
            tipo_liquidacion=tipo_edificacion,
        )

        assert result is None

    def test_returns_existing_when_found(
        self, db, perfil_delegado, municipalidad, tipo_edificacion, especialidad_civil
    ):
        """Returns the existing DelegadoOperacion when one exists."""
        _, delegado = perfil_delegado

        created, _ = _ensure_delegado_operacion(
            delegado=delegado,
            municipalidad=municipalidad,
            tipo_liquidacion=tipo_edificacion,
            especialidad_revision=especialidad_civil,
            dry_run=False,
        )

        result = _get_existing_delegado_operacion(
            delegado=delegado,
            municipalidad=municipalidad,
            tipo_liquidacion=tipo_edificacion,
        )

        assert result is not None
        assert result.id == created.id

    @pytest.fixture
    def perfil_delegado(self, db, especialidad_civil):
        perfil, _ = _ensure_perfil_ingeniero_by_cip("000002", dry_run=False)
        assert perfil is not None, "Simulator CIP 000002 should always hydrate successfully"
        delegado, _ = _ensure_delegado_for_perfil(perfil, dry_run=False)
        return perfil, delegado
