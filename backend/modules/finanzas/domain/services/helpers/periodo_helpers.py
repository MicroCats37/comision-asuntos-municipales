"""
Period parsing helpers for Finanzas domain.

Pure string utilities — no DB access, no side effects.
"""
from typing import Optional


def _parse_periodo_year(periodo: str) -> Optional[int]:
    """Extrae el año (int) de un periodo 'YYYY-MM'. None si no parseable."""
    try:
        return int(str(periodo).split("-")[0])
    except (ValueError, TypeError, IndexError):
        return None


def _parse_periodo_mes(periodo: str) -> Optional[int]:
    """Extrae el mes (int, 1-12) de un periodo 'YYYY-MM'. None si no parseable."""
    try:
        return int(str(periodo).split("-")[1])
    except (ValueError, TypeError, IndexError):
        return None
