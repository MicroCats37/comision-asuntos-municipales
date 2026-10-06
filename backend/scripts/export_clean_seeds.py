#!/usr/bin/env python
"""
Export clean JSON seeds from legacy SQLite database.

Reads from backend/db.sqlite3 using sqlite3 (no Django ORM).
Writes JSON files to backend/core_application/seeds/migrados/.

Usage:
    python scripts/export_clean_seeds.py                  # full export
    python scripts/export_clean_seeds.py --dry-run        # validate only
    python scripts/export_clean_seeds.py --only=usuarios_perfilingeniero,liquidaciones_tipoliquidacion

Transformation rules:
- id         -> uuid        (primary key)
- xxx_id     -> xxx_uuid    (foreign keys)
- usuario_creador_id -> usuario_creador_username (resolved via join to usuarios_usuario)
- M2M tables -> pivoted as arrays of UUIDs per parent record
- created_at, updated_at -> EXCLUDED from output
- legacy/snapshot columns -> EXCLUDED from output
"""

import argparse
import json
import os
import sqlite3
import sys
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

# ─── Configuration ─────────────────────────────────────────────────────────────

# backend/scripts/export_clean_seeds.py -> backend/
BACKEND_DIR = Path(__file__).resolve().parent.parent
DB_PATH = BACKEND_DIR / "db.sqlite3"
OUTPUT_DIR = BACKEND_DIR / "core_application" / "seeds" / "migrados"

# All 47 tables to export
TABLES_WITH_DATA = [
    # Phase 1-10 (22 tables with data)
    "liquidaciones_proyecto",
    "liquidaciones_liquidaciongeneral",
    "liquidaciones_liquidacionedificacion",
    "liquidaciones_liquidacionporcentajeobra",
    "liquidaciones_liquidacionporcentajeobradetalle",
    "liquidaciones_liquidaciondelegado",
    "finanzas_detallehonorariodelegado",
    "liquidaciones_liquidacioncomprobante",
    "liquidaciones_liquidacioninspector",
    "liquidaciones_liquidacioninspeccionobra",
    "liquidaciones_liquidacionporcategoriavisitas",
    "entidades_entidad",
    "liquidaciones_liquidacionhabilitacionurbana",
    "liquidaciones_liquidacionpormetrocuadrado",
    "entidades_ubigeodistrito",
    "entidades_ubigeoprovincia",
    "entidades_ubigeodepartamento",
    "entidades_municipalidad",
    "liquidaciones_delegadooperacion",
    "liquidaciones_delegadooperacionperiodo",
    "liquidaciones_delegado",
    "liquidaciones_inspector",
    "liquidaciones_inspectoroperacion",
    "liquidaciones_inspectoroperacionperiodo",
    "liquidaciones_liquidacionrelaciongrupo",
    "usuarios_perfilingeniero",
    "usuarios_usuario",
    "usuarios_capitulo",
    "usuarios_especialidadingeniero",
    "usuarios_especialidadrevision",
    "finanzas_uit",
    "finanzas_igv",
    "finanzas_tasadelegado",
    "finanzas_rangodescuentoinspector",
    "finanzas_escaladescuentoinspector",
    "liquidaciones_tipoliquidacion",
    "liquidaciones_liquidacioncodigo",
    "liquidaciones_tarifaliquidacionbase",
    "liquidaciones_tarifaporcentajeobra",
    "liquidaciones_tarifaporcategoriavisitas",
    "liquidaciones_tarifapormetrocuadrado",
    "liquidaciones_derechopormetrocuadrado",
    "liquidaciones_derechoporcentajeobra",
    "liquidaciones_liquidacionespecialidaddisponibles",
]

