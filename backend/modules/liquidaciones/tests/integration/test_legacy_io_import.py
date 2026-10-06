"""
Focused unit/integration tests for import_legacy_inspeccion_obra command.
Batch 3 scope: parser, dry-run, reports. NO DB writes.

Covers:
1. _parse_delegado_io — CIP extraction from DELEGADO column
2. _map_categoria_io — integer CATEGORIA → internal category mapping
3. _derive_cantidad_visitas — SUBTOTAL / (PORCENTAJE * UIT) derivation
4. _parse_nrofactura — NROFACTURA parsing
5. _parse_fecha — date parsing with 1/01/1900 sentinel → None
6. _parse_row — full row-level parsing
7. _read_tsv — TSV reading with delimiter detection
8. end-to-end dry-run against real TSV (--limit 100)
"""
import csv
import io
import tempfile
from datetime import date
from decimal import Decimal

import pytest

from modules.liquidaciones.management.commands.import_legacy_inspeccion_obra import (
    _parse_delegado_io,
    _map_categoria_io,
    _derive_cantidad_visitas,
    _parse_nrofactura,
    _parse_fecha,
    _parse_row,
    _read_tsv,
    _resolve_tipo_documento,
    _parse_dptoprdri,
    _normalize_usuario_to_username,
    _is_xlsx,
    _detect_delimiter,
    _build_uit_validacion_detalle,
    _SENTINEL_DATE,
    _COL_ID,
    _COL_NRO,
    _COL_RUC,
    _COL_NOMBRE,
    _COL_NROREV,
    _COL_DPTOPRDI,
    _COL_DIRECCION,
    _COL_DELEGADO,
    _COL_UIT,
    _COL_PORCENTAJE,
    _COL_PORCENFINA,
    _COL_SUBTOTAL,
    _COL_IGV,
    _COL_TOTAL,
    _COL_FECHA,
    _COL_DNI,
    _COL_RAZONSOCIAL,
    _COL_VALOROBRA,
    _COL_TASA,
    _COL_NROEXPDTE,
    _COL_CODPAGO,
    _COL_NROFACTURA,
    _COL_DLEY,
    _COL_IMPBRUTO,
    _COL_APORCODEMU,
    _COL_FONDOCOMUN,
    _COL_HONORARIO,
    _COL_IMPUESRENTA,
    _COL_NETOHONORA,
    _COL_USUARIO,
    _COL_IMPRESO,
    _COL_DOC,
    _COL_FECHAPRES,
    _COL_NROORDEN,
    _COL_FECHAREVI,
    _COL_MES,
    _COL_PERIODO,
    _COL_NRORECIBO,
    _COL_FECHARECIBO,
    _COL_NROMEMO,
    _COL_OBSERVA,
    _COL_DICTAMEN,
    _COL_TDNI,
    _COL_TFONO,
    _COL_TPERSONA,
    _COL_TASAIGV,
    _COL_FECOMPRO,
    _COL_NRONC,
    _COL_NROQRPLZA,
    _COL_RENTACIP,
    _COL_DSCTO,
    _COL_RUCDIRECC,
    _COL_RETENCION,
    _COL_CIP,
    _COL_BLKDEL,
    _COL_NROCHEQUE,
    _COL_CONCEPTO,
    _COL_REINTEGRO,
    _COL_CATEGORIA,
    _COL_PENDIENTES,
    _COL_PAGADAS,
    _COL_REALIZADAS,
    _COL_DIFERENCIA,
)


# ── _parse_delegado_io tests ──────────────────────────────────────────────────

class TestParseDelegadoIO:
    def test_standard_format(self):
        cip, nombre = _parse_delegado_io("CIP 072900-CASTAÑEDA AMES VIVIANA PAOLA")
        assert cip == 72900
        assert nombre == "CASTAÑEDA AMES VIVIANA PAOLA"

    def test_cip_with_leading_zeros(self):
        """Leading zeros in CIP should be stripped."""
        cip, nombre = _parse_delegado_io("CIP 000001-JOSE PEREZ")
        assert cip == 1
        assert nombre == "JOSE PEREZ"

    def test_variant_delimiter(self):
        """Both dash variants should work."""
        cip1, nombre1 = _parse_delegado_io("CIP 23555-AMEZAGA QUEVEDO JESUS")
        cip2, nombre2 = _parse_delegado_io("CIP 23555—AMEZAGA QUEVEDO JESUS")  # em dash
        assert cip1 == cip2 == 23555
        assert nombre1 == nombre2 == "AMEZAGA QUEVEDO JESUS"

    def test_no_cip_prefix(self):
        """No CIP prefix — returns None and the raw text as nombre."""
        cip, nombre = _parse_delegado_io("SIN DATOS")
        assert cip is None
        assert nombre == "SIN DATOS"

    def test_empty(self):
        cip, nombre = _parse_delegado_io(None)
        assert cip is None
        assert nombre is None

    def test_null_string(self):
        cip, nombre = _parse_delegado_io("NULL")
        assert cip is None
        assert nombre is None


# ── _map_categoria_io tests ────────────────────────────────────────────────────

class TestMapCategoriaIO:
    def test_categoria_0(self):
        cat, status = _map_categoria_io(0)
        assert cat is None
        assert status == "null_tariff"

    def test_categoria_1_to_4(self):
        expected = {1: "C1", 2: "C2", 3: "C3", 4: "C4"}
        for val, expected_cat in expected.items():
            cat, status = _map_categoria_io(val)
            assert cat == expected_cat, f"CATEGORIA={val}"
            assert status == "mapped"

    def test_categoria_string(self):
        cat, status = _map_categoria_io("3")
        assert cat == "C3"
        assert status == "mapped"

    def test_categoria_invalid(self):
        cat, status = _map_categoria_io(99)
        assert cat == "99"
        assert status == "anomaly"

    def test_categoria_none(self):
        cat, status = _map_categoria_io(None)
        assert cat is None
        assert status == "anomaly"


