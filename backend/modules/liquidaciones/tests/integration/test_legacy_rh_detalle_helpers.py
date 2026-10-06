"""
Tests for Phase 3 RH Delegado helpers in import_legacy_edificaciones.

Tests the helper functions outside the Command class:
- _find_same_row_liquidacion
- _ensure_liquidacion_delegado
- _ensure_detalle_honorario_delegado

Coverage:
1. _find_same_row_liquidacion returns ENCONTRADO/NO_ENCONTRADO/AMBIGUO
2. _ensure_liquidacion_delegado creates LiquidacionDelegado for same-row LiquidacionGeneral
3. Persists row-driven periodo/mes when present for any slot (including slot 4)
4. Leaves periodo/mes=None when source values are absent/invalid — no inference
5. Creates DetalleHonorarioDelegado with fixed legacy monetary values and recibo_mensual=None
6. Does NOT create ReciboHonorarioDelegadoMensual
7. Idempotency: re-run creates no duplicate LiquidacionDelegado or DetalleHonorarioDelegado
8. Skips/reports when same-row LiquidacionGeneral is missing/ambiguous
9. Dry-run does not create LiquidacionDelegado or DetalleHonorarioDelegado

Fixtures:
- EspecialidadRevision for slots 1-4 (Ingeniería Civil/Sanitaria/Eléctrica y Mecánica
  Eléctrica/Electrónica) — created inline since these canonical names must match
  _SLOT_SPECIALTY_DB_MAP exactly.
- Phase 2 helpers (PerfilIngeniero/Delegado/DelegadoOperacion) used to build the chain.
- LiquidacionGeneral created via Phase 2 orchestrator flow for lookup tests.

Test strategy: integration tests with @pytest.mark.django_db — real DB, real ORM, no mocks.
"""

import pytest
from decimal import Decimal
from datetime import date

from modules.liquidaciones.management.commands.import_legacy_edificaciones import (
    _find_same_row_liquidacion,
    _ensure_liquidacion_delegado,
    _ensure_detalle_honorario_delegado,
)
from modules.liquidaciones.domain.models.delegado import (
    Delegado,
    DelegadoOperacion,
    LiquidacionDelegado,
)
from modules.finanzas.domain.models.detalle_honorario_delegado import (
    DetalleHonorarioDelegado,
)
from modules.finanzas.domain.models.recibo_honorario_delegado_mensual import (
    ReciboHonorarioDelegadoMensual,
)
from modules.usuarios.domain.models.perfil_ingeniero import (
    EspecialidadRevision,
)
from modules.liquidaciones.domain.models.liquidacion.liquidacion_general.liquidacion import (
    LiquidacionGeneral,
)
from modules.liquidaciones.domain.models.tipo_liquidacion import TipoLiquidacion as TipoLiquidacionModel
from modules.liquidaciones.domain.constants import TipoLiquidacion, EstadoLiquidacion


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


@pytest.fixture
def tipo_liq_edificacion(db):
    """TipoLiquidacion model for EDIFICACION."""
    return TipoLiquidacionModel.objects.get_or_create(
        codigo=TipoLiquidacion.EDIFICACION,
        defaults={"nombre": "Edificaciones"},
    )[0]


# ── Helpers to build test chain ────────────────────────────────────────────────

def _build_perfil_delegado_operacion(cip, municipalidad, tipo_liquidacion, especialidad_revision):
    """Build PerfilIngeniero + Delegado + DelegadoOperacion chain via Phase 2 helpers.

    Note: cip should be a simulator CIP (e.g., '000001', '000002', '000003') so that
    _ensure_perfil_ingeniero_by_cip can hydrate a real PerfilIngeniero from the CIP endpoint.
    """
    from modules.liquidaciones.management.commands.import_legacy_edificaciones import (
        _ensure_perfil_ingeniero_by_cip,
        _ensure_delegado_for_perfil,
        _ensure_delegado_operacion,
    )
    perfil, status = _ensure_perfil_ingeniero_by_cip(cip, dry_run=False)
    assert perfil is not None, (
        f"cip={cip!r} should hydrate from CIP endpoint (status={status}). "
        "Use simulator CIPs: '000001', '000002', '000003'"
    )
    assert status in ("CREADO_DESDE_CIP", "ACTUALIZADO_DESDE_CIP", "YA_EXISTE"), (
        f"Unexpected status {status} for simulator CIP {cip}"
    )
    delegado, _ = _ensure_delegado_for_perfil(perfil, dry_run=False)
    operacion, _ = _ensure_delegado_operacion(
        delegado=delegado,
        municipalidad=municipalidad,
        tipo_liquidacion=tipo_liquidacion,
        especialidad_revision=especialidad_revision,
        dry_run=False,
    )
    return perfil, delegado, operacion


