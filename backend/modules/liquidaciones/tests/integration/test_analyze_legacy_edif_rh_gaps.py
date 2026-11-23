from modules.liquidaciones.management.commands.analyze_legacy_edif_rh_gaps import gap_cause


def test_gap_cause_distinguishes_absent_malformed_and_excluded_source_rows():
    assert gap_cause({}, {}, {}, 1) == "SOURCE_ABSENT"
    assert gap_cause({}, {2: [{}]}, {}, 2) == "SOURCE_MALFORMED"
    assert gap_cause({3: [object()]}, {}, {3: ["sin_liquidacion"]}, 3) == "SOURCE_EXCLUDED:sin_liquidacion"
