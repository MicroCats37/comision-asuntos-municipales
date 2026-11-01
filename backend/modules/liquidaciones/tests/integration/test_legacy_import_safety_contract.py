"""Regression contracts for legacy importer safety guards."""
from pathlib import Path
import re
from importlib import import_module

import pytest


COMMANDS_DIR = Path(__file__).parents[2] / "management" / "commands"


def _source(command_name: str) -> str:
    return (COMMANDS_DIR / f"{command_name}.py").read_text(encoding="utf-8")


@pytest.mark.parametrize(
    "command_name",
    [
        "import_legacy_edificaciones",
        "import_legacy_habilitacion_urbana",
        "import_legacy_impacto_vial",
        "import_legacy_taludes",
    ],
)
def test_dry_run_does_not_create_system_or_legacy_users(command_name):
    source = _source(command_name)

    assert "if not self.dry_run:\n            system_user = _get_or_create_system_user()" in source
    assert re.search(r"usuario = None\s+if not self\.dry_run:\s+usuario_raw", source)


def test_hu_has_no_arbitrary_geographic_fallbacks():
    source = _source("import_legacy_habilitacion_urbana")

    assert "Municipalidad.objects.first()" not in source
    assert "UbigeoDistrito.objects.first()" not in source
    assert "distrito_id = None" in source


def test_mecanica_suelos_only_creates_project_under_apply():
    source = _source("import_legacy_mecanica_suelos")

    assert "Municipalidad.objects.first()" not in source
    assert source.index("if apply:") < source.index("legacy_proyecto = Proyecto.objects.create(")


@pytest.mark.parametrize(
    "command_name",
    [
        "import_legacy_edificaciones",
        "import_legacy_impacto_vial",
        "import_legacy_taludes",
    ],
)
def test_concrete_specialties_fail_instead_of_auto_filling(command_name):
    source = _source(command_name)

    assert 'if not especialidad_str or especialidad_str.strip().upper() != "TODAS":' in source
    assert 'raise ValueError(f"Especialidad no encontrada: {especialidad_str}")' in source
    assert 'raise ValueError("No hay tarifa vigente para la fecha")' in source


def test_impacto_vial_import_command_is_importable():
    module = import_module(
        "modules.liquidaciones.management.commands.import_legacy_impacto_vial"
    )

    assert module.Command
