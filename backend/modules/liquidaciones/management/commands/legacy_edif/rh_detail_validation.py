"""
EDIF legacy helpers — source-value extraction and compare helpers for
DetalleHonorarioDelegado rows validated against EDIF_ALL.csv.
"""

from decimal import Decimal

from modules.finanzas.domain.models.detalle_honorario_delegado import (
    DetalleHonorarioDelegado,
)

from .columns import APORTE_CODEMU, FONDO_COMUN, IMP_BRUTO, NETO_HONORARIO, RENTA_CIP
from .parsers import money, money_diff


def extract_source_values(csv_row: dict) -> dict[str, Decimal]:
    """
    Extract monetary fields for DetalleHonorarioDelegado from an EDIF_ALL.csv row.

    Args:
        csv_row: dict with "raw" key containing the split CSV row (list[str])

    Returns:
        dict mapping field_name -> Decimal value:
            imp_bruto, renta_cip, aporte_codemu, fondo_comun, neto_honorario
    """
    raw = csv_row["raw"]
    return {
        "imp_bruto": money(raw[IMP_BRUTO] if len(raw) > IMP_BRUTO else None),
        "renta_cip": money(raw[RENTA_CIP] if len(raw) > RENTA_CIP else None),
        "aporte_codemu": money(raw[APORTE_CODEMU] if len(raw) > APORTE_CODEMU else None),
        "fondo_comun": money(raw[FONDO_COMUN] if len(raw) > FONDO_COMUN else None),
        "neto_honorario": money(raw[NETO_HONORARIO] if len(raw) > NETO_HONORARIO else None),
    }


def build_source_compare_row(
    edificacion, liquidacion, detail: DetalleHonorarioDelegado, expected: dict
) -> dict:
    """
    Build a comparison row between DB values and source CSV values.

    Args:
        edificacion: LiquidacionEdificacion instance
        liquidacion: Liquidacion instance
        detail: DetalleHonorarioDelegado instance
        expected: dict from extract_source_values()

    Returns:
        dict with comparison fields: status, numero, liquidacion_id, expediente,
        detalle_id, especialidad, delegado, actual_*, source_*, diff_*, bad_fields
    """
    ld = detail.liquidacion_delegado
    actual = {
        "imp_bruto": money(detail.imp_bruto),
        "renta_cip": money(detail.renta_cip),
        "aporte_codemu": money(detail.aporte_codemu),
        "fondo_comun": money(detail.fondo_comun),
        "neto_honorario": money(detail.neto_honorario),
    }
    diffs = {name: abs(actual[name] - expected[name]) for name in actual}
    bad_fields = [name for name, value in diffs.items() if value > Decimal("0.00")]
    return {
        "status": "OK" if not bad_fields else "MISMATCH",
        "numero": edificacion.numero,
        "liquidacion_id": str(liquidacion.id),
        "expediente": liquidacion.expediente or "",
        "detalle_id": str(detail.id),
        "especialidad": getattr(ld.especialidad_revision, "nombre", "") or "",
        "delegado": getattr(getattr(ld.delegado, "perfil_ingeniero", None), "nombre_completo", "") or "",
        "actual_imp_bruto": str(actual["imp_bruto"]),
        "source_imp_bruto": str(expected["imp_bruto"]),
        "diff_imp_bruto": str(diffs["imp_bruto"]),
        "actual_renta_cip": str(actual["renta_cip"]),
        "source_renta_cip": str(expected["renta_cip"]),
        "diff_renta_cip": str(diffs["renta_cip"]),
        "actual_aporte_codemu": str(actual["aporte_codemu"]),
        "source_aporte_codemu": str(expected["aporte_codemu"]),
        "diff_aporte_codemu": str(diffs["aporte_codemu"]),
        "actual_fondo_comun": str(actual["fondo_comun"]),
        "source_fondo_comun": str(expected["fondo_comun"]),
        "diff_fondo_comun": str(diffs["fondo_comun"]),
        "actual_neto_honorario": str(actual["neto_honorario"]),
        "source_neto_honorario": str(expected["neto_honorario"]),
        "diff_neto_honorario": str(diffs["neto_honorario"]),
        "bad_fields": ",".join(bad_fields),
    }


def source_needs_fix(detail: DetalleHonorarioDelegado, expected: dict, tolerance: Decimal) -> bool:
    """
    Check whether any monetary field on a detail differs from the source CSV value
    beyond the given tolerance.

    Args:
        detail: DetalleHonorarioDelegado instance
        expected: dict from extract_source_values()
        tolerance: Decimal tolerance threshold

    Returns:
        True if any field exceeds tolerance.
    """
    return any(
        money_diff(getattr(detail, field_name), expected_value) > tolerance
        for field_name, expected_value in {
            "imp_bruto": expected["imp_bruto"],
            "renta_cip": expected["renta_cip"],
            "aporte_codemu": expected["aporte_codemu"],
            "fondo_comun": expected["fondo_comun"],
            "neto_honorario": expected["neto_honorario"],
        }.items()
    )
