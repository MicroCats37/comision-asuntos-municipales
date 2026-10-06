"""
Unit tests for get_liquidacion_tipo_estrategia_rh classification helper.

Tests the classification of TipoLiquidacion.codigo values into RH extraction
strategies: ``detail`` (PO) vs ``direct`` (M2), and the explicit error
for unsupported types.
"""
import pytest

from modules.finanzas.domain.services.finanzas_core_service import (
    get_liquidacion_tipo_estrategia_rh,
    TIPO_LIQUIDACION_ESTRATEGIA_RH_DETAIL,
    TIPO_LIQUIDACION_ESTRATEGIA_RH_DIRECT,
    PO_TIPO_LIQUIDACION_CODES,
    M2_TIPO_LIQUIDACION_CODES,
)


class TestGetLiquidacionTipoEstrategiaRh:
    """Tests for the RH tipo-liquidacion classification helper."""

    @pytest.mark.parametrize("codigo", sorted(PO_TIPO_LIQUIDACION_CODES))
    def test_po_codes_return_detail_strategy(self, codigo):
        """PO tipo codes (EDIFICACION, IMPACTO_VIAL, TALUDES) → strategy detail."""
        result = get_liquidacion_tipo_estrategia_rh(codigo)
        assert result == TIPO_LIQUIDACION_ESTRATEGIA_RH_DETAIL

    @pytest.mark.parametrize("codigo", sorted(M2_TIPO_LIQUIDACION_CODES))
    def test_m2_codes_return_direct_strategy(self, codigo):
        """M2 tipo codes (HABILITACION_URBANA, MECANICA_SUELOS) → strategy direct."""
        result = get_liquidacion_tipo_estrategia_rh(codigo)
        assert result == TIPO_LIQUIDACION_ESTRATEGIA_RH_DIRECT

    def test_unsupported_code_raises_value_error(self):
        """Unsupported tipo code raises ValueError with a clear message."""
        with pytest.raises(ValueError) as exc_info:
            get_liquidacion_tipo_estrategia_rh("INSPECCION_OBRA")
        assert "INSPECCION_OBRA" in str(exc_info.value)
        assert "no soportado" in str(exc_info.value)

    def test_unsupported_code_raises_value_error_with_detail_codes_in_message(self):
        """Error message includes the supported detail and direct codes."""
        with pytest.raises(ValueError) as exc_info:
            get_liquidacion_tipo_estrategia_rh("INSPECCION_OBRA")
        msg = str(exc_info.value)
        assert "EDIFICACION" in msg
        assert "HABILITACION_URBANA" in msg

    def test_empty_string_raises_value_error(self):
        """Empty string is not a valid tipo code."""
        with pytest.raises(ValueError):
            get_liquidacion_tipo_estrategia_rh("")

    def test_arbitrary_string_raises_value_error(self):
        """Arbitrary string raises ValueError, not silently classified."""
        with pytest.raises(ValueError):
            get_liquidacion_tipo_estrategia_rh("FOO_BAR")

    def test_return_value_is_string(self):
        """Return value is always a string constant, usable in downstream comparisons."""
        for codigo in PO_TIPO_LIQUIDACION_CODES | M2_TIPO_LIQUIDACION_CODES:
            result = get_liquidacion_tipo_estrategia_rh(codigo)
            assert isinstance(result, str)

    def test_constants_are_distinct(self):
        """Detail and direct strategy constants must be distinct."""
        assert (
            TIPO_LIQUIDACION_ESTRATEGIA_RH_DETAIL
            != TIPO_LIQUIDACION_ESTRATEGIA_RH_DIRECT
        )
