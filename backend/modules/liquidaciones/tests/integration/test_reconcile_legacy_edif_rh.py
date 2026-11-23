from decimal import Decimal
from types import SimpleNamespace

from modules.liquidaciones.management.commands.reconcile_legacy_edif_rh import (
    expected_bruto,
    expected_rh_values,
    h3_existing_mismatch_parents,
    po_allocation_classification,
    rh_classification,
    summarize_parent_counts,
)


def detail_for(values):
    return SimpleNamespace(**values)


def test_expected_values_use_persisted_po_detail_subtotal_without_a_divisor():
    assert expected_rh_values(Decimal("100.00")) == {
        "imp_bruto": Decimal("100.00"),
        "renta_cip": Decimal("25.00"),
        "aporte_codemu": Decimal("5.00"),
        "fondo_comun": Decimal("10.00"),
        "neto_honorario": Decimal("60.00"),
    }


def test_three_persisted_po_details_are_the_allocation_source():
    porcentaje = SimpleNamespace(
        estrategia_cotizacion="TARIFA_HABILITADAS_PARTICIPANTES",
        cantidad_especialidades_habilitadas=3,
    )

    assert po_allocation_classification(porcentaje, 3) == "PO_TRES_DETALLES_PERSISTIDOS"


def test_total_explicito_uses_the_persisted_detail_count_not_the_rh_count():
    porcentaje = SimpleNamespace(
        estrategia_cotizacion="TOTAL_EXPLICITO",
        cantidad_especialidades_habilitadas=3,
    )

    assert (
        po_allocation_classification(porcentaje, 3) == "PO_TOTAL_EXPLICITO_POR_DETALLE"
    )


def test_exclusive_single_specialty_assigns_its_full_po_detail_to_rh():
    porcentaje = SimpleNamespace(
        estrategia_cotizacion="NORMAL_SELECCIONADAS",
        cantidad_especialidades_habilitadas=3,
    )

    assert po_allocation_classification(porcentaje, 1) == "PO_EXCLUSIVO_ESPECIALIDAD"


def test_single_unit_rate_assigns_the_parent_total_to_its_specialty():
    liquidacion = SimpleNamespace(sub_total=Decimal("180.86"))
    detail = SimpleNamespace(
        tarifa_aplicada_id="tarifa-05", porcentaje_aplicado=Decimal("0.0005"), subtotal=Decimal("60.29")
    )

    assert expected_bruto(liquidacion, [detail], detail) == Decimal("180.86")


def test_rh_comparison_marks_a_quarter_split_as_a_persisted_detail_discrepancy():
    actual = detail_for(expected_rh_values(Decimal("25.00")))

    assert (
        rh_classification(
            actual, expected_rh_values(Decimal("100.00")), Decimal("0.01")
        )
        == "RH_DISCREPANTE_PO_DETALLE"
    )


def test_parent_summary_counts_unique_parents_not_specialty_lines():
    parent_records = [
        {"numero": 10, "has_rh": True},
        {"numero": 11, "has_rh": True},
        {"numero": 12, "has_rh": False},
    ]
    rows = [
        {"numero": 10, "rh_classification": "RH_DISCREPANTE_PO_DETALLE"},
        {
            "numero": 10,
            "rh_classification": "RH_DISCREPANTE_PO_DETALLE_DUPLICADO_ESPECIALIDAD",
        },
        {"numero": 11, "rh_classification": "RH_FALTANTE_PARA_PO_DETALLE"},
        {"numero": 12, "rh_classification": "RH_FALTANTE_PARA_PO_DETALLE"},
    ]

    assert summarize_parent_counts(parent_records, rows) == {
        "legacy_edif_post_cutover_parents": 3,
        "parents_with_any_rh": 2,
        "parents_without_rh": 1,
        "parents_with_existing_rh_mismatches": 1,
        "parents_with_missing_po_to_rh_specialties": 2,
    }


def test_h3_existing_mismatch_report_has_one_row_per_parent():
    rows = [
        {
            "numero": 20,
            "po_detail_count": 3,
            "rh_classification": "RH_DISCREPANTE_PO_DETALLE",
        },
        {
            "numero": 20,
            "po_detail_count": 3,
            "rh_classification": "RH_DISCREPANTE_PO_DETALLE_DUPLICADO_ESPECIALIDAD",
        },
        {
            "numero": 21,
            "po_detail_count": 2,
            "rh_classification": "RH_DISCREPANTE_PO_DETALLE",
        },
    ]

    assert h3_existing_mismatch_parents(rows) == [rows[0]]