TABLES_EMPTY_STUBS = [
    # Phase 11-13 (25 empty stubs)
    "entidades_alcalde",
    "entidades_banco",
    "entidades_contacto",
    "entidades_contactobanco",
    "entidades_contactomunicipalidad",
    "entidades_gerenteurbano",
    "finanzas_detallehonorarioinspector",
    "finanzas_recibohonorariodelegado",
    "finanzas_recibohonorariodelegadomensual",
    "finanzas_recibohonorarioinspector",
    "finanzas_recibohonorarioinspectormensual",
    "finanzas_registropagoinspector",
    "finanzas_rhreparticionestacional",
    "finanzas_rhreparticionestacionalcapitulo",
    "finanzas_rhreparticionestacionaldelegado",
    "liquidaciones_liquidacionproyectista",
    "liquidaciones_liquidacionmecanicasuelos",
    "liquidaciones_liquidaciontaludes",
    "liquidaciones_liquidacionimpactovial",
    "liquidaciones_liquidacioncontacto",
    "liquidaciones_liquidaciondocumentos",
    "liquidaciones_liquidacionrelacionmiembro",
    "liquidaciones_proyectista",
]

ALL_TABLES = TABLES_WITH_DATA + TABLES_EMPTY_STUBS

# Columns to EXCLUDE from every export (universal)
EXCLUDE_COLUMNS = {"created_at", "updated_at"}

# Additional per-table column exclusions (table -> set of columns)
TABLE_EXCLUDE_COLUMNS: Dict[str, set] = {
    "liquidaciones_liquidaciongeneral": {
        "igv_snapshot", "uit_snapshot", "descripcion_legacy", "legacy",
    },
}

# Special FK renaming rules
# key: (table_name, column_name) -> new_column_name
# If not in this map, default rule is xxx_id -> xxx_uuid
SPECIAL_FK_RENAME: Dict[tuple, str] = {
    ("liquidaciones_liquidaciongeneral", "usuario_creador_id"): "usuario_creador_username",
    ("liquidaciones_liquidaciongeneral", "igv_id_id"): "igv_uuid",
    ("liquidaciones_liquidaciongeneral", "uit_id_id"): "uit_uuid",
}

# M2M junction tables: (parent_table, m2m_table, parent_fk_col, m2m_fk_col) -> m2m_field_name
M2M_TABLES = [
    (
        "liquidaciones_liquidaciongeneral",
        "liquidaciones_liquidaciongeneral_especialidades_revisadas",
        "liquidaciongeneral_id",
        "especialidadrevision_id",
        "especialidades_revisadas",
    ),
]


# ─── Core transformation ──────────────────────────────────────────────────────


def _build_username_cache(conn: sqlite3.Connection) -> Dict[str, str]:
    """
    Build a dict mapping usuarios_usuario.id -> username.
    Used to resolve usuario_creador_id -> username.
    """
    cur = conn.cursor()
    cur.execute("SELECT id, username FROM usuarios_usuario")
    return {str(row[0]): str(row[1]) for row in cur.fetchall()}


def _collect_m2m_data(
    conn: sqlite3.Connection,
    m2m_specs: List,
) -> Dict[str, Dict[str, List[str]]]:
    """
    Collect M2M data from junction tables.
    Returns: {parent_uuid: {m2m_field_name: [uuid, ...], ...}}
    """
    result: Dict[str, Dict[str, List[str]]] = {}
    cur = conn.cursor()
    for (
        parent_table,
        m2m_table,
        parent_fk_col,
        m2m_fk_col,
        m2m_field_name,
    ) in m2m_specs:
        try:
            cur.execute(f"SELECT {parent_fk_col}, {m2m_fk_col} FROM {m2m_table}")
            for parent_uuid, child_uuid in cur.fetchall():
                parent_uuid = str(parent_uuid)
                m2m_field_name_str = m2m_field_name
                if parent_uuid not in result:
                    result[parent_uuid] = {}
                if m2m_field_name_str not in result[parent_uuid]:
                    result[parent_uuid][m2m_field_name_str] = []
                result[parent_uuid][m2m_field_name_str].append(str(child_uuid))
        except sqlite3.OperationalError:
            # M2M table may not exist or be empty
            pass
    return result