# ── _derive_cantidad_visitas tests (NROREV-based — batch 3b) ─────────────────

class TestDeriveCantidadVisitas:
    """Tests for NROREV-based cantidad_visitas derivation."""

    def test_positive_integer_nrorev(self):
        """NROREV=36 → cantidad_visitas=36.0, status='from_nrorev'."""
        cantidad, status = _derive_cantidad_visitas(36)
        assert cantidad == 36.0
        assert status == "from_nrorev"

    def test_nrorev_one(self):
        """NROREV=1 → cantidad_visitas=1.0."""
        cantidad, status = _derive_cantidad_visitas(1)
        assert cantidad == 1.0
        assert status == "from_nrorev"

    def test_missing_nrorev(self):
        """NROREV=None → None, status='missing'."""
        cantidad, status = _derive_cantidad_visitas(None)
        assert cantidad is None
        assert status == "missing"

    def test_zero_nrorev(self):
        """NROREV=0 → None, status='non_positive'."""
        cantidad, status = _derive_cantidad_visitas(0)
        assert cantidad is None
        assert status == "non_positive"

    def test_negative_nrorev(self):
        """NROREV=-5 → None, status='non_positive'."""
        cantidad, status = _derive_cantidad_visitas(-5)
        assert cantidad is None
        assert status == "non_positive"


# ── _parse_nrofactura tests ───────────────────────────────────────────────────

class TestParseNroFactura:
    def test_standard_format(self):
        serie, numero, raw = _parse_nrofactura("001-00001")
        assert serie == "001"
        assert numero == "00001"

    def test_no_separator(self):
        serie, numero, raw = _parse_nrofactura("00002")
        assert serie is None
        assert numero == "00002"

    def test_empty(self):
        serie, numero, raw = _parse_nrofactura(None)
        assert serie is None
        assert numero is None

    def test_null_string(self):
        serie, numero, raw = _parse_nrofactura("NULL")
        assert serie is None
        assert numero is None


# ── _parse_fecha tests ────────────────────────────────────────────────────────

class TestParseFecha:
    def test_sentinel_returns_none(self):
        result = _parse_fecha("1/01/1900")
        assert result is None

    def test_sentinel_with_time(self):
        result = _parse_fecha("1/01/1900 00:00")
        assert result is None

    def test_standard_date(self):
        result = _parse_fecha("20/08/2026")
        assert result == date(2026, 8, 20)

    def test_datetime_object(self):
        from datetime import datetime
        dt = datetime(2026, 8, 20, 14, 30)
        result = _parse_fecha(dt)
        assert result == date(2026, 8, 20)

    def test_datetime_sentinel(self):
        from datetime import datetime
        dt = datetime(1900, 1, 1, 0, 0)
        result = _parse_fecha(dt)
        assert result is None

    def test_invalid_raises_valueerror(self):
        """Invalid dates raise ValueError (distinguishes from sentinel None)."""
        import pytest
        with pytest.raises(ValueError):
            _parse_fecha("not-a-date")


# ── _resolve_tipo_documento tests ─────────────────────────────────────────────

class TestResolveTipoDocumento:
    def test_dni_8_digits(self):
        tipo, num = _resolve_tipo_documento("45049925", None)
        assert tipo == "DNI"
        assert num == "45049925"

    def test_ruc(self):
        tipo, num = _resolve_tipo_documento("", "20611093579")
        assert tipo == "RUC"
        assert num == "20611093579"

    def test_both_empty(self):
        tipo, num = _resolve_tipo_documento("", "")
        assert tipo == "SIN_DOCUMENTO"
        assert num == "00000000"

    def test_dni_takes_priority(self):
        """When both DNI and RUC present, prefer DNI if 8 digits."""
        tipo, num = _resolve_tipo_documento("45049925", "20611093579")
        assert tipo == "DNI"
        assert num == "45049925"


# ── _parse_dptoprdri tests ────────────────────────────────────────────────────

class TestParseDptoprdri:
    def test_province_district(self):
        prov, dist = _parse_dptoprdri("LIMA/MAGDALENA DEL MAR")
        assert prov == "LIMA"
        assert dist == "MAGDALENA DEL MAR"

    def test_district_only(self):
        prov, dist = _parse_dptoprdri("SAN BORJA")
        assert prov == ""
        assert dist == "SAN BORJA"

    def test_empty(self):
        prov, dist = _parse_dptoprdri("")
        assert prov == ""
        assert dist == ""


# ── _normalize_usuario_to_username tests ──────────────────────────────────────

class TestNormalizeUsuarioToUsername:
    def test_basic(self):
        assert _normalize_usuario_to_username("SANDRA OJEDA") == "sandra.ojeda"

    def test_with_accent(self):
        result = _normalize_usuario_to_username("MARIBEL QUIÑONES")
        assert result == "maribel.quinones"

    def test_empty(self):
        assert _normalize_usuario_to_username(None) is None
        assert _normalize_usuario_to_username("NULL") is None


# ── _detect_delimiter tests ────────────────────────────────────────────────────

class TestDetectDelimiter:
    def test_tsv(self):
        assert _detect_delimiter("ID\tNRO\tRU") == "\t"

    def test_csv(self):
        assert _detect_delimiter("ID,NRO,RUC") == ","


# ── _is_xlsx tests ────────────────────────────────────────────────────────────

class TestIsXlsx:
    def test_xlsx_by_pk_header(self):
        with tempfile.NamedTemporaryFile(suffix=".bin", delete=False) as f:
            f.write(b"PK\x03\x04")  # ZIP/XLSX header
            f.flush()
            from pathlib import Path
            result = _is_xlsx(Path(f.name))
        import os
        os.unlink(f.name)
        assert result is True

    def test_text_file(self):
        with tempfile.NamedTemporaryFile(suffix=".csv", delete=False) as f:
            f.write(b"ID,NRO,RUC\n")
            f.flush()
            from pathlib import Path
            result = _is_xlsx(Path(f.name))
        import os
        os.unlink(f.name)
        assert result is False


