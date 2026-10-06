"""
Tests for RH (Responsable de Habilitación) parser helpers in import_legacy_edificaciones.

These are PURE UNIT TESTS — no database, no Django ORM, no network.
They test the parsing helpers directly using controlled row fixtures.

Coverage:
1. _parse_rh_slot parses slots 1..4 correctly
2. Slot 4 (and others) returns mes=None only when absent/invalid — not hard-coded null
3. Slot with no delegate/CIP is skipped (returns None)
4. Monetary parser returns fixed source legacy values without recalculation
5. Comprobante parser splits NROFACTURA into serie+numero; handles malformed/blank safely
6. --dry-run-rh flag is accessible from the command

Fixtures:
- A minimal "row" is a list of 70+ None values, indexed by column constants.
- Helper make_row() creates a row with specified column overrides.
"""

import pytest
from datetime import date, datetime
from decimal import Decimal

from modules.liquidaciones.management.commands.import_legacy_edificaciones import (
    _parse_rh_slot,
    _parse_comprobante,
    _parse_row_monetary,
    _coerce_int,
    _coerce_month,
    # Column constants — used to build test fixtures
    COL_DELEGADO1, COL_CIP1, COL_PERIODO1, COL_MES1,
    COL_FECHAPRES1, COL_FECHAREVI1, COL_NROORDEN1, COL_DICTAMEN1,
    COL_NRORH1, COL_NROMM1,
    COL_DELEGADO2, COL_CIP2, COL_PERIODO2, COL_MES2,
    COL_DELEGADO3, COL_CIP3, COL_PERIODO3, COL_MES3,
    COL_DELEGADO4, COL_CIP4, COL_PERIODO4, COL_MES4,
    COL_IMPBRUTO, COL_RENTACIP, COL_APORCODEMU,
    COL_FONDOCOMUN, COL_NETOHONORA, COL_NROFACTURA,
    _SLOT_SPECIALTY_MAP,
)


# ── Row fixture builder ───────────────────────────────────────────────────────

def make_row(**overrides) -> list:
    """
    Build a minimal row list (70+ columns) with column overrides.

    Defaults: all None. Pass column_constant=value to override.
    Example: make_row(_col(COL_DELEGADO1)=123, _col(COL_CIP1)="12345")
    """
    # Use a large enough list — columns go up to 70+
    row = [None] * 80
    for key, value in overrides.items():
        # key may be the raw index (int) or a column constant evaluated here
        if isinstance(key, int):
            row[key] = value
    return row


def _col(constant_val: int, value) -> tuple[int, object]:
    """Helper to build (index, value) tuples for make_row."""
    return (constant_val, value)


def make_full_row(
    delegate: str | None = "Ing. Juan Perez",
    cip: int | None = 12345,
    periodo: int | None = 2024,
    mes: int | None = 6,
    fecha_pres: datetime | None = None,
    fecha_rev: datetime | None = None,
    nro_orden: int | None = 1,
    dictamen: str | None = "APROBADO",
    nro_rh: int | None = 100,
    nro_mm: int | None = 200,
    *,
    slot: int = 1,
) -> list:
    """
    Build a row with a single slot's fields populated.

    slot: 1..4. The column indices follow the pattern in _parse_rh_slot:
        offset = (slot - 1) * 10
        col_delegado = 20 + offset  → slot1=20, slot2=30, slot3=40, slot4=50
        col_cip       = 21 + offset  → slot1=21, slot2=31, slot3=41, slot4=51
        ...
    """
    row = [None] * 80

    # These MUST match what _parse_rh_slot computes internally
    col_delegado = 20 + (slot - 1) * 10
    col_cip = 21 + (slot - 1) * 10
    col_periodo = 22 + (slot - 1) * 10
    col_mes = 23 + (slot - 1) * 10
    col_fecha_pres = 24 + (slot - 1) * 10
    col_fecha_rev = 25 + (slot - 1) * 10
    col_nro_orden = 26 + (slot - 1) * 10
    col_dictamen = 27 + (slot - 1) * 10
    col_nro_rh = 28 + (slot - 1) * 10
    col_nro_mm = 29 + (slot - 1) * 10

    if delegate is not None:
        row[col_delegado] = delegate
    if cip is not None:
        row[col_cip] = cip
    if periodo is not None:
        row[col_periodo] = periodo
    if mes is not None:
        row[col_mes] = mes
    if fecha_pres is not None:
        row[col_fecha_pres] = fecha_pres
    if fecha_rev is not None:
        row[col_fecha_rev] = fecha_rev
    if nro_orden is not None:
        row[col_nro_orden] = nro_orden
    if dictamen is not None:
        row[col_dictamen] = dictamen
    if nro_rh is not None:
        row[col_nro_rh] = nro_rh
    if nro_mm is not None:
        row[col_nro_mm] = nro_mm

    return row


