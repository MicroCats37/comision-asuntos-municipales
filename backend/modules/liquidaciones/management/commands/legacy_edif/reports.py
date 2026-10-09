"""
EDIF legacy helpers — CSV output and row-formatting utilities.
"""

import csv
from pathlib import Path


def write_csv(path: Path, rows: list[dict]) -> None:
    """
    Write a list of dicts as a UTF-8 BOM CSV file.

    Creates parent directories if they do not exist.
    """
    if path.parent and not path.parent.exists():
        path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8-sig") as file:
        writer = csv.DictWriter(file, fieldnames=list(rows[0].keys()) if rows else [])
        if rows:
            writer.writeheader()
            writer.writerows(rows)


def format_result_row(row: dict) -> str:
    """
    Format a validation result row for console output.

    Args:
        row: dict as produced by _result_row in the command

    Returns:
        Human-readable string for the console.
    """
    base = (
        f"{row['status']} numero={row['numero']} exp={row['expediente']} "
        f"rh_count={row['rh_detail_count']} esp={row['especialidad']} bad={row['bad_fields'] or '-'}"
    )
    if row["status"] == "MISMATCH":
        return f"{base} | bruto {row['actual_imp_bruto']}->{row['expected_imp_bruto_legacy']}"
    return base