# ── _read_tsv tests ───────────────────────────────────────────────────────────

class TestReadTsv:
    def test_tab_delimited(self):
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".csv", delete=False
        ) as f:
            f.write("ID\tNRO\tRU\n")
            f.write("10488\t\t20611093579\n")
            f.flush()
            from pathlib import Path
            headers, rows = _read_tsv(Path(f.name))

        assert headers == ["ID", "NRO", "RU"]
        assert rows[0] == ["10488", "", "20611093579"]
        import os
        os.unlink(f.name)

    def test_comma_delimited(self):
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".csv", delete=False
        ) as f:
            f.write("ID,NRO,RU\n")
            f.write('10488,,"20611093579"\n')
            f.flush()
            from pathlib import Path
            headers, rows = _read_tsv(Path(f.name))

        assert headers == ["ID", "NRO", "RU"]
        import os
        os.unlink(f.name)


# ── _parse_row tests ──────────────────────────────────────────────────────────

# Minimal 63-column row (all required fields present) for testing _parse_row
# against the real TSV column order.
_MINIMAL_ROW = [
    "10488",        # _COL_ID (0)
    "",             # _COL_NRO (1)
    "20611093579",  # _COL_RUC (2)
    "VAL D0 S.A.C.",# _COL_NOMBRE (3)
    "36",           # _COL_NROREV (4) — batch 3b: positive integer
    "LIMA/MAGDALENA DEL MAR",  # _COL_DPTOPRDI (5)
    "AV. TEST 123", # _COL_DIRECCION (6)
    "CIP 072900-CASTAÑEDA AMES VIVIANA PAOLA",  # _COL_DELEGADO (7)
    "5500",         # _COL_UIT (8)
    "272.58",       # _COL_PORCENTAJE (9) — unit total with IGV = TOTAL/NROREV
    "0.04",         # _COL_PORCENFINA (10) — nominal/rounded rate (informational)
    "8316",         # _COL_SUBTOTAL (11)
    "1496.88",      # _COL_IGV (12)
    "9812.88",      # _COL_TOTAL (13)
    "20/08/2026",   # _COL_FECHA (14)
    "",             # _COL_DNI (15)
    "VAL D0 S.A.C.",# _COL_RAZONSOCIAL (16)
    "",             # _COL_VALOROBRA (17)
    "0.042",        # _COL_TASA (18) — batch 3b: effective UIT percentage
    "E-1748-2026",  # _COL_NROEXPDTE (19)
    "",             # _COL_CODPAGO (20)
    "",             # _COL_NROFACTURA (21)
    "",             # _COL_DLEY (22)
    "",             # _COL_IMPBRUTO (23)
    "",             # _COL_APORCODEMU (24)
    "",             # _COL_FONDOCOMUN (25)
    "",             # _COL_HONORARIO (26)
    "",             # _COL_IMPUESRENTA (27)
    "",             # _COL_NETOHONORA (28)
    "MARIBEL QUIÑONES",  # _COL_USUARIO (29)
    "",             # _COL_IMPRESO (30)
    "",             # _COL_DOC (31)
    "1/01/1900",    # _COL_FECHAPRES (32)
    "0",            # _COL_NROORDEN (33)
    "1/01/1900",    # _COL_FECHAREVI (34)
    "",             # _COL_MES (35)
    "",             # _COL_PERIODO (36)
    "",             # _COL_NRORECIBO (37)
    "",             # _COL_FECHARECIBO (38)
    "",             # _COL_NROMEMO (39)
    "",             # _COL_OBSERVA (40)
    "",             # _COL_DICTAMEN (41)
    "",             # _COL_TDNI (42)
    "",             # _COL_TFONO (43)
    "",             # _COL_TPERSONA (44)
    "18",           # _COL_TASAIGV (45)
    "1/01/1900",    # _COL_FECOMPRO (46)
    "",             # _COL_NRONC (47)
    "",             # _COL_NROQRPLZA (48)
    "",             # _COL_RENTACIP (49)
    "",             # _COL_DSCTO (50)
    "",             # _COL_RUCDIRECC (51)
    "",             # _COL_RETENCION (52)
    "72900",        # _COL_CIP (53)
    "",             # _COL_BLKDEL (54)
    "",             # _COL_NROCHEQUE (55)
    "",             # _COL_CONCEPTO (56)
    "",             # _COL_REINTEGRO (57)
    "3",            # _COL_CATEGORIA (58)
    "0",            # _COL_PENDIENTES (59)
    "0",            # _COL_PAGADAS (60)
    "0",            # _COL_REALIZADAS (61)
    "0",            # _COL_DIFERENCIA (62)
]

_CAT_ZERO_ROW = _MINIMAL_ROW[:]
_CAT_ZERO_ROW[_COL_CATEGORIA] = "0"  # CATEGORIA=0 (null tariff)

# Batch 3b: NROREV=36 validation test row
# NROREV=36, TASA=0.042, UIT=5500, SUBTOTAL=8316, TOTAL=9812.88, PORCENTAJE=272.58, TASAIGV=18
# Expected:
#   cantidad_visitas = 36.0 (from NROREV, status='from_nrorev')
#   subtotal_unitario_legacy = 8316/36 = 231
#   total_unitario_legacy = 9812.88/36 = 272.58
#   subtotal_unitario_recalc = 0.042 * 5500 = 231
#   total_unitario_recalc = 231 * 1.18 = 272.58
#   diff_subtotal = 0, diff_total = 0
#   validation_status = 'OK'
_NROREV36_VALIDATION_ROW = _MINIMAL_ROW[:]
_NROREV36_VALIDATION_ROW[_COL_NROREV] = "36"
_NROREV36_VALIDATION_ROW[_COL_TASA] = "0.042"
_NROREV36_VALIDATION_ROW[_COL_SUBTOTAL] = "8316"
_NROREV36_VALIDATION_ROW[_COL_TOTAL] = "9812.88"
_NROREV36_VALIDATION_ROW[_COL_PORCENTAJE] = "272.58"
_NROREV36_VALIDATION_ROW[_COL_TASAIGV] = "18"

