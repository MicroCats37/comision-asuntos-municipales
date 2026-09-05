import os
import sys
import csv
import unicodedata
from pathlib import Path

# Configure Django before any model imports
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.development")

import tablib
import django
django.setup()

from backend.modules.liquidaciones.domain.resources import DelegadoOperacionResource, parse_date
from backend.modules.liquidaciones.domain.models import DelegadoOperacion, DelegadoOperacionPeriodo
from datetime import date as date_class

ROOT = Path(__file__).resolve().parent.parent
CSV_PATH = ROOT / "data-old" / "delegados" / "comisiones_tecnicas_cam_sep2025_ago2026_consolidado.csv"

TIPO_COMISION_TO_TIPO_LIQUIDACION = {
    "EDIFICACION": "EDIFICACION",
    "HABILITACION URBANA": "HABILITACION_URBANA",
}

_SUFFIXES = (" - EDIFICACIONES", " - HABILITACIONES URBANAS", " - Edificaciones", " - Habilitaciones Urbanas")

def strip_especialidad_suffix(raw):
    esp = raw.strip()
    for suf in _SUFFIXES:
        if esp.upper().endswith(suf.upper()):
            esp = esp[: -len(suf)].strip()
    return esp

# Count before
before_count = DelegadoOperacion.objects.count()
print(f"DelegadoOperacion before: {before_count}")
print(f"DelegadoOperacionPeriodo before: {DelegadoOperacionPeriodo.objects.count()}")

# Read CSV
print(f"Leyendo CSV: {CSV_PATH}")
try:
    with open(CSV_PATH, encoding="utf-8-sig") as f:
        rows = list(csv.DictReader(f))
except UnicodeDecodeError:
    with open(CSV_PATH, encoding="utf-8") as f:
        rows = list(csv.DictReader(f))

print(f"  Filas en CSV: {len(rows)}")

# Flatten
dataset = tablib.Dataset()
dataset.headers = [
    "cip", "municipalidad_codigo", "tipo", "tipo_liquidacion_codigo",
    "especialidad_nombre", "vigencia_inicio", "vigencia_fin",
]

skipped_empty = 0
skipped_unknown_tipo = 0

for r in rows:
    tipo_comision = (r.get("tipo_comision") or "").strip().upper()
    tipo_liq_codigo = TIPO_COMISION_TO_TIPO_LIQUIDACION.get(tipo_comision)
    if tipo_liq_codigo is None:
        skipped_unknown_tipo += 1
        continue

    especialidad_raw = (r.get("especialidad") or "").strip()
    especialidad_nombre = strip_especialidad_suffix(especialidad_raw)
    muni_nombre = (r.get("municipalidad") or "").strip()

    vigencia_inicio = "2025-09-01"
    vigencia_fin = "2026-08-31"

    entries = [
        ("TITULAR", r.get("titular_1_cip")),
        ("TITULAR", r.get("titular_2_cip")),
        ("ALTERNO", r.get("alterno_cip")),
    ]

    for tipo, cip_raw in entries:
        digits = "".join(ch for ch in (cip_raw or "").strip() if ch.isdigit())
        if not digits:
            skipped_empty += 1
            continue
        cip = digits.zfill(6)[:6]
        if cip == "000000":
            skipped_empty += 1
            continue
        dataset.append([
            cip, muni_nombre, tipo, tipo_liq_codigo,
            especialidad_nombre, vigencia_inicio, vigencia_fin,
        ])

print(f"  Registros a importar: {len(dataset)}")
print(f"  Saltados (sin CIP): {skipped_empty}")
print(f"  Saltados (tipo_comision desconocido): {skipped_unknown_tipo}")

# Import
print("\nEjecutando import (dry_run=False)...")
result = DelegadoOperacionResource().import_data(dataset, dry_run=False)

# Report
print("\n=== RESULTADOS DEL IMPORT ===")
print(f"  Total filas  : {result.total_rows}")
print(f"  valid_rows   : {len(result.valid_rows)}")
print(f"  invalid_rows : {len(result.invalid_rows)}")
print(f"  base_errors  : {len(result.base_errors)}")
if result.invalid_rows:
    print("\n=== INVALID ROWS ===")
    for ir in result.invalid_rows[:10]:
        print(f"  {ir}")

# Count after
after_count = DelegadoOperacion.objects.count()
periodos_2025 = DelegadoOperacionPeriodo.objects.filter(periodo_inicio=date_class(2025, 9, 1)).count()
periodos_2026 = DelegadoOperacionPeriodo.objects.filter(periodo_inicio=date_class(2026, 9, 1)).count()
print(f"\nDelegadoOperacion after: {after_count} (diff: {after_count - before_count})")
print(f"DelegadoOperacionPeriodo with 2025-09-01: {periodos_2025}")
print(f"DelegadoOperacionPeriodo with 2026-09-01: {periodos_2026}")
