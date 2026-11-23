from decimal import Decimal
from types import SimpleNamespace

from modules.liquidaciones.management.commands.reconcile_legacy_edif_rh import (
    classify_po,
    classify_rh,
    expected_rh_values,
)


def detail_for(values):
    return SimpleNamespace(**values)


def test_expected_h3_values_round_each_component_without_residual_distribution():
    values = expected_rh_values(Decimal("100.00"), 3)

    assert values == {
        "imp_bruto": Decimal("33.33"),
        "renta_cip": Decimal("8.33"),
        "aporte_codemu": Decimal("1.67"),
        "fondo_comun": Decimal("3.33"),
        "neto_honorario": Decimal("20.00"),
    }


def test_classify_rh_detects_three_persisted_rows_divided_by_four():
    divided_by_four = expected_rh_values(Decimal("100.00"), 4)
    status, expected = classify_rh(
        [detail_for(divided_by_four) for _ in range(3)],
        Decimal("100.00"),
        Decimal("0.01"),
    )

    assert status == "RH_DIVIDIDO_4"
    assert expected["imp_bruto"] == Decimal("33.33")


def test_classify_rh_detects_divided_by_four_when_a_persisted_row_is_missing():
    divided_by_four = expected_rh_values(Decimal("100.00"), 4)
    status, _ = classify_rh(
        [detail_for(divided_by_four) for _ in range(2)],
        Decimal("100.00"),
        Decimal("0.01"),
    )

    assert status == "RH_DIVIDIDO_4"


def test_classify_rh_uses_fixed_divisor_when_fourth_split_has_legacy_component_rounding():
    details = [
        detail_for(
            {
                "imp_bruto": Decimal("175.10"),
                "renta_cip": Decimal("43.78"),
                "aporte_codemu": Decimal("8.76"),
                "fondo_comun": Decimal("17.51"),
                "neto_honorario": Decimal("105.05"),
            }
        )
        for _ in range(3)
    ]

    status, _ = classify_rh(details, Decimal("700.42"), Decimal("0.01"))

    assert status == "RH_DIVIDIDO_4"


def test_classify_rh_distinguishes_missing_details_from_wrong_count():
    status, _ = classify_rh([], Decimal("100.00"), Decimal("0.01"))

    assert status == "RH_SIN_DETALLE"


def test_classify_po_accepts_h3_rate_without_legacy_snapshots():
    correct = SimpleNamespace(
        estrategia_cotizacion="NORMAL_SELECCIONADAS",
        cantidad_especialidades_habilitadas=None,
        porcentaje_tarifa=None,
        porcentaje_liquidacion=Decimal("0.0015"),
    )

    assert classify_po(correct) == "PO_CORRECTO"
    correct.porcentaje_liquidacion = Decimal("0.0020")
    assert classify_po(correct) == "PO_DISCREPANTE"