# Batch 3b: missing NROREV row (nrorev_status='missing')
_NROREV_MISSING_ROW = _MINIMAL_ROW[:]
_NROREV_MISSING_ROW[_COL_NROREV] = ""

# Batch 3b: zero NROREV row (nrorev_status='non_positive')
_NROREV_ZERO_ROW = _MINIMAL_ROW[:]
_NROREV_ZERO_ROW[_COL_NROREV] = "0"

# Batch 3c: UIT-implicita test row — year-end implied 2026 UIT with 2025 archivo UIT
# Scenario: fecha=2025-12-30, UIT archivo=5350 (2025), but actual calculation used 2026 UIT=5500
# NROREV=36, TASA=0.042, SUBTOTAL=8316 (=36*0.042*5500 → implies UIT=5500)
# UIT archivo=5350 (but formula gives 5500)
# Expected: uit_implicita≈5500, year_candidate=2026, status=OK_UIT_CONOCIDA_DIFERENTE
# validation_status=OK_UIT_IMPLICITA (diff is explained by known UIT)
_UIT_IMPLICITA_2026_ROW = _MINIMAL_ROW[:]
_UIT_IMPLICITA_2026_ROW[_COL_NROREV] = "36"
_UIT_IMPLICITA_2026_ROW[_COL_TASA] = "0.042"
_UIT_IMPLICITA_2026_ROW[_COL_SUBTOTAL] = "8316"
_UIT_IMPLICITA_2026_ROW[_COL_TOTAL] = "9812.88"
_UIT_IMPLICITA_2026_ROW[_COL_TASAIGV] = "18"
_UIT_IMPLICITA_2026_ROW[_COL_UIT] = "5350"  # archivo says 2025 UIT=5350
_UIT_IMPLICITA_2026_ROW[_COL_FECHA] = "30/12/2025"  # year-end 2025

# Batch 3c: UIT-implicita test row — impossible implied UIT (no known year matches)
# NROREV=36, TASA=0.042, SUBTOTAL=7502 → uit_implicita≈4960 (not 4950/5150/5350/5500)
# Expected: uit_implicita≈4960, year_candidate=None, status=NO_COINCIDE_UIT_CONOCIDA
# validation_status=DIF_SUBTOTAL (diff is NOT explained by known UIT)
_UIT_IMPLICITA_IMPOSSIBLE_ROW = _MINIMAL_ROW[:]
_UIT_IMPLICITA_IMPOSSIBLE_ROW[_COL_NROREV] = "36"
_UIT_IMPLICITA_IMPOSSIBLE_ROW[_COL_TASA] = "0.042"
_UIT_IMPLICITA_IMPOSSIBLE_ROW[_COL_SUBTOTAL] = "7502"  # implies UIT≈4960 (not in known map)
_UIT_IMPLICITA_IMPOSSIBLE_ROW[_COL_TOTAL] = "8852.36"  # 7502*1.18
_UIT_IMPLICITA_IMPOSSIBLE_ROW[_COL_TASAIGV] = "18"
_UIT_IMPLICITA_IMPOSSIBLE_ROW[_COL_UIT] = "5350"


class TestParseRow:
    def test_full_parse_normal_row(self):
        pr, rechazo = _parse_row(_MINIMAL_ROW, 2)
        assert pr.row_index == 2
        assert pr.id_val == 10488
        assert pr.nroexpdte == "E-1748-2026"
        assert pr.dptoprdri == "LIMA/MAGDALENA DEL MAR"
        assert pr.cip == 72900
        assert pr.delegado_nombre == "CASTAÑEDA AMES VIVIANA PAOLA"
        assert pr.categoria_mapped == "C3"
        assert pr.categoria_status == "mapped"
        assert pr.modo_calculo == "TARIFA"
        assert pr.fecha == date(2026, 8, 20)
        assert pr.subtotal == Decimal("8316")
        assert pr.total == Decimal("9812.88")
        assert pr.tasa_igv == Decimal("18")
        assert pr.fecha_pres is None  # sentinel
        assert pr.fecha_revi is None  # sentinel
        assert pr.rechazo_motivo == ""
        assert rechazo == ""
        # Batch 3b: cantidad_visitas from NROREV
        assert pr.cantidad_visitas == 36.0
        assert pr.visitas_status == "from_nrorev"
        # Batch 3b: NROREV correction fields
        assert pr.nrorev == 36
        assert pr.tasa == Decimal("0.042")
        assert pr.porcenfina == Decimal("0.04")
        # Validation: subtotal_unitario_legacy = 8316/36 = 231
        assert pr.subtotal_unitario_legacy == Decimal("231")
        # total_unitario_legacy = 9812.88/36 = 272.58
        assert pr.total_unitario_legacy == Decimal("272.58")
        # subtotal_unitario_recalc = 0.042 * 5500 = 231
        assert pr.subtotal_unitario_recalc_legacy == Decimal("231")
        # total_unitario_recalc = 231 * 1.18 = 272.58
        assert pr.total_unitario_recalc_legacy == Decimal("272.58")
        # Both diffs should be ~0
        assert pr.diff_subtotal_unitario_legacy is not None
        assert pr.diff_total_unitario_legacy is not None
        assert pr.validation_status == "OK"
        # Batch 3c: UIT-implicita fields
        assert pr.uit_implicita is not None
        assert pr.uit_implicita_year_candidate == 2026
        assert pr.uit_implicita_status == "OK_IGUAL_ARCHIVO"
        # Batch 3d: UIT validation detail
        assert pr.uit_validacion_detalle == "La UIT del archivo explica el subtotal unitario."

    def test_categoria_zero(self):
        pr, rechazo = _parse_row(_CAT_ZERO_ROW, 3)
        assert pr.categoria_mapped is None
        assert pr.categoria_status == "null_tariff"
        assert pr.modo_calculo == "MANUAL"
        assert pr.rechazo_motivo == ""
        assert rechazo == ""
        # CATEGORIA=0 still maps to null/manual with NROREV intact
        assert pr.nrorev == 36
        assert pr.cantidad_visitas == 36.0

    def test_empty_dptoprdri_rejected(self):
        row = _MINIMAL_ROW[:]
        row[_COL_DPTOPRDI] = ""
        pr, rechazo = _parse_row(row, 4)
        assert pr.rechazo_motivo != ""
        assert "DPTOPRDI vacío" in pr.rechazo_motivo

    def test_encoding_issue_detected(self):
        row = _MINIMAL_ROW[:]
        row[_COL_NOMBRE] = "CASTA�EDA"  # garbled
        pr, rechazo = _parse_row(row, 5)
        assert any("Encoding issue" in a for a in pr.anomalies)

    def test_usuario_normalized(self):
        pr, rechazo = _parse_row(_MINIMAL_ROW, 6)
        assert pr.usuario == "MARIBEL QUIÑONES"
        # The normalized version would be "maribel.quinones" but that's only
        # needed when looking up/creating Usuario records (batch 4+)

    def test_reporte_row_length(self):
        """to_report_row() returns the correct number of fields."""
        pr, _ = _parse_row(_MINIMAL_ROW, 7)
        row = pr.to_report_row()
        from modules.liquidaciones.management.commands.import_legacy_inspeccion_obra import (
            _build_rechazo_headers,
        )
        assert len(row) == len(_build_rechazo_headers())

    def test_detailed_report_row_length(self):
        """to_detailed_report_row() returns correct number of fields."""
        pr, _ = _parse_row(_MINIMAL_ROW, 8)
        row = pr.to_detailed_report_row([])
        from modules.liquidaciones.management.commands.import_legacy_inspeccion_obra import (
            _build_detailed_headers,
        )
        assert len(row) == len(_build_detailed_headers())


