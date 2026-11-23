from modules.liquidaciones.management.commands.report_legacy_edif_rh_gaps import (
    summarize_year_counts,
)


def test_summarize_year_counts_groups_legacy_edif_with_and_without_rh():
    assert summarize_year_counts(
        [(2025, True), (2025, False), (2026, False), (None, False)]
    ) == [
        {"year": 2025, "liquidaciones_edif": 2, "sin_rh_migrado": 1},
        {"year": 2026, "liquidaciones_edif": 1, "sin_rh_migrado": 1},
        {"year": None, "liquidaciones_edif": 1, "sin_rh_migrado": 1},
    ]
