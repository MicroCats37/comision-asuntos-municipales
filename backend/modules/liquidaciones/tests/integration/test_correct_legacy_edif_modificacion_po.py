from modules.liquidaciones.management.commands.correct_legacy_edif_modificacion_po import (
    is_modificacion_licencia,
)


def test_modificacion_label_accepts_legacy_variants():
    assert is_modificacion_licencia("MODIFICACION DE LICENCIA DE INST. SANITARIAS")
    assert is_modificacion_licencia("MODIF. DE LICENCIA - ESTRUCTURAS")


def test_modificacion_label_never_reclassifies_reintegros():
    assert not is_modificacion_licencia(
        "REINTEGRO A LA MODIFICACION DE LICENCIA DE INST. SANITARIAS"
    )


def test_modificacion_label_keeps_specialty_specific_plantas_tipicas():
    assert is_modificacion_licencia(
        "MODIFICACION DE LICENCIA DE ESTRUCTURAS - PLANTAS TIPICAS"
    )