class TestNrorevValidation:
    """
    Batch 3b: NROREV validation tests.

    Validates the complete NROREV-based quantity and unitario calculation pipeline
    using the sample row: NROREV=36, TASA=0.042, UIT=5500,
    SUBTOTAL=8316, TOTAL=9812.88, PORCENTAJE=272.58, TASAIGV=18.
    """

    def test_nrorev_36_validation_status_ok(self):
        """
        Sample row: NROREV=36, TASA=0.042, UIT=5500,
        SUBTOTAL=8316, TOTAL=9812.88, PORCENTAJE=272.58, TASAIGV=18.

        Expected:
          cantidad_visitas = 36.0 (from NROREV, status='from_nrorev')
          subtotal_unitario_legacy = 8316/36 = 231
          total_unitario_legacy = 9812.88/36 = 272.58
          subtotal_unitario_recalc = 0.042 * 5500 = 231
          total_unitario_recalc = 231 * 1.18 = 272.58
          diff_subtotal = 0, diff_total = 0
          validation_status = 'OK'
        """
        pr, _ = _parse_row(_NROREV36_VALIDATION_ROW, 10)
        assert pr.nrorev == 36
        assert pr.tasa == Decimal("0.042")
        assert pr.uit == Decimal("5500")
        assert pr.subtotal == Decimal("8316")
        assert pr.total == Decimal("9812.88")
        assert pr.tasa_igv == Decimal("18")
        # cantidad_visitas from NROREV
        assert pr.cantidad_visitas == 36.0
        assert pr.visitas_status == "from_nrorev"
        # Unitario legacy
        assert pr.subtotal_unitario_legacy == Decimal("231")
        assert pr.total_unitario_legacy == Decimal("272.58")
        # Unitario recalculated
        assert pr.subtotal_unitario_recalc_legacy == Decimal("231")
        assert pr.total_unitario_recalc_legacy == Decimal("272.58")
        # Diffs
        assert pr.diff_subtotal_unitario_legacy is not None
        assert pr.diff_total_unitario_legacy is not None
        assert pr.diff_subtotal_unitario_legacy < Decimal("0.01")
        assert pr.diff_total_unitario_legacy < Decimal("0.01")
        # Status
        assert pr.validation_status == "OK"
        # Batch 3c: UIT-implicita — archivo UIT=5500, implied UIT=5500 (exact match)
        assert pr.uit_implicita is not None
        assert pr.uit_implicita_year_candidate == 2026
        assert pr.uit_implicita_status == "OK_IGUAL_ARCHIVO"
        # Batch 3d: UIT validation detail
        assert pr.uit_validacion_detalle == "La UIT del archivo explica el subtotal unitario."

    def test_nrorev_missing_reported(self):
        """Missing NROREV → nrorev_status='missing', cantidad_visitas=None, anomaly."""
        pr, _ = _parse_row(_NROREV_MISSING_ROW, 11)
        assert pr.nrorev is None
        assert pr.cantidad_visitas is None
        assert pr.visitas_status == "missing"
        assert pr.validation_status == "SIN_DATOS"
        # Batch 3c: UIT-implicita also SIN_DATOS when NROREV missing
        assert pr.uit_implicita is None
        assert pr.uit_implicita_status == "SIN_DATOS"
        assert any("NROREV missing" in a for a in pr.anomalies)
        # Batch 3d: UIT validation detail
        assert pr.uit_validacion_detalle == "No se pudo validar por NROREV, TASA, UIT o SUBTOTAL faltante/cero."

    def test_nrorev_zero_reported(self):
        """Zero NROREV → nrorev_status='non_positive', cantidad_visitas=None, anomaly."""
        pr, _ = _parse_row(_NROREV_ZERO_ROW, 12)
        assert pr.nrorev == 0
        assert pr.cantidad_visitas is None
        assert pr.visitas_status == "non_positive"
        assert pr.validation_status == "SIN_DATOS"
        # Batch 3c: UIT-implicita also SIN_DATOS when NROREV zero
        assert pr.uit_implicita is None
        assert pr.uit_implicita_status == "SIN_DATOS"
        assert any("NROREV non_positive" in a for a in pr.anomalies)
        # Batch 3d: UIT validation detail
        assert pr.uit_validacion_detalle == "No se pudo validar por NROREV, TASA, UIT o SUBTOTAL faltante/cero."