# ── Tests: _find_same_row_liquidacion ─────────────────────────────────────────

class TestFindSameRowLiquidacion:
    """Tests for finding the LiquidacionGeneral created from the same legacy row."""

    @pytest.fixture
    def liquidacion_row(
        self, db, proyecto, municipalidad, tipo_liq_edificacion
    ):
        """Create a LiquidacionGeneral with legacy=True for lookup tests."""
        return LiquidacionGeneral.objects.create(
            proyecto=proyecto,
            municipalidad=municipalidad,
            tipo_liquidacion=tipo_liq_edificacion,
            expediente="EXP-2024-001",
            numero_revision=1,
            legacy=True,
            total=Decimal("1000.00"),
            sub_total=Decimal("1000.00"),
            estado=EstadoLiquidacion.PENDIENTE,
        )

    def test_returns_no_encontrado_when_no_match(
        self, db, municipalidad
    ):
        """Returns NO_ENCONTRADO when no LiquidacionGeneral matches."""
        liq, status = _find_same_row_liquidacion(
            expediente="NOEXISTE-EXP",
            numero_revision=1,
            municipalidad=municipalidad,
        )
        assert liq is None
        assert status == "NO_ENCONTRADO"

    def test_returns_no_encontrado_when_expediente_is_none(
        self, db, municipalidad
    ):
        """Returns NO_ENCONTRADO when expediente is None."""
        liq, status = _find_same_row_liquidacion(
            expediente=None,
            numero_revision=1,
            municipalidad=municipalidad,
        )
        assert liq is None
        assert status == "NO_ENCONTRADO"

    def test_returns_encontrado_when_exactly_one_match(
        self, db, liquidacion_row, municipalidad
    ):
        """Returns ENCONTRADO when exactly one LiquidacionGeneral matches."""
        liq, status = _find_same_row_liquidacion(
            expediente="EXP-2024-001",
            numero_revision=1,
            municipalidad=municipalidad,
        )
        assert liq is not None
        assert status == "ENCONTRADO"
        assert liq.id == liquidacion_row.id

    def test_returns_ambiguo_when_multiple_matches(
        self, db, proyecto, municipalidad, tipo_liq_edificacion
    ):
        """Returns AMBIGUO when more than one LiquidacionGeneral matches."""
        # Create first LiquidacionGeneral
        LiquidacionGeneral.objects.create(
            proyecto=proyecto,
            municipalidad=municipalidad,
            tipo_liquidacion=tipo_liq_edificacion,
            expediente="EXP-DUP",
            numero_revision=1,
            legacy=True,
            total=Decimal("1000.00"),
            sub_total=Decimal("1000.00"),
            estado=EstadoLiquidacion.PENDIENTE,
        )
        # Create a second Proyecto for the second LiquidacionGeneral
        from modules.entidades.domain.models import Entidad
        entidad2 = Entidad.objects.create(
            tipo_documento="RUC",
            numero_documento="20456789013",
        )
        from modules.liquidaciones.domain.models.proyecto import Proyecto
        proyecto2 = Proyecto.objects.create(
            entidad=entidad2,
            nombre_propietario="Propietario 2",
            direccion="Dirección 2",
            distrito=proyecto.distrito,
            entidad_tipo_documento="RUC",
            entidad_numero_documento="20456789013",
            entidad_razon_social="Propietario 2 SAC",
        )
        LiquidacionGeneral.objects.create(
            proyecto=proyecto2,
            municipalidad=municipalidad,
            tipo_liquidacion=tipo_liq_edificacion,
            expediente="EXP-DUP",
            numero_revision=1,
            legacy=True,
            total=Decimal("2000.00"),
            sub_total=Decimal("2000.00"),
            estado=EstadoLiquidacion.PENDIENTE,
        )

        liq, status = _find_same_row_liquidacion(
            expediente="EXP-DUP",
            numero_revision=1,
            municipalidad=municipalidad,
        )
        assert liq is None
        assert status == "AMBIGUO"

    def test_requires_legacy_flag(
        self, db, liquidacion_row, municipalidad, tipo_liq_edificacion
    ):
        """Only finds LiquidacionGeneral with legacy=True."""
        # Create non-legacy record with same expediente/revision
        from modules.entidades.domain.models import Entidad
        entidad_nl = Entidad.objects.create(
            tipo_documento="RUC",
            numero_documento="20456789014",
        )
        from modules.liquidaciones.domain.models.proyecto import Proyecto
        proyecto_nl = Proyecto.objects.create(
            entidad=entidad_nl,
            nombre_propietario="Propietario NL",
            direccion="Dirección NL",
            distrito=liquidacion_row.proyecto.distrito,
            entidad_tipo_documento="RUC",
            entidad_numero_documento="20456789014",
            entidad_razon_social="Propietario NL SAC",
        )
        LiquidacionGeneral.objects.create(
            proyecto=proyecto_nl,
            municipalidad=municipalidad,
            tipo_liquidacion=tipo_liq_edificacion,
            expediente="EXP-2024-001",
            numero_revision=1,
            legacy=False,  # Not legacy
            total=Decimal("2000.00"),
            sub_total=Decimal("2000.00"),
            estado=EstadoLiquidacion.PENDIENTE,
        )

        # Should find the legacy one
        liq, status = _find_same_row_liquidacion(
            expediente="EXP-2024-001",
            numero_revision=1,
            municipalidad=municipalidad,
        )
        assert liq is not None
        assert liq.id == liquidacion_row.id
        assert liq.legacy is True