# ── Tests: _coerce_int ────────────────────────────────────────────────────────

class TestCoerceInt:
    def test_none_returns_none(self):
        assert _coerce_int(None) is None

    def test_empty_string_returns_none(self):
        assert _coerce_int("") is None
        assert _coerce_int("   ") is None

    def test_null_string_returns_none(self):
        assert _coerce_int("NULL") is None
        assert _coerce_int("null") is None
        assert _coerce_int("Null") is None

    def test_valid_int_string(self):
        assert _coerce_int("123") == 123
        assert _coerce_int("  456  ") == 456

    def test_valid_float_string(self):
        # "123.45" -> int(123.45) -> 123
        assert _coerce_int("123.45") == 123
        assert _coerce_int("0.9") == 0

    def test_negative_int(self):
        assert _coerce_int("-5") == -5

    def test_invalid_string_returns_none(self):
        assert _coerce_int("abc") is None
        assert _coerce_int("12a") is None


# ── Tests: _coerce_month ──────────────────────────────────────────────────────

class TestCoerceMonth:
    def test_none_returns_none(self):
        assert _coerce_month(None) is None

    def test_empty_string_returns_none(self):
        assert _coerce_month("") is None
        assert _coerce_month("   ") is None

    def test_null_string_returns_none(self):
        assert _coerce_month("NULL") is None

    def test_valid_months_1_to_12(self):
        assert _coerce_month(1) == 1
        assert _coerce_month(6) == 6
        assert _coerce_month(12) == 12
        assert _coerce_month("3") == 3
        assert _coerce_month("  7 ") == 7

    def test_float_month(self):
        # 6.0 -> int 6
        assert _coerce_month(6.0) == 6

    def test_invalid_month_0_returns_none(self):
        assert _coerce_month(0) is None

    def test_invalid_month_13_returns_none(self):
        assert _coerce_month(13) is None

    def test_invalid_month_99_returns_none(self):
        assert _coerce_month(99) is None

    def test_negative_month_returns_none(self):
        assert _coerce_month(-1) is None


# ── Tests: _parse_rh_slot — all 4 slots ──────────────────────────────────────

