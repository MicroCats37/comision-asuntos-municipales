from decimal import Decimal

import pytest
from django.core.management.base import CommandError

from modules.liquidaciones.management.commands.correct_legacy_edif_rh_h3 import (
    Command,
    distribute_bruto,
    values_for_bruto,
)


def test_distribute_bruto_preserves_parent_subtotal_with_rounding_residue():
    values = distribute_bruto(Decimal("100.00"))

    assert values == [Decimal("33.33"), Decimal("33.33"), Decimal("33.34")]
    assert sum(values) == Decimal("100.00")


def test_values_for_bruto_rounds_each_persisted_component():
    assert values_for_bruto(Decimal("33.34")) == {
        "imp_bruto": Decimal("33.34"),
        "renta_cip": Decimal("8.34"),
        "aporte_codemu": Decimal("1.67"),
        "fondo_comun": Decimal("3.33"),
        "neto_honorario": Decimal("20.00"),
    }


def test_command_rejects_unverified_subtotal_division():
    with pytest.raises(CommandError, match="Unsafe correction disabled"):
        Command().handle()