# ── Tests: _ensure_liquidacion_delegado ───────────────────────────────────────

class TestEnsureLiquidacionDelegado:
    """Tests for LiquidacionDelegado creation/reuse with slot data."""

    @pytest.fixture
    def perfil_delegado_op(
        self, db, especialidad_civil, municipalidad, tipo_liq_edificacion
    ):
        """Build PerfilIngeniero + Delegado + DelegadoOperacion chain."""
        _, delegado, operacion = _build_perfil_delegado_operacion(
            cip="000001",
            municipalidad=municipalidad,
            tipo_liquidacion=tipo_liq_edificacion,
            especialidad_revision=especialidad_civil,
        )
        return delegado, operacion

    @pytest.fixture
    def liquidacion_row(
        self, db, proyecto, municipalidad, tipo_liq_edificacion
    ):
        """Create a LiquidacionGeneral with legacy=True."""
        return LiquidacionGeneral.objects.create(
            proyecto=proyecto,
            municipalidad=municipalidad,
            tipo_liquidacion=tipo_liq_edificacion,
            expediente="EXP-LD-001",
            numero_revision=1,
            legacy=True,
            total=Decimal("5000.00"),
            sub_total=Decimal("5000.00"),
            estado=EstadoLiquidacion.PENDIENTE,
        )

    def test_creates_new_liquidacion_delegado(
        self,
        db,
        perfil_delegado_op,
        liquidacion_row,
        especialidad_civil,
    ):
        """First call creates a new LiquidacionDelegado."""
        delegado, operacion = perfil_delegado_op

        slot_data = {
            "periodo": 2024,
            "mes": 6,
            "fecha_presentacion": date(2024, 5, 15),
            "fecha_revision": date(2024, 6, 1),
            "nro_rh": 100,
            "dictamen": "APROBADO",
        }

        ld, status = _ensure_liquidacion_delegado(
            liquidacion=liquidacion_row,
            delegado=delegado,
            especialidad_revision=especialidad_civil,
            delegado_operacion=operacion,
            slot_data=slot_data,
            dry_run=False,
        )

        assert ld is not None
        assert status == "CREADO"
        assert ld.liquidacion_id == liquidacion_row.id
        assert ld.delegado_id == delegado.id
        assert ld.especialidad_revision_id == especialidad_civil.id
        assert ld.delegado_operacion_id == operacion.id
        assert ld.periodo == 2024
        assert ld.mes == 6

    def test_reuses_existing_liquidacion_delegado(
        self,
        db,
        perfil_delegado_op,
        liquidacion_row,
        especialidad_civil,
    ):
        """Second call with same params returns existing LiquidacionDelegado."""
        delegado, operacion = perfil_delegado_op

        slot_data = {
            "periodo": 2024,
            "mes": 6,
            "fecha_presentacion": date(2024, 5, 15),
            "fecha_revision": date(2024, 6, 1),
            "nro_rh": 100,
            "dictamen": "APROBADO",
        }

        ld1, status1 = _ensure_liquidacion_delegado(
            liquidacion=liquidacion_row,
            delegado=delegado,
            especialidad_revision=especialidad_civil,
            delegado_operacion=operacion,
            slot_data=slot_data,
            dry_run=False,
        )
        assert status1 == "CREADO"

        ld2, status2 = _ensure_liquidacion_delegado(
            liquidacion=liquidacion_row,
            delegado=delegado,
            especialidad_revision=especialidad_civil,
            delegado_operacion=operacion,
            slot_data=slot_data,
            dry_run=False,
        )
        assert status2 == "YA_EXISTE"
        assert ld2.id == ld1.id

    def test_persists_periodo_and_mes_from_slot_data(
        self,
        db,
        perfil_delegado_op,
        liquidacion_row,
        especialidad_civil,
    ):
        """LiquidacionDelegado stores periodo and mes from slot_data."""
        delegado, operacion = perfil_delegado_op

        slot_data = {
            "periodo": 2023,
            "mes": 12,
            "fecha_presentacion": None,
            "fecha_revision": None,
            "nro_rh": 50,
            "dictamen": None,
        }

        ld, status = _ensure_liquidacion_delegado(
            liquidacion=liquidacion_row,
            delegado=delegado,
            especialidad_revision=especialidad_civil,
            delegado_operacion=operacion,
            slot_data=slot_data,
            dry_run=False,
        )

        assert ld.periodo == 2023
        assert ld.mes == 12

    def test_persists_periodo_mes_for_slot_4_electronica(
        self,
        db,
        proyecto,
        municipalidad,
        tipo_liq_edificacion,
        especialidad_electronica,
    ):
        """Slot 4 (Electrónica) periodo/mes are persisted correctly."""
        _, delegado, operacion = _build_perfil_delegado_operacion(
            cip="000002",
            municipalidad=municipalidad,
            tipo_liquidacion=tipo_liq_edificacion,
            especialidad_revision=especialidad_electronica,
        )

        liq = LiquidacionGeneral.objects.create(
            proyecto=proyecto,
            municipalidad=municipalidad,
            tipo_liquidacion=tipo_liq_edificacion,
            expediente="EXP-E4-001",
            numero_revision=1,
            legacy=True,
            total=Decimal("3000.00"),
            sub_total=Decimal("3000.00"),
            estado=EstadoLiquidacion.PENDIENTE,
        )

        slot_data = {
            "periodo": 2024,
            "mes": 3,
            "fecha_presentacion": date(2024, 3, 1),
            "fecha_revision": date(2024, 3, 15),
            "nro_rh": 300,
            "dictamen": "OBSERVADO",
        }

        ld, status = _ensure_liquidacion_delegado(
            liquidacion=liq,
            delegado=delegado,
            especialidad_revision=especialidad_electronica,
            delegado_operacion=operacion,
            slot_data=slot_data,
            dry_run=False,
        )

        assert status == "CREADO"
        assert ld.especialidad_revision_id == especialidad_electronica.id
        assert ld.periodo == 2024
        assert ld.mes == 3

    def test_leaves_periodo_mes_none_when_absent(
        self,
        db,
        perfil_delegado_op,
        liquidacion_row,
        especialidad_civil,
    ):
        """periodo/mes are None when source slot values are absent/invalid."""
        delegado, operacion = perfil_delegado_op

        slot_data = {
            "periodo": None,
            "mes": None,
            "fecha_presentacion": None,
            "fecha_revision": None,
            "nro_rh": None,
            "dictamen": None,
        }

        ld, status = _ensure_liquidacion_delegado(
            liquidacion=liquidacion_row,
            delegado=delegado,
            especialidad_revision=especialidad_civil,
            delegado_operacion=operacion,
            slot_data=slot_data,
            dry_run=False,
        )

        assert ld.periodo is None
        assert ld.mes is None

    def test_dry_run_does_not_create(
        self,
        db,
        perfil_delegado_op,
        liquidacion_row,
        especialidad_civil,
    ):
        """dry_run=True does not write LiquidacionDelegado to DB."""
        delegado, operacion = perfil_delegado_op

        slot_data = {
            "periodo": 2024,
            "mes": 7,
            "fecha_presentacion": date(2024, 6, 1),
            "fecha_revision": date(2024, 6, 15),
            "nro_rh": 200,
            "dictamen": "APROBADO",
        }

        ld, status = _ensure_liquidacion_delegado(
            liquidacion=liquidacion_row,
            delegado=delegado,
            especialidad_revision=especialidad_civil,
            delegado_operacion=operacion,
            slot_data=slot_data,
            dry_run=True,
        )

        assert ld is None
        assert status == "CREADO"
        assert LiquidacionDelegado.objects.filter(
            liquidacion=liquidacion_row,
            delegado=delegado,
            especialidad_revision=especialidad_civil,
        ).count() == 0

    def test_dry_run_returns_existing_without_writing(
        self,
        db,
        perfil_delegado_op,
        liquidacion_row,
        especialidad_civil,
    ):
        """dry_run=True returns existing LiquidacionDelegado without writing."""
        delegado, operacion = perfil_delegado_op

        slot_data = {
            "periodo": 2024,
            "mes": 8,
            "fecha_presentacion": date(2024, 7, 1),
            "fecha_revision": date(2024, 7, 15),
            "nro_rh": 300,
            "dictamen": "APROBADO",
        }

        # Create first
        _ensure_liquidacion_delegado(
            liquidacion=liquidacion_row,
            delegado=delegado,
            especialidad_revision=especialidad_civil,
            delegado_operacion=operacion,
            slot_data=slot_data,
            dry_run=False,
        )

        # Dry run sees it
        ld, status = _ensure_liquidacion_delegado(
            liquidacion=liquidacion_row,
            delegado=delegado,
            especialidad_revision=especialidad_civil,
            delegado_operacion=operacion,
            slot_data=slot_data,
            dry_run=True,
        )

        assert status == "YA_EXISTE"
        assert ld is not None


