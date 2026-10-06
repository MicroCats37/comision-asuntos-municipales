"""
Tests for LiquidacionRelacion code generator and relation key mapper helpers.

These are pure unit-level tests using pytest (no Django DB required for the
helpers themselves — they have no DB side effects).

Covers:
- Code format: LQG-YYYYMMDD-HHMMSS-XXXX pattern
- Code uniqueness across multiple generations
- Relation key mapping for all supported tipo_liquidacion values
- Relation key with tipo_tramite subtypes for EDIFICACION
- Error case for unsupported tipo_liquidacion
"""

import pytest
import re

from modules.liquidaciones.domain.services.core.liquidacion_general.liquidacion_relacion_codigo_helper import (
    generar_codigo_grupo,
    generar_codigo_grupo_con_reintento,
)
from modules.liquidaciones.domain.services.core.liquidacion_general.liquidacion_relacion_key_helper import (
    generar_relacion_key,
)


# ── Code Generator Tests ────────────────────────────────────────────────────

class TestGenerarCodigoGrupo:
    def test_codigo_formato_lqg_timestamp_hex(self):
        """
        WHEN: generar_codigo_grupo() is called
        THEN: it returns a string starting with 'LQG-' and matching the expected format
        """
        codigo = generar_codigo_grupo()

        assert codigo.startswith("LQG-"), f"Code should start with 'LQG-', got: {codigo}"

        parts = codigo.split("-")
        assert len(parts) == 4, f"Code should have 4 parts separated by '-', got: {codigo}"

        # YYYYMMDD
        assert len(parts[1]) == 8, f"Date part should be 8 chars, got: {parts[1]}"
        assert parts[1].isdigit(), f"Date part should be digits, got: {parts[1]}"

        # HHMMSS
        assert len(parts[2]) == 6, f"Time part should be 6 chars, got: {parts[2]}"
        assert parts[2].isdigit(), f"Time part should be digits, got: {parts[2]}"

        # XXXX hex suffix
        assert len(parts[3]) == 4, f"Suffix should be 4 chars, got: {parts[3]}"
        assert all(c in "0123456789ABCDEF" for c in parts[3]), (
            f"Suffix should be uppercase hex, got: {parts[3]}"
        )

    def test_codigo_timestamp_is_reasonable(self):
        """
        WHEN: generar_codigo_grupo() is called
        THEN: the embedded timestamp corresponds to a recent date
        """
        import re
        from datetime import datetime, timezone

        codigo = generar_codigo_grupo()
        match = re.match(r"LQG-(\d{8})-(\d{6})-([0-9A-F]{4})", codigo)
        assert match, f"Code format unexpected: {codigo}"

        date_str, time_str = match.groups()[0], match.groups()[1]
        dt = datetime.strptime(f"{date_str}{time_str}", "%Y%m%d%H%M%S")
        dt = dt.replace(tzinfo=timezone.utc)

        # Should not be more than 1 day in the past or future
        from datetime import timedelta

        now = datetime.now(timezone.utc)
        delta = abs((now - dt).total_seconds())
        assert delta < 86400, f"Embedded timestamp is too far from now: {dt}"

    def test_codigo_unico_entre_intentos(self):
        """
        WHEN: 100 codes are generated in a row
        THEN: all 100 are unique (no collisions in normal execution)
        """
        codigos = [generar_codigo_grupo() for _ in range(100)]
        assert len(set(codigos)) == 100, "All 100 codes should be unique"

    def test_codigo_no_flaky_por_segundo(self):
        """
        WHEN: two codes are generated in the same second
        THEN: they differ only in the hex suffix
        """
        import time

        c1 = generar_codigo_grupo()
        time.sleep(0.01)  # Small delay but same second
        c2 = generar_codigo_grupo()

        # They should differ at most in the suffix
        p1, p2 = c1.split("-"), c2.split("-")
        assert p1[1] == p2[1], "Date part should be same"
        assert p1[2] == p2[2], "Time part should be same"
        assert p1[3] != p2[3], "Suffixes should differ (and be unique)"


