from decimal import Decimal
from types import SimpleNamespace

from modules.liquidaciones.management.commands.restore_legacy_edif_rh_h3 import (
    normalize_cip,
    po_category,
)


def test_normalize_cip_matches_source_and_database_representations():
    assert normalize_cip("000123") == "123"
    assert normalize_cip(123) == "123"


def test_po_category_marks_total_explicito_as_non_universal_h3():
    porcentaje = SimpleNamespace(
        estrategia_cotizacion="TOTAL_EXPLICITO",
        porcentaje_tarifa=Decimal("0.0005"),
        cantidad_especialidades_habilitadas=3,
    )

    assert po_category(porcentaje) == "TOTAL_EXPLICITO"


def test_po_category_marks_single_specialty_unit_rate_as_fractional():
    porcentaje = SimpleNamespace(
        estrategia_cotizacion="NORMAL_SELECCIONADAS",
        porcentaje_tarifa=Decimal("0.0005"),
        cantidad_especialidades_habilitadas=1,
    )

    assert po_category(porcentaje) == "SINGLE_SPECIALTY_UNIT_RATE"