# ── Tests: _ensure_detalle_honorario_delegado ──────────────────────────────────

class TestEnsureDetalleHonorarioDelegado:
    """Tests for DetalleHonorarioDelegado creation/reuse with legacy monetary values."""

    @pytest.fixture
    def perfil_delegado_op(
        self, db, especialidad_civil, municipalidad, tipo_liq_edificacion
    ):
        """Build PerfilIngeniero + Delegado + DelegadoOperacion chain."""
        _, delegado, operacion = _build_perfil_delegado_operacion(
            cip="000001",
            municipalidad=municipalidad,
            tipo_liquidacion=tipo_liq_edificacion,
            especialidad_revision=especialidad_civil,
        )
        return delegado, operacion

    @pytest.fixture
    def liquidacion_delegado_row(
        self,
        db,
        perfil_delegado_op,
        proyecto,
        municipalidad,
        tipo_liq_edificacion,
        especialidad_civil,
    ):
        """Create a LiquidacionDelegado for detail tests."""
        _, operacion = perfil_delegado_op

        liq = LiquidacionGeneral.objects.create(
            proyecto=proyecto,
            municipalidad=municipalidad,
            tipo_liquidacion=tipo_liq_edificacion,
            expediente="EXP-DH-001",
            numero_revision=1,
            legacy=True,
            total=Decimal("5000.00"),
            sub_total=Decimal("5000.00"),
            estado=EstadoLiquidacion.PENDIENTE,
        )

        ld, _ = _ensure_liquidacion_delegado(
            liquidacion=liq,
            delegado=perfil_delegado_op[0],
            especialidad_revision=especialidad_civil,
            delegado_operacion=operacion,
            slot_data={"periodo": 2024, "mes": 6, "nro_rh": 100, "dictamen": "APROBADO"},
            dry_run=False,
        )
        return ld

    def test_creates_detalle_with_recibo_mensual_none(
        self,
        db,
        liquidacion_delegado_row,
    ):
        """DetalleHonorarioDelegado is created with recibo_mensual=None (legacy)."""
        monetary = {
            "imp_bruto": Decimal("1000.00"),
            "subtotal": Decimal("1000.00"),
            "renta_cip": Decimal("100.00"),
            "aporte_codemu": Decimal("50.00"),
            "fondo_comun": Decimal("25.00"),
            "neto_honorario": Decimal("825.00"),
        }

        detalle, status = _ensure_detalle_honorario_delegado(
            liquidacion_delegado=liquidacion_delegado_row,
            monetary=monetary,
            dry_run=False,
        )

        assert detalle is not None
        assert status == "CREADO"
        assert detalle.recibo_mensual is None

    def test_creates_detalle_with_fixed_legacy_monetary_values(
        self,
        db,
        liquidacion_delegado_row,
    ):
        """DetalleHonorarioDelegado stores the exact legacy monetary values."""
        monetary = {
            "imp_bruto": Decimal("1500.50"),
            "subtotal": Decimal("1500.50"),
            "renta_cip": Decimal("150.05"),
            "aporte_codemu": Decimal("75.00"),
            "fondo_comun": Decimal("37.50"),
            "neto_honorario": Decimal("1237.95"),
        }

        detalle, status = _ensure_detalle_honorario_delegado(
            liquidacion_delegado=liquidacion_delegado_row,
            monetary=monetary,
            dry_run=False,
        )

        assert detalle.imp_bruto == Decimal("1500.50")
        assert detalle.sub_total == Decimal("1500.50")
        assert detalle.renta_cip == Decimal("150.05")
        assert detalle.aporte_codemu == Decimal("75.00")
        assert detalle.fondo_comun == Decimal("37.50")
        assert detalle.neto_honorario == Decimal("1237.95")
        assert detalle.tasa_delegado is None

    def test_idempotency_no_duplicate_detalle(
        self,
        db,
        liquidacion_delegado_row,
    ):
        """Re-running does not create duplicate DetalleHonorarioDelegado."""
        monetary = {
            "imp_bruto": Decimal("2000.00"),
            "subtotal": Decimal("2000.00"),
            "renta_cip": Decimal("200.00"),
            "aporte_codemu": Decimal("100.00"),
            "fondo_comun": Decimal("50.00"),
            "neto_honorario": Decimal("1650.00"),
        }

        detalle1, status1 = _ensure_detalle_honorario_delegado(
            liquidacion_delegado=liquidacion_delegado_row,
            monetary=monetary,
            dry_run=False,
        )
        assert status1 == "CREADO"

        detalle2, status2 = _ensure_detalle_honorario_delegado(
            liquidacion_delegado=liquidacion_delegado_row,
            monetary=monetary,
            dry_run=False,
        )
        assert status2 == "YA_EXISTE"
        assert detalle2.id == detalle1.id

        # Only one detail exists for this LD
        assert DetalleHonorarioDelegado.objects.filter(
            liquidacion_delegado=liquidacion_delegado_row
        ).count() == 1

    def test_dry_run_does_not_create_detalle(
        self,
        db,
        liquidacion_delegado_row,
    ):
        """dry_run=True does not write DetalleHonorarioDelegado to DB."""
        monetary = {
            "imp_bruto": Decimal("3000.00"),
            "subtotal": Decimal("3000.00"),
            "renta_cip": Decimal("300.00"),
            "aporte_codemu": Decimal("150.00"),
            "fondo_comun": Decimal("75.00"),
            "neto_honorario": Decimal("2475.00"),
        }

        detalle, status = _ensure_detalle_honorario_delegado(
            liquidacion_delegado=liquidacion_delegado_row,
            monetary=monetary,
            dry_run=True,
        )

        assert detalle is None
        assert status == "CREADO"
        assert DetalleHonorarioDelegado.objects.filter(
            liquidacion_delegado=liquidacion_delegado_row
        ).count() == 0

    def test_dry_run_returns_existing_without_writing(
        self,
        db,
        liquidacion_delegado_row,
    ):
        """dry_run=True returns existing DetalleHonorarioDelegado without writing."""
        monetary = {
            "imp_bruto": Decimal("4000.00"),
            "subtotal": Decimal("4000.00"),
            "renta_cip": Decimal("400.00"),
            "aporte_codemu": Decimal("200.00"),
            "fondo_comun": Decimal("100.00"),
            "neto_honorario": Decimal("3300.00"),
        }

        # Create first
        _ensure_detalle_honorario_delegado(
            liquidacion_delegado=liquidacion_delegado_row,
            monetary=monetary,
            dry_run=False,
        )

        # Dry run sees it
        detalle, status = _ensure_detalle_honorario_delegado(
            liquidacion_delegado=liquidacion_delegado_row,
            monetary=monetary,
            dry_run=True,
        )

        assert status == "YA_EXISTE"
        assert detalle is not None


