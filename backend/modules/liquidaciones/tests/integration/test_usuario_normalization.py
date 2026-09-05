"""
Unit tests for the _normalize_usuario_to_username helper function.

Tests the username normalization logic used in the legacy edificaciones import:
- Strip accents
- Lowercase
- Whitespace to dot
- Remove invalid characters
"""
import pytest

from modules.liquidaciones.management.commands.import_legacy_edificaciones import (
    _normalize_usuario_to_username,
)


class TestNormalizeUsuarioToUsername:
    """Tests for _normalize_usuario_to_username helper."""

    def test_basic_name(self):
        """Simple two-part name becomes dot-separated lowercase."""
        assert _normalize_usuario_to_username("SANDRA OJEDA") == "sandra.ojeda"

    def test_name_with_accent(self):
        """Name with accents gets normalized."""
        assert _normalize_usuario_to_username("MARIBEL QUIÑONES") == "maribel.quinones"

    def test_name_with_special_chars(self):
        """Name with special characters only keeps valid ones."""
        # The function removes invalid chars
        result = _normalize_usuario_to_username("JOAN DOE-SMITH")
        assert result == "joan.doe-smith"

    def test_none_input(self):
        """None input returns None."""
        assert _normalize_usuario_to_username(None) is None

    def test_empty_string(self):
        """Empty string returns None."""
        assert _normalize_usuario_to_username("") is None
        assert _normalize_usuario_to_username("   ") is None

    def test_null_string(self):
        """NULL string returns None."""
        assert _normalize_usuario_to_username("NULL") is None
        assert _normalize_usuario_to_username("null") is None

    def test_single_name(self):
        """Single name without space."""
        result = _normalize_usuario_to_username("SANDRA")
        assert result == "sandra"

    def test_multiple_spaces(self):
        """Multiple spaces become single dot."""
        result = _normalize_usuario_to_username("SANDRA  OJEDA")
        assert result == "sandra.ojeda"

    def test_leading_trailing_spaces(self):
        """Leading/trailing spaces are stripped."""
        result = _normalize_usuario_to_username("  SANDRA OJEDA  ")
        assert result == "sandra.ojeda"

    def test_leading_trailing_dots_removed(self):
        """Leading/trailing dots, underscores, hyphens are removed."""
        result = _normalize_usuario_to_username(".sandra.ojeda.")
        assert result == "sandra.ojeda"

    def test_uppercase_with_numbers(self):
        """Name with numbers is preserved."""
        result = _normalize_usuario_to_username("JUAN 123 SANCHEZ")
        assert result == "juan.123.sanchez"