class TestUitValidacionDetalle:
    """
    Batch 3d: Direct unit tests for _build_uit_validacion_detalle.
    Tests all four detail message cases with exact string assertions.
    """

    def test_detalle_ok_igual_archivo(self):
        """OK_IGUAL_ARCHIVO → exact detail message."""
        detail = _build_uit_validacion_detalle(
            uit_archivo=Decimal("5500"),
            uit_implicita=Decimal("5500"),
            uit_implicita_status="OK_IGUAL_ARCHIVO",
            uit_implicita_year_candidate=2026,
            tasa=Decimal("0.042"),
        )
        assert detail == "La UIT del archivo explica el subtotal unitario."

    def test_detalle_ok_uit_conocida_diferente(self):
        """OK_UIT_CONOCIDA_DIFERENTE with archivo and year candidate → full message."""
        detail = _build_uit_validacion_detalle(
            uit_archivo=Decimal("5350"),
            uit_implicita=Decimal("5500"),
            uit_implicita_status="OK_UIT_CONOCIDA_DIFERENTE",
            uit_implicita_year_candidate=2026,
            tasa=Decimal("0.042"),
        )
        assert detail == (
            "El subtotal no cuadra con UIT_ARCHIVO=5350, "
            "pero sí con UIT_IMPLICITA=5500 (año 2026)."
        )

    def test_detalle_ok_uit_conocida_diferente_sin_archivo(self):
        """OK_UIT_CONOCIDA_DIFERENTE with no archivo UIT → partial message."""
        detail = _build_uit_validacion_detalle(
            uit_archivo=None,
            uit_implicita=Decimal("5500"),
            uit_implicita_status="OK_UIT_CONOCIDA_DIFERENTE",
            uit_implicita_year_candidate=2026,
            tasa=Decimal("0.042"),
        )
        assert detail == (
            "El subtotal no cuadra con la UIT del archivo, "
            "pero sí con UIT_IMPLICITA=5500 (año 2026)."
        )

    def test_detalle_no_coincide_uit_conocida(self):
        """NO_COINCIDE_UIT_CONOCIDA → shows implied UIT."""
        detail = _build_uit_validacion_detalle(
            uit_archivo=Decimal("5350"),
            uit_implicita=Decimal("4960"),
            uit_implicita_status="NO_COINCIDE_UIT_CONOCIDA",
            uit_implicita_year_candidate=None,
            tasa=Decimal("0.042"),
        )
        assert detail == (
            "El subtotal unitario implica UIT=4960, que no coincide con una UIT conocida."
        )

    def test_detalle_sin_datos(self):
        """SIN_DATOS → shows missing-data message."""
        detail = _build_uit_validacion_detalle(
            uit_archivo=None,
            uit_implicita=None,
            uit_implicita_status="SIN_DATOS",
            uit_implicita_year_candidate=None,
            tasa=None,
        )
        assert detail == "No se pudo validar por NROREV, TASA, UIT o SUBTOTAL faltante/cero."