# ── Tests: No ReciboHonorarioDelegadoMensual creation ──────────────────────────

class TestNoReciboHonorarioDelegadoMensualCreated:
    """Verifies that legacy import does NOT create ReciboHonorarioDelegadoMensual records."""

    @pytest.fixture
    def perfil_delegado_op(
        self, db, especialidad_civil, municipalidad, tipo_liq_edificacion
    ):
        """Build PerfilIngeniero + Delegado + DelegadoOperacion chain."""
        _, delegado, operacion = _build_perfil_delegado_operacion(
            cip="000003",
            municipalidad=municipalidad,
            tipo_liquidacion=tipo_liq_edificacion,
            especialidad_revision=especialidad_civil,
        )
        return delegado, operacion

    @pytest.fixture
    def liquidacion_delegado_full(
        self,
        db,
        perfil_delegado_op,
        proyecto,
        municipalidad,
        tipo_liq_edificacion,
        especialidad_civil,
    ):
        """Create LiquidacionDelegado for testing."""
        _, operacion = perfil_delegado_op

        liq = LiquidacionGeneral.objects.create(
            proyecto=proyecto,
            municipalidad=municipalidad,
            tipo_liquidacion=tipo_liq_edificacion,
            expediente="EXP-RHMM-001",
            numero_revision=1,
            legacy=True,
            total=Decimal("5000.00"),
            sub_total=Decimal("5000.00"),
            estado=EstadoLiquidacion.PENDIENTE,
        )

        ld, _ = _ensure_liquidacion_delegado(
            liquidacion=liq,
            delegado=perfil_delegado_op[0],
            especialidad_revision=especialidad_civil,
            delegado_operacion=operacion,
            slot_data={"periodo": 2024, "mes": 6, "nro_rh": 100, "dictamen": "APROBADO"},
            dry_run=False,
        )
        return ld

    def test_no_recibo_honorario_delegado_mensual_created(
        self,
        db,
        liquidacion_delegado_full,
    ):
        """Creating LiquidacionDelegado and DetalleHonorarioDelegado does NOT
        create any ReciboHonorarioDelegadoMensual records."""
        before_count = ReciboHonorarioDelegadoMensual.objects.count()

        monetary = {
            "imp_bruto": Decimal("5000.00"),
            "subtotal": Decimal("5000.00"),
            "renta_cip": Decimal("500.00"),
            "aporte_codemu": Decimal("250.00"),
            "fondo_comun": Decimal("125.00"),
            "neto_honorario": Decimal("4125.00"),
        }

        _ensure_detalle_honorario_delegado(
            liquidacion_delegado=liquidacion_delegado_full,
            monetary=monetary,
            dry_run=False,
        )

        after_count = ReciboHonorarioDelegadoMensual.objects.count()
        assert after_count == before_count


