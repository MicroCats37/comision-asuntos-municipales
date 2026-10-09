"""
Legacy EDIF helpers — modular support for EDIF_ALL.csv validation and curation.

Modules
-------
columns              — EDIF_ALL.csv column index constants (all fields).
delegado_columns     — DELEGADO slot column index constants + specialty maps.
parsers             — Monetary, date, int, month, documento, and specialty parsing utilities.
rh_detail_validation — DetalleHonorarioDelegado source-value extraction and compare.
delegado_curation   — LiquidacionDelegado field curation from DELEGADO CSV slots.
reports             — CSV output and row formatting.

Example
-------
>>> from legacy_edif.parsers import money, load_source_csv
>>> from legacy_edif.columns import IMP_BRUTO, COL_RUC
"""

from .delegado_columns import (
    DELEGADO_SLOT_COLUMNS,
    SLOT_SPECIALTY_DB_MAP,
    VALID_DICTAMEN_VALUES,
    _SLOT_SPECIALTY_MAP,
)
from .delegado_curation import (
    curation_report_header,
    curate_record,
    extract_slot_fields,
)
from .columns import (
    APORTE_CODEMU,
    CIP_EMBEDDED_RE,
    COL_APORCODEMU,
    COL_CIP1,
    COL_CIP2,
    COL_CIP3,
    COL_CIP4,
    COL_CODPAGO,
    COL_DELEGADO1,
    COL_DELEGADO2,
    COL_DELEGADO3,
    COL_DELEGADO4,
    COL_DICTAMEN1,
    COL_DICTAMEN2,
    COL_DICTAMEN3,
    COL_DICTAMEN4,
    COL_DIRECCION,
    COL_DNI,
    COL_FECHA,
    COL_FONDOCOMUN,
    COL_ID,
    COL_IGV,
    COL_IMPBRUTO,
    COL_NETOHONORA,
    COL_NOMBRE,
    COL_NRO,
    COL_NROEXPDTE,
    COL_NROREV,
    COL_PORCENTAJE,
    COL_PROYECTO,
    COL_RAZONSOCIAL,
    COL_RENTACIP,
    COL_RUC,
    COL_SUBTOTAL,
    COL_TOTAL,
    COL_TFONO,
    COL_TPERSONA,
    COL_USUARIO,
    DELEGADO_BLOCK_END,
    FONDO_COMUN,
    IMP_BRUTO,
    NETO_HONORARIO,
    RENTA_CIP,
    RH_SLOT_COLUMNS,
)
from .parsers import (
    _parse_date,
    coerce_int,
    coerce_month,
    DISTRITO_SINONIMOS,
    load_source_csv,
    money,
    money_diff,
    normalize_specialty,
    normalizar_distrito,
    parse_tpersona,
    resolve_tipo_documento,
    round_money,
)
from .reports import format_result_row, write_csv
from .rh_detail_validation import (
    build_source_compare_row,
    extract_source_values,
    source_needs_fix,
)

__all__ = [
    # columns
    "APORTE_CODEMU",
    "CIP_EMBEDDED_RE",
    "COL_APORCODEMU",
    "COL_CIP1",
    "COL_CIP2",
    "COL_CIP3",
    "COL_CIP4",
    "COL_CODPAGO",
    "COL_DELEGADO1",
    "COL_DELEGADO2",
    "COL_DELEGADO3",
    "COL_DELEGADO4",
    "COL_DICTAMEN1",
    "COL_DICTAMEN2",
    "COL_DICTAMEN3",
    "COL_DICTAMEN4",
    "COL_DIRECCION",
    "COL_DNI",
    "COL_FECHA",
    "COL_FONDOCOMUN",
    "COL_ID",
    "COL_IGV",
    "COL_IMPBRUTO",
    "COL_NETOHONORA",
    "COL_NOMBRE",
    "COL_NRO",
    "COL_NROEXPDTE",
    "COL_NROREV",
    "COL_PORCENTAJE",
    "COL_PROYECTO",
    "COL_RAZONSOCIAL",
    "COL_RENTACIP",
    "COL_RUC",
    "COL_SUBTOTAL",
    "COL_TOTAL",
    "COL_TFONO",
    "COL_TPERSONA",
    "COL_USUARIO",
    "DELEGADO_BLOCK_END",
    "FONDO_COMUN",
    "IMP_BRUTO",
    "NETO_HONORARIO",
    "RENTA_CIP",
    "RH_SLOT_COLUMNS",
    # delegado_columns
    "DELEGADO_SLOT_COLUMNS",
    "SLOT_SPECIALTY_DB_MAP",
    "_SLOT_SPECIALTY_MAP",
    "VALID_DICTAMEN_VALUES",
    # delegado_curation
    "curate_record",
    "curation_report_header",
    "extract_slot_fields",
    # parsers
    "_parse_date",
    "coerce_int",
    "coerce_month",
    "DISTRITO_SINONIMOS",
    "load_source_csv",
    "money",
    "money_diff",
    "normalize_specialty",
    "normalizar_distrito",
    "parse_tpersona",
    "resolve_tipo_documento",
    "round_money",
    # reports
    "write_csv",
    "format_result_row",
    # rh_detail_validation
    "extract_source_values",
    "build_source_compare_row",
    "source_needs_fix",
]