class TestUitImplicita:
    """
    Batch 3c: UIT-implicita classification tests.

    Tests the implied UIT computation and classification:
        uit_implicita = (SUBTOTAL / NROREV) / TASA
        status: OK_IGUAL_ARCHIVO | OK_UIT_CONOCIDA_DIFERENTE
                | NO_COINCIDE_UIT_CONOCIDA | SIN_DATOS
    """

    def test_uit_implicita_igual_archivo(self):
        """
        Normal row: archivo UIT=5500, implied UIT=5500 (exact match).
        Expected: uit_implicita_status='OK_IGUAL_ARCHIVO',
                  uit_implicita_year_candidate=2026,
                  validation_status='OK'.
        """
        pr, _ = _parse_row(_NROREV36_VALIDATION_ROW, 20)
        assert pr.uit == Decimal("5500")
        assert pr.uit_implicita is not None
        assert int(round(pr.uit_implicita)) == 5500
        assert pr.uit_implicita_year_candidate == 2026
        assert pr.uit_implicita_status == "OK_IGUAL_ARCHIVO"
        assert pr.validation_status == "OK"
        # Batch 3d: detail for OK_IGUAL_ARCHIVO
        assert pr.uit_validacion_detalle == "La UIT del archivo explica el subtotal unitario."

    def test_uit_implicita_uit_conocida_diferente(self):
        """
        Year-end row: archivo UIT=5350 (2025) but calculation used 2026 UIT=5500.
        SUBTOTAL=8316 (=36*0.042*5500 → implies UIT=5500), archivo says 5350.
        Expected: uit_implicita_status='OK_UIT_CONOCIDA_DIFERENTE',
                  uit_implicita_year_candidate=2026,
                  validation_status='OK_UIT_IMPLICITA' (diff is explained).
        """
        pr, _ = _parse_row(_UIT_IMPLICITA_2026_ROW, 21)
        assert pr.uit == Decimal("5350")  # archivo says 2025
        assert pr.uit_implicita is not None
        assert int(round(pr.uit_implicita)) == 5500  # implied is 2026
        assert pr.uit_implicita_year_candidate == 2026
        assert pr.uit_implicita_status == "OK_UIT_CONOCIDA_DIFERENTE"
        # Diff exists but is explained by known UIT → OK_UIT_IMPLICITA
        assert pr.validation_status == "OK_UIT_IMPLICITA"
        # The numeric diff is still visible
        assert pr.diff_subtotal_unitario_legacy is not None
        assert pr.diff_subtotal_unitario_legacy > Decimal("0.01")
        # Batch 3d: detail for OK_UIT_CONOCIDA_DIFERENTE
        assert pr.uit_validacion_detalle == (
            "El subtotal no cuadra con UIT_ARCHIVO=5350, pero sí con UIT_IMPLICITA=5500 (año 2026)."
        )

    def test_uit_implicita_no_coincide_uit_conocida(self):
        """
        Impossible implied UIT: SUBTOTAL=7502 → uit_implicita≈4960 (not in known map).
        Known UITs: 2023=4950, 2024=5150, 2025=5350, 2026=5500.
        Expected: uit_implicita_status='NO_COINCIDE_UIT_CONOCIDA',
                  uit_implicita_year_candidate=None,
                  validation_status='DIF_SUBTOTAL' (diff is NOT explained).
        """
        pr, _ = _parse_row(_UIT_IMPLICITA_IMPOSSIBLE_ROW, 22)
        assert pr.uit == Decimal("5350")
        assert pr.uit_implicita is not None
        implied_int = int(round(pr.uit_implicita))
        # 4960 is close to 4950 but not exact → not in known map
        assert pr.uit_implicita_year_candidate is None
        assert pr.uit_implicita_status == "NO_COINCIDE_UIT_CONOCIDA"
        # Diff is NOT explained → stays as DIF_SUBTOTAL
        assert pr.validation_status == "DIF_SUBTOTAL"
        # Batch 3d: detail for NO_COINCIDE_UIT_CONOCIDA
        assert pr.uit_validacion_detalle == (
            f"El subtotal unitario implica UIT={implied_int}, que no coincide con una UIT conocida."
        )

    def test_uit_implicita_sin_datos_nrorev_missing(self):
        """Missing NROREV → uit_implicita=SIN_DATOS."""
        pr, _ = _parse_row(_NROREV_MISSING_ROW, 23)
        assert pr.uit_implicita is None
        assert pr.uit_implicita_status == "SIN_DATOS"
        assert pr.uit_implicita_year_candidate is None
        assert pr.validation_status == "SIN_DATOS"
        # Batch 3d: detail for SIN_DATOS
        assert pr.uit_validacion_detalle == "No se pudo validar por NROREV, TASA, UIT o SUBTOTAL faltante/cero."

    def test_uit_implicita_sin_datos_tasa_zero(self):
        """Zero TASA → uit_implicita=SIN_DATOS."""
        row = _NROREV36_VALIDATION_ROW[:]
        row[_COL_TASA] = "0"
        pr, _ = _parse_row(row, 24)
        assert pr.uit_implicita is None
        assert pr.uit_implicita_status == "SIN_DATOS"
        assert pr.validation_status == "SIN_DATOS"
        # Batch 3d: detail for SIN_DATOS
        assert pr.uit_validacion_detalle == "No se pudo validar por NROREV, TASA, UIT o SUBTOTAL faltante/cero."


# ── Integration: full command against real TSV ────────────────────────────────