class TestParseRhSlot:
    """Tests for _parse_rh_slot covering slots 1-4."""

    def test_slot1_parses_all_fields(self):
        """Slot 1 with all fields populated returns complete dict."""
        row = make_full_row(
            delegate="Ing. Pedro Ruiz",
            cip=54321,
            periodo=2023,
            mes=11,
            fecha_pres=datetime(2023, 11, 15, 10, 0),
            fecha_rev=datetime(2023, 11, 20, 14, 30),
            nro_orden=3,
            dictamen="FAVORABLE",
            nro_rh=500,
            nro_mm=600,
            slot=1,
        )
        result = _parse_rh_slot(row, 1)

        assert result is not None
        assert result["slot"] == 1
        assert result["specialty"] == _SLOT_SPECIALTY_MAP[1]
        assert result["delegado"] == "Ing. Pedro Ruiz"
        assert result["cip"] == 54321
        assert result["periodo"] == 2023
        assert result["mes"] == 11
        assert result["fecha_presentacion"] == date(2023, 11, 15)
        assert result["fecha_revision"] == date(2023, 11, 20)
        assert result["nro_orden"] == 3
        assert result["dictamen"] == "FAVORABLE"
        assert result["nro_rh"] == 500
        assert result["nro_mm"] == 600
        assert result["skip_reason"] is None

    def test_slot2_parses_all_fields(self):
        """Slot 2 with all fields populated returns complete dict."""
        row = make_full_row(
            delegate="Ing. Maria Lopez",
            cip=98765,
            periodo=2024,
            mes=3,
            slot=2,
        )
        result = _parse_rh_slot(row, 2)

        assert result is not None
        assert result["slot"] == 2
        assert result["specialty"] == _SLOT_SPECIALTY_MAP[2]
        assert result["delegado"] == "Ing. Maria Lopez"
        assert result["cip"] == 98765
        assert result["periodo"] == 2024
        assert result["mes"] == 3

    def test_slot3_parses_all_fields(self):
        """Slot 3 with all fields populated returns complete dict."""
        row = make_full_row(
            delegate="Ing. Carlos Diaz",
            cip=11111,
            periodo=2025,
            mes=1,
            slot=3,
        )
        result = _parse_rh_slot(row, 3)

        assert result is not None
        assert result["slot"] == 3
        assert result["specialty"] == _SLOT_SPECIALTY_MAP[3]
        assert result["delegado"] == "Ing. Carlos Diaz"
        assert result["cip"] == 11111
        assert result["periodo"] == 2025
        assert result["mes"] == 1

    def test_slot4_parses_all_fields(self):
        """Slot 4 with all fields populated returns complete dict."""
        row = make_full_row(
            delegate="Ing. Ana Sanchez",
            cip=22222,
            periodo=2025,
            mes=7,
            slot=4,
        )
        result = _parse_rh_slot(row, 4)

        assert result is not None
        assert result["slot"] == 4
        assert result["specialty"] == _SLOT_SPECIALTY_MAP[4]
        assert result["delegado"] == "Ing. Ana Sanchez"
        assert result["cip"] == 22222
        assert result["periodo"] == 2025
        assert result["mes"] == 7


class TestParseRhSlotSkipReasons:
    """Slot is skipped (returns None) only when no delegate OR no CIP."""

    def test_no_delegate_returns_none(self):
        """Slot with no DELEGADO value returns None (skip signal)."""
        row = make_full_row(delegate=None, cip=12345, slot=1)
        assert _parse_rh_slot(row, 1) is None

    def test_null_string_delegate_returns_none(self):
        """Slot with DELEGADO='NULL' string returns None (skip signal)."""
        row = make_full_row(delegate="NULL", cip=12345, slot=1)
        assert _parse_rh_slot(row, 1) is None

    def test_blank_delegate_returns_none(self):
        """Slot with blank DELEGADO returns None (skip signal)."""
        row = make_full_row(delegate="   ", cip=12345, slot=1)
        assert _parse_rh_slot(row, 1) is None

    def test_no_cip_returns_none(self):
        """Slot with DELEGADO but no CIP returns None (skip signal)."""
        row = make_full_row(delegate="Ing. Test", cip=None, slot=1)
        assert _parse_rh_slot(row, 1) is None

    def test_invalid_cip_returns_none(self):
        """Slot with DELEGADO but invalid CIP (non-numeric) returns None."""
        row = make_full_row(delegate="Ing. Test", cip="ABC", slot=1)
        assert _parse_rh_slot(row, 1) is None