def _transform_row(
    row: Dict[str, Any],
    table_name: str,
    username_cache: Dict[str, str],
    exclude_cols: set,
    special_renames: Dict[tuple, str],
) -> Dict[str, Any]:
    """
    Transform a row dict from SQLite format to export format:
    - id -> uuid
    - xxx_id -> xxx_uuid (or special names)
    - usuario_creador_id -> usuario_creador_username (via cache)
    - Exclude universal and per-table columns
    """
    result: Dict[str, Any] = {}
    for key, value in row.items():
        # Always exclude universal columns
        if key in exclude_cols:
            continue
        # Get table-specific exclusions
        table_excludes = TABLE_EXCLUDE_COLUMNS.get(table_name, set())
        if key in table_excludes:
            continue

        # Transform key name
        new_key = key
        if key == "id":
            new_key = "uuid"
        elif key.endswith("_id"):
            special = special_renames.get((table_name, key))
            if special:
                new_key = special
            else:
                new_key = key[:-3] + "_uuid"  # strip _id, add _uuid

        # Resolve usuario_creador_id -> username
        if key == "usuario_creador_id":
            new_key = "usuario_creador_username"
            value = username_cache.get(str(value), None) if value else None

        result[new_key] = value
    return result


def export_table(
    conn: sqlite3.Connection,
    table_name: str,
    username_cache: Dict[str, str],
    m2m_data: Dict[str, Dict[str, List[str]]],
    dry_run: bool = False,
) -> tuple:
    """
    Export a single table to JSON.

    Returns (row_count, output_rows).
    """
    cur = conn.cursor()

    # Get column names
    cur.execute(f"PRAGMA table_info({table_name})")
    all_cols = [r[1] for r in cur.fetchall()]

    # Build exclusion set
    exclude_cols = set(EXCLUDE_COLUMNS)
    if table_name in TABLE_EXCLUDE_COLUMNS:
        exclude_cols.update(TABLE_EXCLUDE_COLUMNS[table_name])

    # Fetch all rows
    cur.execute(f"SELECT * FROM {table_name}")
    raw_rows = cur.fetchall()

    transformed = []
    for raw in raw_rows:
        row_dict = dict(zip(all_cols, raw))
        t = _transform_row(row_dict, table_name, username_cache, exclude_cols, SPECIAL_FK_RENAME)
        # Attach M2M data if available
        row_uuid = t.get("uuid")
        if row_uuid and row_uuid in m2m_data:
            for m2m_field, uuids in m2m_data[row_uuid].items():
                t[m2m_field] = uuids
        transformed.append(t)

    return len(transformed), transformed


# ─── Main export ───────────────────────────────────────────────────────────────


def main():
    parser = argparse.ArgumentParser(description="Export clean JSON seeds from SQLite")
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Validate tables and row counts without writing files.",
    )
    parser.add_argument(
        "--only",
        type=str,
        default="",
        help="Comma-separated list of table names to export only.",
    )
    args = parser.parse_args()

    if not DB_PATH.exists():
        print(f"ERROR: SQLite database not found at {DB_PATH}")
        sys.exit(1)

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    # Filter tables
    only_filter = set(args.only.split(",")) if args.only else None
    if only_filter:
        tables_to_export = [t for t in ALL_TABLES if t in only_filter]
    else:
        tables_to_export = ALL_TABLES

    print(f"Database: {DB_PATH}")
    print(f"Output:   {OUTPUT_DIR}")
    print(f"Tables:   {len(tables_to_export)}")
    print()

    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row

    # Build username cache once
    username_cache = _build_username_cache(conn)

    # Collect M2M data once
    m2m_data = _collect_m2m_data(conn, M2M_TABLES)

    total_rows = 0
    total_tables = 0
    start = time.time()

    for table_name in tables_to_export:
        try:
            row_count, rows = export_table(
                conn, table_name, username_cache, m2m_data, dry_run=args.dry_run
            )
            total_rows += row_count
            total_tables += 1

            if args.dry_run:
                print(f"  [DRY-RUN] {table_name}: {row_count} rows")
            else:
                output_path = OUTPUT_DIR / f"{table_name}.json"
                with open(output_path, "w", encoding="utf-8") as f:
                    json.dump(rows, f, ensure_ascii=False, indent=2, default=str)
                print(f"  [OK] {table_name}: {row_count} rows -> {output_path.name}")

        except Exception as e:
            print(f"  [ERROR] {table_name}: {e}")
            if not args.dry_run:
                raise

    elapsed = time.time() - start

    print()
    print(f"Export complete: {total_tables} tables, {total_rows} total rows in {elapsed:.2f}s")

    conn.close()


if __name__ == "__main__":
    main()
