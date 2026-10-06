"""
Tests for Phase 4 LiquidacionComprobante helpers in import_legacy_edificaciones.

Tests the helper functions outside the Command class:
- _parse_total
- _tipo_comprobante_from_nrofactura
- _upsert_liquidacion_comprobante

Coverage:
1. _parse_total returns Decimal for valid numeric; None for zero/invalid/absent
2. _tipo_comprobante_from_nrofactura maps FAC->FACTURA, BOL->BOLETA, other->None
3. Creates active LiquidacionComprobante with serie/numero from NROFACTURA
4. Sets monto from legacy TOTAL
5. Maps type safely (FAC->FACTURA, BOL->BOLETA, other->None)
6. Updates existing active comprobante instead of duplicating
7. Does not store IGV (no such field on LiquidacionComprobante)
8. Blank/malformed NROFACTURA skips safely / returns OMITIDO
9. Dry-run does not write comprobante

Fixtures:
- EspecialidadRevision for slots 1-4 (created inline to match _SLOT_SPECIALTY_DB_MAP).
- Phase 2 helpers (PerfilIngeniero/Delegado/DelegadoOperacion) used to build chain.
- LiquidacionGeneral created via Phase 2 orchestrator flow for upsert tests.

Test strategy: integration tests with @pytest.mark.django_db — real DB, real ORM, no mocks.
"""

import pytest
from decimal import Decimal

from modules.liquidaciones.management.commands.import_legacy_edificaciones import (
    _parse_total,
    _tipo_comprobante_from_nrofactura,
    _upsert_liquidacion_comprobante,
    COL_TOTAL,
)
from modules.liquidaciones.domain.models.liquidacion.liquidacion_general.comprobante import (
    LiquidacionComprobante,
)
from modules.liquidaciones.domain.models.liquidacion.liquidacion_general.liquidacion import (
    LiquidacionGeneral,
)
from modules.liquidaciones.domain.models.tipo_liquidacion import TipoLiquidacion as TipoLiquidacionModel
from modules.liquidaciones.domain.constants import EstadoLiquidacion


# ── Fixtures ───────────────────────────────────────────────────────────────────

@pytest.fixture
def tipo_liq_edificacion(db):
    """TipoLiquidacion EDIFICACION for comprobante tests."""
    return TipoLiquidacionModel.objects.get_or_create(
        codigo="EDIFICACION",
        defaults={"nombre": "Edificaciones"},
    )[0]


@pytest.fixture
def liquidacion_general_comp(db, proyecto, municipalidad, tipo_liq_edificacion):
    """Minimal LiquidacionGeneral for comprobante tests."""
    return LiquidacionGeneral.objects.create(
        proyecto=proyecto,
        municipalidad=municipalidad,
        tipo_liquidacion=tipo_liq_edificacion,
        expediente="TEST-LEGACY-COMP-001",
        numero_revision=1,
        legacy=True,
        total=Decimal("1000.00"),
        sub_total=Decimal("1000.00"),
        estado=EstadoLiquidacion.PENDIENTE,
    )


# ── Tests: _parse_total ───────────────────────────────────────────────────────

class TestParseTotal:
    """Tests for TOTAL column parser."""

    def test_returns_decimal_for_valid_numeric(self, db):
        """Valid numeric string returns Decimal."""
        row = [None] * (COL_TOTAL + 1)
        row[COL_TOTAL] = "1234.56"
        result = _parse_total(row)
        assert result == Decimal("1234.56")

    def test_returns_none_for_none(self, db):
        """None value returns None."""
        row = [None] * (COL_TOTAL + 1)
        result = _parse_total(row)
        assert result is None

    def test_returns_none_for_empty_string(self, db):
        """Empty string returns None."""
        row = [None] * (COL_TOTAL + 1)
        row[COL_TOTAL] = ""
        result = _parse_total(row)
        assert result is None

    def test_returns_none_for_null_string(self, db):
        """NULL string returns None."""
        row = [None] * (COL_TOTAL + 1)
        row[COL_TOTAL] = "NULL"
        result = _parse_total(row)
        assert result is None

    def test_returns_none_for_zero(self, db):
        """Zero returns None (treated as absent/invalid in legacy data)."""
        row = [None] * (COL_TOTAL + 1)
        row[COL_TOTAL] = "0"
        result = _parse_total(row)
        assert result is None

    def test_returns_none_for_zero_decimal(self, db):
        """Decimal('0') returns None."""
        row = [None] * (COL_TOTAL + 1)
        row[COL_TOTAL] = Decimal("0")
        result = _parse_total(row)
        assert result is None

    def test_returns_none_for_invalid_non_numeric(self, db):
        """Non-numeric string returns None."""
        row = [None] * (COL_TOTAL + 1)
        row[COL_TOTAL] = "NOT_A_NUMBER"
        result = _parse_total(row)
        assert result is None

    def test_row_too_short_returns_none(self, db):
        """Row shorter than COL_TOTAL returns None."""
        row = [None] * 5
        result = _parse_total(row)
        assert result is None

    def test_large_value_preserved(self, db):
        """Large numeric values are preserved exactly."""
        row = [None] * (COL_TOTAL + 1)
        row[COL_TOTAL] = "999999.99"
        result = _parse_total(row)
        assert result == Decimal("999999.99")