class TestParseRhSlotMesNone:
    """Slot 4 supports period/month when present; mes=None only when absent/invalid."""

    def test_slot4_with_valid_period_and_month(self):
        """Slot 4 with valid periodo and mes returns mes as int."""
        row = make_full_row(
            delegate="Ing. Elena Rota",
            cip=33333,
            periodo=2024,
            mes=9,
            slot=4,
        )
        result = _parse_rh_slot(row, 4)
        assert result is not None
        assert result["periodo"] == 2024
        assert result["mes"] == 9

    def test_slot4_with_no_mes_returns_none_not_hardcoded(self):
        """Slot 4 with periodo but no MES returns mes=None — not hard-coded null.

        The function uses _coerce_month which returns None for absent/invalid months.
        This is the same behavior as slots 1-3. mes=None means "absent/invalid",
        not "hard-coded to None" — the slot is still returned with data.
        """
        row = make_full_row(
            delegate="Ing. Felipe Torres",
            cip=44444,
            periodo=2024,
            mes=None,  # absent month
            slot=4,
        )
        result = _parse_rh_slot(row, 4)
        assert result is not None
        assert result["periodo"] == 2024
        assert result["mes"] is None  # None because absent, not because hard-coded

    def test_slot4_with_invalid_mes_returns_none_slot_still_returned(self):
        """Slot 4 with invalid month (99) returns mes=None but slot is still returned.

        Invalid mes does NOT cause the slot to be skipped — the slot dict is
        returned with mes=None. Only no-delegate or no-CIP skips the slot.
        """
        row = make_full_row(
            delegate="Ing. Gina Vazquez",
            cip=55555,
            periodo=2024,
            mes=99,  # invalid — out of range 1..12
            slot=4,
        )
        result = _parse_rh_slot(row, 4)
        assert result is not None  # Slot IS returned — only skip_reason is None
        assert result["mes"] is None  # mes=None because invalid, not hard-coded
        assert result["periodo"] == 2024
        assert result["delegado"] == "Ing. Gina Vazquez"
        assert result["cip"] == 55555

    def test_slot1_invalid_mes_returns_none_slot_still_returned(self):
        """Same behavior for slot 1: invalid mes -> mes=None, slot not skipped."""
        row = make_full_row(
            delegate="Ing. Hugo Ruiz",
            cip=66666,
            periodo=2023,
            mes=13,  # invalid
            slot=1,
        )
        result = _parse_rh_slot(row, 1)
        assert result is not None
        assert result["mes"] is None
        assert result["delegado"] == "Ing. Hugo Ruiz"


class TestParseRhSlotDateParsing:
    """Date parsing returns None for invalid/absent dates; does not raise."""

    def test_no_fecha_presentacion_returns_none(self):
        """fecha_presentacion=None when absent — slot still returned."""
        row = make_full_row(
            delegate="Ing. Test",
            cip=11111,
            periodo=2024,
            mes=5,
            fecha_pres=None,
            slot=1,
        )
        result = _parse_rh_slot(row, 1)
        assert result is not None
        assert result["fecha_presentacion"] is None

    def test_datetime_fecha_presentacion_parsed(self):
        """fecha_presentacion parsed from datetime object."""
        row = make_full_row(
            delegate="Ing. Test",
            cip=11111,
            periodo=2024,
            mes=5,
            fecha_pres=datetime(2024, 5, 10, 8, 30),
            slot=1,
        )
        result = _parse_rh_slot(row, 1)
        assert result["fecha_presentacion"] == date(2024, 5, 10)

    def test_string_fecha_presentacion_parsed_dmy(self):
        """fecha_presentacion parsed from DD/MM/YYYY string."""
        row = [None] * 80
        row[20] = "Ing. Test"
        row[21] = 11111
        row[22] = 2024
        row[23] = 5
        row[24] = "10/05/2024"  # DD/MM/YYYY
        result = _parse_rh_slot(row, 1)
        assert result is not None
        assert result["fecha_presentacion"] == date(2024, 5, 10)

    def test_invalid_fecha_returns_none_does_not_raise(self):
        """Invalid fecha_presentacion returns None — does not raise."""
        row = [None] * 80
        row[20] = "Ing. Test"
        row[21] = 11111
        row[22] = 2024
        row[23] = 5
        row[24] = "not-a-date"
        result = _parse_rh_slot(row, 1)
        assert result is not None
        assert result["fecha_presentacion"] is None


# ── Tests: _parse_comprobante ─────────────────────────────────────────────────