# ── Tests: Idempotency across both helpers ─────────────────────────────────────

class TestIdempotencyAcrossBothHelpers:
    """Verifies that re-running the full Phase 3 chain produces no duplicates."""

    @pytest.fixture
    def perfil_delegado_op(
        self, db, especialidad_sanitaria, municipalidad, tipo_liq_edificacion
    ):
        """Build PerfilIngeniero + Delegado + DelegadoOperacion chain for slot 2."""
        _, delegado, operacion = _build_perfil_delegado_operacion(
            cip="000002",
            municipalidad=municipalidad,
            tipo_liquidacion=tipo_liq_edificacion,
            especialidad_revision=especialidad_sanitaria,
        )
        return delegado, operacion

    @pytest.fixture
    def liquidacion_row_idem(
        self, db, proyecto, municipalidad, tipo_liq_edificacion
    ):
        """Create a LiquidacionGeneral with legacy=True."""
        return LiquidacionGeneral.objects.create(
            proyecto=proyecto,
            municipalidad=municipalidad,
            tipo_liquidacion=tipo_liq_edificacion,
            expediente="EXP-IDEM-001",
            numero_revision=1,
            legacy=True,
            total=Decimal("8000.00"),
            sub_total=Decimal("8000.00"),
            estado=EstadoLiquidacion.PENDIENTE,
        )

    def test_no_duplicate_liquidacion_delegado_on_rerun(
        self,
        db,
        perfil_delegado_op,
        liquidacion_row_idem,
        especialidad_sanitaria,
    ):
        """Second run of _ensure_liquidacion_delegado reuses existing — no duplicate."""
        delegado, operacion = perfil_delegado_op

        slot_data = {
            "periodo": 2024,
            "mes": 5,
            "fecha_presentacion": date(2024, 4, 1),
            "fecha_revision": date(2024, 4, 15),
            "nro_rh": 500,
            "dictamen": "APROBADO",
        }

        # First run
        _ensure_liquidacion_delegado(
            liquidacion=liquidacion_row_idem,
            delegado=delegado,
            especialidad_revision=especialidad_sanitaria,
            delegado_operacion=operacion,
            slot_data=slot_data,
            dry_run=False,
        )

        # Second run
        _ensure_liquidacion_delegado(
            liquidacion=liquidacion_row_idem,
            delegado=delegado,
            especialidad_revision=especialidad_sanitaria,
            delegado_operacion=operacion,
            slot_data=slot_data,
            dry_run=False,
        )

        # Only one LiquidacionDelegado
        assert LiquidacionDelegado.objects.filter(
            liquidacion=liquidacion_row_idem,
            delegado=delegado,
            especialidad_revision=especialidad_sanitaria,
        ).count() == 1

    def test_no_duplicate_detalle_on_rerun(
        self,
        db,
        perfil_delegado_op,
        liquidacion_row_idem,
        especialidad_sanitaria,
    ):
        """Second run of _ensure_detalle_honorario_delegado reuses existing — no duplicate."""
        _, operacion = perfil_delegado_op

        slot_data = {
            "periodo": 2024,
            "mes": 5,
            "fecha_presentacion": date(2024, 4, 1),
            "fecha_revision": date(2024, 4, 15),
            "nro_rh": 500,
            "dictamen": "APROBADO",
        }

        monetary = {
            "imp_bruto": Decimal("8000.00"),
            "subtotal": Decimal("8000.00"),
            "renta_cip": Decimal("800.00"),
            "aporte_codemu": Decimal("400.00"),
            "fondo_comun": Decimal("200.00"),
            "neto_honorario": Decimal("6600.00"),
        }

        # First run — creates LD + DH
        ld, _ = _ensure_liquidacion_delegado(
            liquidacion=liquidacion_row_idem,
            delegado=perfil_delegado_op[0],
            especialidad_revision=especialidad_sanitaria,
            delegado_operacion=operacion,
            slot_data=slot_data,
            dry_run=False,
        )
        _ensure_detalle_honorario_delegado(
            liquidacion_delegado=ld,
            monetary=monetary,
            dry_run=False,
        )

        # Second run — reuses LD + DH
        ld2, _ = _ensure_liquidacion_delegado(
            liquidacion=liquidacion_row_idem,
            delegado=perfil_delegado_op[0],
            especialidad_revision=especialidad_sanitaria,
            delegado_operacion=operacion,
            slot_data=slot_data,
            dry_run=False,
        )
        _ensure_detalle_honorario_delegado(
            liquidacion_delegado=ld2,
            monetary=monetary,
            dry_run=False,
        )

        # Only one of each
        assert LiquidacionDelegado.objects.filter(
            liquidacion=liquidacion_row_idem,
            delegado=perfil_delegado_op[0],
            especialidad_revision=especialidad_sanitaria,
        ).count() == 1
        assert DetalleHonorarioDelegado.objects.filter(
            liquidacion_delegado=ld
        ).count() == 1