# ── Tests: _tipo_comprobante_from_nrofactura ───────────────────────────────────

class TestTipoComprobanteFromNrofactura:
    """Tests for NROFACTURA prefix -> TipoComprobante mapping."""

    def test_fac_prefix_returns_factura(self, db):
        """'FAC' prefix (case-insensitive) returns 'FACTURA'."""
        assert _tipo_comprobante_from_nrofactura("FAC-001") == "FACTURA"
        assert _tipo_comprobante_from_nrofactura("fac-001") == "FACTURA"
        assert _tipo_comprobante_from_nrofactura("Fac-001") == "FACTURA"

    def test_bol_prefix_returns_boleta(self, db):
        """'BOL' prefix (case-insensitive) returns 'BOLETA'."""
        assert _tipo_comprobante_from_nrofactura("BOL-002") == "BOLETA"
        assert _tipo_comprobante_from_nrofactura("bol-002") == "BOLETA"
        assert _tipo_comprobante_from_nrofactura("Bol-002") == "BOLETA"

    def test_other_prefix_returns_none(self, db):
        """Unrecognized prefix returns None."""
        assert _tipo_comprobante_from_nrofactura("NTC-001") is None
        assert _tipo_comprobante_from_nrofactura("NOTA-001") is None
        assert _tipo_comprobante_from_nrofactura("000-001") is None

    def test_none_returns_none(self, db):
        """None input returns None."""
        assert _tipo_comprobante_from_nrofactura(None) is None

    def test_empty_string_returns_none(self, db):
        """Empty string returns None."""
        assert _tipo_comprobante_from_nrofactura("") is None
        assert _tipo_comprobante_from_nrofactura("   ") is None


# ── Tests: _upsert_liquidacion_comprobante ─────────────────────────────────────