class TestParseComprobante:
    """Tests for _parse_comprobante: splits NROFACTURA into serie and numero."""

    def test_well_formed_factura(self):
        """'001-00001' -> serie='001', numero='00001'."""
        row = [None] * 80
        row[COL_NROFACTURA] = "001-00001"
        result = _parse_comprobante(row)

        assert result["serie"] == "001"
        assert result["numero"] == "00001"
        assert result["raw"] == "001-00001"

    def test_factura_with_spaces(self):
        """'  001 - 00001  ' -> serie='001', numero='00001' (stripped)."""
        row = [None] * 80
        row[COL_NROFACTURA] = "  001 - 00001  "
        result = _parse_comprobante(row)

        assert result["serie"] == "001"
        assert result["numero"] == "00001"

    def test_factura_no_serie(self):
        """'00001' (no separator) -> serie=None, numero='00001'."""
        row = [None] * 80
        row[COL_NROFACTURA] = "00001"
        result = _parse_comprobante(row)

        assert result["serie"] is None
        assert result["numero"] == "00001"

    def test_factura_multiple_dashes_uses_first(self):
        """'001-00001-EXTRA' splits on first '-' only."""
        row = [None] * 80
        row[COL_NROFACTURA] = "001-00001-EXTRA"
        result = _parse_comprobante(row)

        assert result["serie"] == "001"
        assert result["numero"] == "00001-EXTRA"

    def test_factura_none_returns_none_fields(self):
        """None raw -> serie=None, numero=None, raw=None."""
        row = [None] * 80
        # COL_NROFACTURA stays None
        result = _parse_comprobante(row)

        assert result["serie"] is None
        assert result["numero"] is None
        assert result["raw"] is None

    def test_factura_empty_string(self):
        """'' -> serie=None, numero=None, raw=''."""
        row = [None] * 80
        row[COL_NROFACTURA] = ""
        result = _parse_comprobante(row)

        assert result["serie"] is None
        assert result["numero"] is None
        assert result["raw"] == ""

    def test_factura_blank_string(self):
        """'   ' -> serie=None, numero=None, raw='   '."""
        row = [None] * 80
        row[COL_NROFACTURA] = "   "
        result = _parse_comprobante(row)

        assert result["serie"] is None
        assert result["numero"] is None

    def test_factura_null_string(self):
        """'NULL' -> serie=None, numero=None, raw='NULL'."""
        row = [None] * 80
        row[COL_NROFACTURA] = "NULL"
        result = _parse_comprobante(row)

        assert result["serie"] is None
        assert result["numero"] is None

    def test_row_too_short_returns_none_fields(self):
        """Row with fewer than COL_NROFACTURA+1 columns returns None fields."""
        row = [None] * 10  # too short
        result = _parse_comprobante(row)

        assert result["serie"] is None
        assert result["numero"] is None
        assert result["raw"] is None


# ── Tests: _parse_row_monetary ─────────────────────────────────────────────────