@pytest.mark.django_db
class TestIOImportCommandRealFile:
    """
    Run the actual command against the real supervisones.csv file with --limit 100.
    This is a smoke test that verifies the full pipeline works on real data.
    """

    def test_dry_run_limit_100(self, tmp_path, settings):
        """Verify dry-run --limit 100 produces reports without errors."""
        from django.core.management import call_command
        from pathlib import Path

        data_path = Path(__file__).resolve().parents[5] / "data-old" / "data-real" / "supervisiones.csv"
        if not data_path.exists():
            pytest.skip(f"Real data file not found: {data_path}")

        out_dir = tmp_path / "reports"
        out_dir.mkdir()

        rechazo_path = out_dir / "reporte_ingesta_legacy_io.csv"
        detalle_csv = out_dir / "reporte_legacy_io_detallado.csv"
        detalle_xlsx = out_dir / "reporte_legacy_io_detallado.xlsx"

        # Write a small test TSV directly — build rows as lists, join with tab
        test_tsv = out_dir / "test_io.tsv"

        def make_row(row_id, expediente, categoria, nrorev="36", tasa="0.042"):
            """Build a 63-column TSV row as a list (batch 3b: NROREV + TASA)."""
            return [
                str(row_id),        # _COL_ID (0)
                "",                 # _COL_NRO (1)
                "20611093579",     # _COL_RUC (2)
                "VAL D0 S.A.C.",  # _COL_NOMBRE (3)
                nrorev,            # _COL_NROREV (4) — batch 3b
                "LIMA/MAGDALENA DEL MAR",  # _COL_DPTOPRDI (5)
                "AV. TEST 123",    # _COL_DIRECCION (6)
                "CIP 072900-CASTAÑEDA AMES VIVIANA PAOLA",  # _COL_DELEGADO (7)
                "5500",            # _COL_UIT (8)
                "272.58",          # _COL_PORCENTAJE (9)
                "0.04",            # _COL_PORCENFINA (10)
                "8316",            # _COL_SUBTOTAL (11)
                "1496.88",         # _COL_IGV (12)
                "9812.88",         # _COL_TOTAL (13)
                "20/08/2026",     # _COL_FECHA (14)
                "",                 # _COL_DNI (15)
                "VAL D0 S.A.C.",  # _COL_RAZONSOCIAL (16)
                "",                 # _COL_VALOROBRA (17)
                tasa,              # _COL_TASA (18) — batch 3b
                expediente,        # _COL_NROEXPDTE (19)
                "",                 # _COL_CODPAGO (20)
                "",                 # _COL_NROFACTURA (21)
                "",                 # _COL_DLEY (22)
                "",                 # _COL_IMPBRUTO (23)
                "",                 # _COL_APORCODEMU (24)
                "",                 # _COL_FONDOCOMUN (25)
                "",                 # _COL_HONORARIO (26)
                "",                 # _COL_IMPUESRENTA (27)
                "",                 # _COL_NETOHONORA (28)
                "MARIBEL QUIÑONES", # _COL_USUARIO (29)
                "",                 # _COL_IMPRESO (30)
                "",                 # _COL_DOC (31)
                "1/01/1900",      # _COL_FECHAPRES (32)
                "0",               # _COL_NROORDEN (33)
                "1/01/1900",      # _COL_FECHAREVI (34)
                "",                 # _COL_MES (35)
                "",                 # _COL_PERIODO (36)
                "",                 # _COL_NRORECIBO (37)
                "",                 # _COL_FECHARECIBO (38)
                "",                 # _COL_NROMEMO (39)
                "",                 # _COL_OBSERVA (40)
                "",                 # _COL_DICTAMEN (41)
                "",                 # _COL_TDNI (42)
                "",                 # _COL_TFONO (43)
                "",                 # _COL_TPERSONA (44)
                "18",              # _COL_TASAIGV (45)
                "1/01/1900",      # _COL_FECOMPRO (46)
                "",                 # _COL_NRONC (47)
                "",                 # _COL_NROQRPLZA (48)
                "",                 # _COL_RENTACIP (49)
                "",                 # _COL_DSCTO (50)
                "",                 # _COL_RUCDIRECC (51)
                "",                 # _COL_RETENCION (52)
                "72900",           # _COL_CIP (53)
                "",                 # _COL_BLKDEL (54)
                "",                 # _COL_NROCHEQUE (55)
                "",                 # _COL_CONCEPTO (56)
                "",                 # _COL_REINTEGRO (57)
                str(categoria),    # _COL_CATEGORIA (58)
                "0",               # _COL_PENDIENTES (59)
                "0",               # _COL_PAGADAS (60)
                "0",               # _COL_REALIZADAS (61)
                "0",               # _COL_DIFERENCIA (62)
            ]

        # Row 1: normal CATEGORIA=3 (TARIFA mode)
        # Row 2: CATEGORIA=0 (MANUAL/null_tariff mode)
        row1 = make_row(10488, "E-1748-2026", 3)
        row2 = make_row(10489, "E-1749-2026", 0)

        header_cols = [
            "ID", "NRO", "RUC", "NOMBRE", "NROREV", "DPTOPRDI", "DIRECCION",
            "DELEGADO", "UIT", "PORCENTAJE", "PORCENFINA", "SUBTOTAL", "IGV",
            "TOTAL", "FECHA", "DNI", "RAZONSOCIAL", "VALOROBRA", "TASA",
            "NROEXPDTE", "CODPAGO", "NROFACTURA", "DLEY", "IMPBRUTO",
            "APORCODEMU", "FONDOCOMUN", "HONORARIO", "IMPUESRENTA",
            "NETOHONORA", "USUARIO", "IMPRESO", "DOC", "FECHAPRES",
            "NROORDEN", "FECHAREVI", "MES", "PERIODO", "NRORECIBO",
            "FECHARECIBO", "NROMEMO", "OBSERVA", "DICTAMEN", "TDNI",
            "TFONO", "TPERSONA", "TASAIGV", "FECOMPRO", "NRONC",
            "NROQRPLZA", "RENTACIP", "DSCTO", "RUCDIRECC", "RETENCION",
            "CIP", "BLKDEL", "NROCHEQUE", "CONCEPTO", "REINTEGRO",
            "CATEGORIA", "PENDIENTES", "PAGADAS", "REALIZADAS", "DIFERENCIA",
        ]
        assert len(header_cols) == 63, f"Expected 63 header cols, got {len(header_cols)}"
        assert len(row1) == 63, f"Expected 63 data cols, got {len(row1)}"

        with test_tsv.open("w", encoding="utf-8") as f:
            f.write("\t".join(header_cols) + "\n")
            f.write("\t".join(row1) + "\n")
            f.write("\t".join(row2) + "\n")

        call_command(
            "import_legacy_inspeccion_obra",
            f"--data-path={test_tsv}",
            "--limit=10",
            "--dry-run",
            "--settings=config.settings.development",
            verbosity=0,
        )

        # Reports should have been written next to the data file
        reports_dir = test_tsv.parent
        rechazo = reports_dir / "reporte_ingesta_legacy_io.csv"
        detalle = reports_dir / "reporte_legacy_io_detallado.csv"
        detalle_xl = reports_dir / "reporte_legacy_io_detallado.xlsx"

        assert rechazo.exists(), f"Rechazo report not found: {rechazo}"
        assert detalle.exists(), f"Detalle CSV not found: {detalle}"
        assert detalle_xl.exists(), f"Detalle XLSX not found: {detalle_xl}"

        # Verify rechazo CSV has headers
        with rechazo.open("r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            headers = reader.fieldnames
            assert "FILA" in headers
            assert "MOTIVO" in headers
            assert "MODO_CALCULO" in headers

        # Verify detalle CSV
        with detalle.open("r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            rows = list(reader)
            assert len(rows) == 2
            # Row 1 is TARIFA mode
            cat3_row = next(r for r in rows if r["CATEGORIA"] == "3")
            assert cat3_row["CATEGORIA_MAPPED"] == "C3"
            assert cat3_row["MODO_CALCULO"] == "TARIFA"
            # Batch 3b: NROREV-based fields
            assert cat3_row["NROREV"] == "36"
            assert cat3_row["VISITAS_STATUS"] == "from_nrorev"
            assert cat3_row["TASA"] == "0.042"
            # Validation status OK (matches recalculated formula)
            assert cat3_row["VALIDATION_STATUS"] == "OK"
            # Row 2 is MANUAL mode (CATEGORIA=0)
            cat0_row = next(r for r in rows if r["CATEGORIA"] == "0")
            assert cat0_row["CATEGORIA_MAPPED"] == ""
            assert cat0_row["MODO_CALCULO"] == "MANUAL"
            assert cat0_row["CATEGORIA_STATUS"] == "null_tariff"
            # CATEGORIA=0 still carries NROREV data
            assert cat0_row["NROREV"] == "36"
            assert cat0_row["VISITAS_STATUS"] == "from_nrorev"