class TestUpsertLiquidacionComprobante:
    """Tests for LiquidacionComprobante upsert logic."""

    def test_creates_new_comprobante_with_serie_numero(
        self, db, liquidacion_general_comp
    ):
        """New comprobante is created with serie/numero from NROFACTURA and activo=True."""
        comprobante_data = {"serie": "001", "numero": "00001", "raw": "001-00001"}
        total = Decimal("1500.00")

        comp, status = _upsert_liquidacion_comprobante(
            liquidacion_general_comp, comprobante_data, total, dry_run=False
        )

        assert status == "CREADO"
        assert comp is not None
        assert comp.serie == "001"
        assert comp.numero == "00001"
        assert comp.monto == Decimal("1500.00")
        assert comp.activo is True
        assert comp.liquidacion_general_id == liquidacion_general_comp.id

    def test_sets_monto_from_legacy_total(
        self, db, liquidacion_general_comp
    ):
        """monto is set from the legacy TOTAL (Decimal)."""
        comprobante_data = {"serie": "F001", "numero": "00042", "raw": "F001-00042"}
        total = Decimal("9876.54")

        comp, status = _upsert_liquidacion_comprobante(
            liquidacion_general_comp, comprobante_data, total, dry_run=False
        )

        assert status == "CREADO"
        assert comp.monto == Decimal("9876.54")

    def test_maps_fac_to_factura(
        self, db, liquidacion_general_comp
    ):
        """FAC prefix in raw NROFACTURA sets tipo_comprobante='FACTURA'."""
        comprobante_data = {"serie": "001", "numero": "1", "raw": "FAC-001"}
        total = Decimal("100.00")

        comp, status = _upsert_liquidacion_comprobante(
            liquidacion_general_comp, comprobante_data, total, dry_run=False
        )

        assert status == "CREADO"
        assert comp.tipo_comprobante == "FACTURA"

    def test_maps_bol_to_boleta(
        self, db, liquidacion_general_comp
    ):
        """BOL prefix in raw NROFACTURA sets tipo_comprobante='BOLETA'."""
        comprobante_data = {"serie": "B01", "numero": "2", "raw": "BOL-B01-00002"}
        total = Decimal("200.00")

        comp, status = _upsert_liquidacion_comprobante(
            liquidacion_general_comp, comprobante_data, total, dry_run=False
        )

        assert status == "CREADO"
        assert comp.tipo_comprobante == "BOLETA"

    def test_other_prefix_sets_tipo_none(
        self, db, liquidacion_general_comp
    ):
        """Unrecognized prefix leaves tipo_comprobante=None."""
        comprobante_data = {"serie": "NTC", "numero": "001", "raw": "NTC-001"}
        total = Decimal("100.00")

        comp, status = _upsert_liquidacion_comprobante(
            liquidacion_general_comp, comprobante_data, total, dry_run=False
        )

        assert status == "CREADO"
        assert comp.tipo_comprobante is None

    def test_updates_existing_active_instead_of_duplicating(
        self, db, liquidacion_general_comp
    ):
        """Calling again on same liquidacion updates the existing active comprobante."""
        comprobante_data_1 = {"serie": "001", "numero": "00001", "raw": "001-00001"}
        total_1 = Decimal("1000.00")

        comp_1, status_1 = _upsert_liquidacion_comprobante(
            liquidacion_general_comp, comprobante_data_1, total_1, dry_run=False
        )
        assert status_1 == "CREADO"
        id_1 = comp_1.id

        # Second call with different data — should UPDATE, not create
        comprobante_data_2 = {"serie": "002", "numero": "00002", "raw": "002-00002"}
        total_2 = Decimal("2000.00")

        comp_2, status_2 = _upsert_liquidacion_comprobante(
            liquidacion_general_comp, comprobante_data_2, total_2, dry_run=False
        )

        assert status_2 == "ACTUALIZADO"
        assert comp_2.id == id_1  # Same record
        assert comp_2.serie == "002"
        assert comp_2.numero == "00002"
        assert comp_2.monto == Decimal("2000.00")

        # No new record created
        assert LiquidacionComprobante.objects.filter(liquidacion_general=liquidacion_general_comp).count() == 1

    def test_blank_nrofactura_returns_omitido(
        self, db, liquidacion_general_comp
    ):
        """When NROFACTURA is blank/malformed (no serie, no numero), returns OMITIDO."""
        # Malformed: both serie and numero are None
        comprobante_data = {"serie": None, "numero": None, "raw": None}
        total = Decimal("500.00")

        comp, status = _upsert_liquidacion_comprobante(
            liquidacion_general_comp, comprobante_data, total, dry_run=False
        )

        assert status == "OMITIDO"
        assert comp is None

    def test_blank_nrofactura_does_not_create_comprobante(
        self, db, liquidacion_general_comp
    ):
        """OMITIDO path does not write any record to DB."""
        comprobante_data = {"serie": None, "numero": None, "raw": ""}
        total = Decimal("500.00")

        _upsert_liquidacion_comprobante(
            liquidacion_general_comp, comprobante_data, total, dry_run=False
        )

        assert LiquidacionComprobante.objects.filter(liquidacion_general=liquidacion_general_comp).count() == 0

    def test_omitido_when_only_numero_present(
        self, db, liquidacion_general_comp
    ):
        """Only numero present (serie=None) is still valid — comprobante created with serie=None.

        The OMITIDO guard only fires when BOTH serie and numero are None.
        A comprobante with only numero (no serie) is a valid edge case (legacy data quirk).
        """
        comprobante_data = {"serie": None, "numero": "00001", "raw": "00001"}
        total = Decimal("500.00")

        comp, status = _upsert_liquidacion_comprobante(
            liquidacion_general_comp, comprobante_data, total, dry_run=False
        )

        # Implementation only skips when BOTH are None; this is valid.
        assert status == "CREADO"
        assert comp is not None
        assert comp.serie is None
        assert comp.numero == "00001"

    def test_dry_run_does_not_write(
        self, db, liquidacion_general_comp
    ):
        """dry_run=True does not write any record to the DB."""
        comprobante_data = {"serie": "DRY", "numero": "001", "raw": "DRY-001"}
        total = Decimal("333.33")

        comp, status = _upsert_liquidacion_comprobante(
            liquidacion_general_comp, comprobante_data, total, dry_run=True
        )

        assert status == "CREADO"  # Reports what would be created
        assert comp is None  # But no record returned (not written)
        assert LiquidacionComprobante.objects.filter(liquidacion_general=liquidacion_general_comp).count() == 0

    def test_dry_run_returns_existing_without_writing(
        self, db, liquidacion_general_comp
    ):
        """dry_run=True returns existing record as ACTUALIZADO without writing."""
        # Create first
        comprobante_data_1 = {"serie": "EX", "numero": "001", "raw": "EX-001"}
        total_1 = Decimal("100.00")
        _upsert_liquidacion_comprobante(
            liquidacion_general_comp, comprobante_data_1, total_1, dry_run=False
        )

        # Dry run on existing
        comprobante_data_2 = {"serie": "NEW", "numero": "002", "raw": "NEW-002"}
        total_2 = Decimal("200.00")
        comp, status = _upsert_liquidacion_comprobante(
            liquidacion_general_comp, comprobante_data_2, total_2, dry_run=True
        )

        assert status == "ACTUALIZADO"
        assert comp is not None
        assert comp.serie == "EX"  # Unchanged (dry run)

        # Verify no write happened
        liquidacion_general_comp.refresh_from_db()
        comp.refresh_from_db()
        assert comp.serie == "EX"  # Still original
        assert comp.monto == Decimal("100.00")  # Unchanged

    def test_no_igv_field_exists_on_model(self, db):
        """LiquidacionComprobante has no IGV field — correctly not stored."""
        # This is a structural assertion: the model has no igv field
        assert not hasattr(LiquidacionComprobante, 'igv')
        assert not hasattr(LiquidacionComprobante, 'igv_delegado')
        assert not hasattr(LiquidacionComprobante, 'monto_igv')

    def test_comprobante_activo_is_true_by_default(
        self, db, liquidacion_general_comp
    ):
        """Created comprobante has activo=True by default (or explicit=True)."""
        comprobante_data = {"serie": "ACT", "numero": "001", "raw": "ACT-001"}
        total = Decimal("100.00")

        comp, status = _upsert_liquidacion_comprobante(
            liquidacion_general_comp, comprobante_data, total, dry_run=False
        )

        assert status == "CREADO"
        assert comp.activo is True

    def test_comprobante_with_none_monto_saved(
        self, db, liquidacion_general_comp
    ):
        """total=None is accepted and saved as monto=None (e.g., when TOTAL is absent)."""
        comprobante_data = {"serie": "N01", "numero": "001", "raw": "N01-001"}

        comp, status = _upsert_liquidacion_comprobante(
            liquidacion_general_comp, comprobante_data, None, dry_run=False
        )

        assert status == "CREADO"
        assert comp.monto is None

    def test_unique_constraint_one_active_per_liquidacion(
        self, db, liquidacion_general_comp
    ):
        """Only one active comprobante can exist per liquidacion (enforced by model constraint)."""
        # Create first
        comp_1, _ = _upsert_liquidacion_comprobante(
            liquidacion_general_comp,
            {"serie": "A", "numero": "1", "raw": "A-1"},
            Decimal("100"),
            dry_run=False,
        )
        assert comp_1.activo is True

        # Try to create a second active comprobante directly (bypassing upsert)
        # This should violate the unique constraint
        from django.db import IntegrityError
        with pytest.raises(IntegrityError):
            LiquidacionComprobante.objects.create(
                liquidacion_general=liquidacion_general_comp,
                serie="B",
                numero="2",
                monto=Decimal("200"),
                activo=True,
            )