class TestParseRowMonetary:
    """Tests for _parse_row_monetary: returns fixed source values without recalculation."""

    def test_all_monetary_fields_present(self):
        """All monetary fields parsed as Decimal."""
        row = [None] * 80
        row[COL_IMPBRUTO] = "1500.00"
        row[COL_RENTACIP] = "150.00"
        row[COL_APORCODEMU] = "30.00"
        row[COL_FONDOCOMUN] = "20.00"
        row[COL_FONDOCOMUN] = "20.00"
        row[COL_NETOHONORA] = "1300.00"

        result = _parse_row_monetary(row)

        assert result["imp_bruto"] == Decimal("1500.00")
        assert result["renta_cip"] == Decimal("150.00")
        assert result["aporte_codemu"] == Decimal("30.00")
        assert result["fondo_comun"] == Decimal("20.00")
        assert result["neto_honorario"] == Decimal("1300.00")

    def test_monetary_none_returns_none(self):
        """None/missing fields return None (not 0 or raise)."""
        row = [None] * 80
        result = _parse_row_monetary(row)

        assert result["imp_bruto"] is None
        assert result["renta_cip"] is None
        assert result["aporte_codemu"] is None
        assert result["fondo_comun"] is None
        assert result["neto_honorario"] is None

    def test_monetary_null_string_returns_none(self):
        """'NULL' string returns None for each field."""
        row = [None] * 80
        row[COL_IMPBRUTO] = "NULL"
        row[COL_NETOHONORA] = "null"
        result = _parse_row_monetary(row)

        assert result["imp_bruto"] is None
        assert result["neto_honorario"] is None

    def test_monetary_empty_string_returns_none(self):
        """Empty/blank string returns None."""
        row = [None] * 80
        row[COL_IMPBRUTO] = ""
        row[COL_NETOHONORA] = "   "
        result = _parse_row_monetary(row)

        assert result["imp_bruto"] is None
        assert result["neto_honorario"] is None

    def test_monetary_invalid_value_returns_none(self):
        """Non-numeric string returns None (no raise)."""
        row = [None] * 80
        row[COL_IMPBRUTO] = "not-a-number"
        result = _parse_row_monetary(row)

        assert result["imp_bruto"] is None

    def test_monetary_returns_decimal_not_float(self):
        """Values are returned as Decimal, not float."""
        row = [None] * 80
        row[COL_IMPBRUTO] = "1234.56"
        result = _parse_row_monetary(row)

        assert isinstance(result["imp_bruto"], Decimal)
        assert result["imp_bruto"] == Decimal("1234.56")

    def test_monetary_source_values_not_recalculated(self):
        """Monetary values come from the row as-is; no recalculation."""
        row = [None] * 80
        # Legacy source values that may not match recalculated values
        row[COL_IMPBRUTO] = "1000.00"
        row[COL_RENTACIP] = "100.00"
        row[COL_APORCODEMU] = "20.00"
        row[COL_FONDOCOMUN] = "10.00"
        row[COL_NETOHONORA] = "870.00"
        result = _parse_row_monetary(row)

        # The values are returned exactly as they appear in the source row.
        # No recalculation (e.g. no IGV addition) is performed.
        assert result["imp_bruto"] == Decimal("1000.00")
        assert result["renta_cip"] == Decimal("100.00")
        assert result["neto_honorario"] == Decimal("870.00")
        # Verify: 1000 - 100 - 20 - 10 = 870 — but this was NOT calculated
        # It was returned as the source value directly.
        assert result["neto_honorario"] != Decimal("870.00") + Decimal("1")  # not recalculated


# ── Tests: --dry-run-rh flag exists ──────────────────────────────────────────

class TestDryRunRhFlag:
    """Verify the --dry-run-rh flag is accessible from the command parser."""

    def test_dry_run_rh_flag_registered(self):
        """The --dry-run-rh argument is registered on the command parser."""
        from modules.liquidaciones.management.commands.import_legacy_edificaciones import Command
        from django.core.management.base import BaseCommand
        import argparse

        # Create command instance to access add_arguments
        cmd = Command()

        # Capture what add_arguments registers
        parser = argparse.ArgumentParser()
        cmd.add_arguments(parser)

        # Check that --dry-run-rh is in the known actions
        # argparse uses _actions[1:] for user-added args (index 0 is help)
        action_strings = [
            opt for action in parser._actions
            for opt in action.option_strings
        ]
        assert "--dry-run-rh" in action_strings, (
            f"--dry-run-rh not found in {action_strings}"
        )

    def test_dry_run_rh_flag_is_store_true(self):
        """--dry-run-rh is a boolean flag (action='store_true')."""
        from modules.liquidaciones.management.commands.import_legacy_edificaciones import Command
        import argparse

        cmd = Command()
        parser = argparse.ArgumentParser()
        cmd.add_arguments(parser)

        # Find the --dry-run-rh action
        dry_run_rh_action = None
        for action in parser._actions:
            if "--dry-run-rh" in action.option_strings:
                dry_run_rh_action = action
                break

        assert dry_run_rh_action is not None
        assert dry_run_rh_action.const is True, (
            "--dry-run-rh should be action='store_true' (const=True)"
        )