class TestGenerarCodigoGrupoConReintento:
    def test_retorna_codigo_valido(self):
        """
        WHEN: generar_codigo_grupo_con_reintento is called
        THEN: it returns a valid code and fue_reintentado flag
        """
        codigo, fue_reintentado = generar_codigo_grupo_con_reintento()

        assert codigo.startswith("LQG-"), f"Should be a valid LQG code: {codigo}"
        parts = codigo.split("-")
        assert len(parts) == 4
        assert isinstance(fue_reintentado, bool)

    def test_fue_reintentado_false_con_max_intentos_1(self):
        """
        WHEN: max_intentos=1 (default single attempt)
        THEN: fue_reintentado should be False
        """
        _, fue_reintentado = generar_codigo_grupo_con_reintento(max_intentos=1)
        assert fue_reintentado is False


# ── Relation Key Mapper Tests ────────────────────────────────────────────────


class TestGenerarRelacionKey:
    def test_edificacion_sin_subtipo_retorna_edificacion(self):
        """
        WHEN: tipo_liquidacion is EDIFICACION with no tipo_tramite
        THEN: relation key is the exact code 'EDIFICACION'
        """
        key = generar_relacion_key("EDIFICACION")
        assert key == "EDIFICACION"

    def test_edificacion_con_obra_nueva_retorna_edificacion_obra_nueva(self):
        """
        WHEN: tipo_liquidacion is EDIFICACION with tipo_tramite OBRA_NUEVA
        THEN: relation key is 'EDIFICACION-OBRA_NUEVA' (full tipo_tramite preserved)
        """
        key = generar_relacion_key("EDIFICACION", tipo_tramite="OBRA_NUEVA")
        assert key == "EDIFICACION-OBRA_NUEVA"

    def test_edificacion_con_demolicion_retorna_edificacion_demolicion(self):
        """
        WHEN: tipo_liquidacion is EDIFICACION with tipo_tramite DEMOLICION
        THEN: relation key is 'EDIFICACION-DEMOLICION'
        """
        key = generar_relacion_key("EDIFICACION", tipo_tramite="DEMOLICION")
        assert key == "EDIFICACION-DEMOLICION"

    def test_edificacion_con_ampliacion_retorna_edificacion_ampliacion(self):
        """
        WHEN: tipo_liquidacion is EDIFICACION with tipo_tramite AMPLIACION
        THEN: relation key is 'EDIFICACION-AMPLIACION'
        """
        key = generar_relacion_key("EDIFICACION", tipo_tramite="AMPLIACION")
        assert key == "EDIFICACION-AMPLIACION"

    def test_edificacion_con_remodelacion_retorna_edificacion_remodelacion(self):
        """
        WHEN: tipo_liquidacion is EDIFICACION with tipo_tramite REMODELACION
        THEN: relation key is 'EDIFICACION-REMODELACION'
        """
        key = generar_relacion_key("EDIFICACION", tipo_tramite="REMODELACION")
        assert key == "EDIFICACION-REMODELACION"

    def test_edificacion_con_modificacion_licencia_retorna_edificacion_modificacion_licencia(self):
        """
        WHEN: tipo_liquidacion is EDIFICACION with tipo_tramite MODIFICACION_LICENCIA
        THEN: relation key is 'EDIFICACION-MODIFICACION_LICENCIA' (full tipo_tramite preserved)
        """
        key = generar_relacion_key("EDIFICACION", tipo_tramite="MODIFICACION_LICENCIA")
        assert key == "EDIFICACION-MODIFICACION_LICENCIA"

    def test_edificacion_con_variacion_proyecto_aprobado_retorna_edificacion_variacion_proyecto_aprobado(self):
        """
        WHEN: tipo_liquidacion is EDIFICACION with tipo_tramite VARIACION_PROYECTO_APROBADO
        THEN: relation key is 'EDIFICACION-VARIACION_PROYECTO_APROBADO' (full tipo_tramite preserved)
        """
        key = generar_relacion_key("EDIFICACION", tipo_tramite="VARIACION_PROYECTO_APROBADO")
        assert key == "EDIFICACION-VARIACION_PROYECTO_APROBADO"

    def test_edificacion_con_reintegro_retorna_edificacion_reintegro(self):
        """
        WHEN: tipo_liquidacion is EDIFICACION with tipo_tramite REINTEGRO
        THEN: relation key is 'EDIFICACION-REINTEGRO'
        """
        key = generar_relacion_key("EDIFICACION", tipo_tramite="REINTEGRO")
        assert key == "EDIFICACION-REINTEGRO"

    def test_edificacion_con_proyecto_con_plantas_tipicas_retorna_edificacion_proyecto_con_plantas_tipicas(self):
        """
        WHEN: tipo_liquidacion is EDIFICACION with tipo_tramite PROYECTO_CON_PLANTAS_TIPICAS
        THEN: relation key is 'EDIFICACION-PROYECTO_CON_PLANTAS_TIPICAS' (full tipo_tramite preserved)
        """
        key = generar_relacion_key("EDIFICACION", tipo_tramite="PROYECTO_CON_PLANTAS_TIPICAS")
        assert key == "EDIFICACION-PROYECTO_CON_PLANTAS_TIPICAS"

    def test_habilitacion_urbana_retorna_habilitacion_urbana(self):
        """
        WHEN: tipo_liquidacion is HABILITACION_URBANA
        THEN: relation key is 'HABILITACION_URBANA' (full catalog code)
        """
        key = generar_relacion_key("HABILITACION_URBANA")
        assert key == "HABILITACION_URBANA"

    def test_mecanica_suelos_retorna_mecanica_suelos(self):
        """
        WHEN: tipo_liquidacion is MECANICA_SUELOS
        THEN: relation key is 'MECANICA_SUELOS' (full catalog code)
        """
        key = generar_relacion_key("MECANICA_SUELOS")
        assert key == "MECANICA_SUELOS"

    def test_taludes_retorna_taludes(self):
        """
        WHEN: tipo_liquidacion is TALUDES
        THEN: relation key is 'TALUDES'
        """
        key = generar_relacion_key("TALUDES")
        assert key == "TALUDES"

    def test_impacto_vial_retorna_impacto_vial(self):
        """
        WHEN: tipo_liquidacion is IMPACTO_VIAL
        THEN: relation key is 'IMPACTO_VIAL'
        """
        key = generar_relacion_key("IMPACTO_VIAL")
        assert key == "IMPACTO_VIAL"

    def test_inspeccion_obra_raises_error(self):
        """
        WHEN: tipo_liquidacion is INSPECCION_OBRA (unsupported)
        THEN: ValueError is raised
        """
        with pytest.raises(ValueError) as exc_info:
            generar_relacion_key("INSPECCION_OBRA")

        assert "INSPECCION_OBRA" in str(exc_info.value)
        assert "not supported" in str(exc_info.value)

    def test_unknown_tipo_liquidacion_raises_error(self):
        """
        WHEN: tipo_liquidacion is an unknown value
        THEN: ValueError is raised
        """
        with pytest.raises(ValueError) as exc_info:
            generar_relacion_key("DESCONOCIDO")

        assert "DESCONOCIDO" in str(exc_info.value)

    def test_relacion_key_no_revision_duplication(self):
        """
        WHEN: relation keys are generated for the same tipo in multiple calls
        THEN: they are identical (no revision embedded)
        """
        key1 = generar_relacion_key("HABILITACION_URBANA")
        key2 = generar_relacion_key("HABILITACION_URBANA")
        assert key1 == key2, "Relation key should not vary between calls"

        key3 = generar_relacion_key("EDIFICACION", tipo_tramite="OBRA_NUEVA")
        key4 = generar_relacion_key("EDIFICACION", tipo_tramite="OBRA_NUEVA")
        assert key3 == key4, "Relation key with subtype should be stable"

    def test_relacion_key_diferentes_tipos_son_diferentes(self):
        """
        WHEN: relation keys are generated for different tipos
        THEN: they are all distinct
        """
        keys = {
            generar_relacion_key("EDIFICACION"),
            generar_relacion_key("EDIFICACION", tipo_tramite="OBRA_NUEVA"),
            generar_relacion_key("EDIFICACION", tipo_tramite="DEMOLICION"),
            generar_relacion_key("HABILITACION_URBANA"),
            generar_relacion_key("MECANICA_SUELOS"),
            generar_relacion_key("TALUDES"),
            generar_relacion_key("IMPACTO_VIAL"),
        }
        assert len(keys) == 7, f"All 7 keys should be distinct, got {len(keys)}: {keys}"
