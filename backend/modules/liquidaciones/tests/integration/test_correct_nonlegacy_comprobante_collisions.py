from types import SimpleNamespace

from modules.liquidaciones.management.commands.correct_nonlegacy_comprobante_collisions import (
    COLLISIONS,
    has_legacy_identity,
)


def test_collision_manifest_is_closed_and_unique():
    assert len(COLLISIONS) == 31
    assert sum(item.tipo == "IO" for item in COLLISIONS) == 30
    assert sum(item.tipo == "EDIF" for item in COLLISIONS) == 1
    assert len({item.comprobante_id for item in COLLISIONS}) == len(COLLISIONS)


def test_legacy_identity_detects_untouched_contamination_even_if_amount_changed():
    item = next(item for item in COLLISIONS if item.tipo == "IO" and item.numero == 23)
    comprobante = SimpleNamespace(
        serie=item.legacy_serie,
        numero=item.legacy_numero,
        fecha_emision=item.legacy_fecha,
        monto=item.legacy_monto + 1,
    )

    assert has_legacy_identity(comprobante, item)


def test_legacy_identity_preserves_manually_corrected_receipt():
    item = next(item for item in COLLISIONS if item.tipo == "IO" and item.numero == 23)
    comprobante = SimpleNamespace(
        serie="F004",
        numero="00099999",
        fecha_emision=item.legacy_fecha.replace(year=2026),
        monto=item.legacy_monto,
    )

    assert not has_legacy_identity(comprobante, item)


def test_legacy_date_remains_contaminated_even_if_invoice_identity_changed():
    item = next(item for item in COLLISIONS if item.tipo == "IO" and item.numero == 23)
    comprobante = SimpleNamespace(
        serie="F999",
        numero="00099999",
        fecha_emision=item.legacy_fecha,
        monto=item.legacy_monto,
    )

    assert has_legacy_identity(comprobante, item)
