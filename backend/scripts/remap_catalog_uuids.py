#!/usr/bin/env python
import json
import os
import sys
import time
from pathlib import Path

import psycopg2

BACKEND_DIR = Path(__file__).resolve().parent.parent
SEEDS_DIR = BACKEND_DIR / "core_application" / "seeds" / "migrados"

DB_HOST = os.environ.get("DB_HOST", "localhost")
DB_NAME = os.environ.get("DB_NAME", "cam_db")
DB_USER = os.environ.get("DB_USER", "cam_user")
DB_PASSWORD = os.environ.get("DB_PASSWORD", "changeme")


CATALOG_UUIDS = {
    "usuarios_capitulo": ("registro_id", "registro_id"),
    "usuarios_especialidadingeniero": ("codigo_capitulo", "codigo", "capitulo_id"),
    "usuarios_especialidadrevision": ("slug", "slug"),
    "finanzas_uit": ("anio", "anio"),
    "finanzas_igv": ("snapshot_label", "porcentaje"),
    "finanzas_tasadelegado": ("anio", "anio"),
    "finanzas_rangodescuentoinspector": ("anio", "anio"),
    "finanzas_escaladescuentoinspector": ("anio", "anio"),
    "entidades_ubigeodepartamento": ("codigo_departamento", "codigo_departamento"),
    "entidades_ubigeoprovincia": ("codigo_provincia", "codigo_departamento", "codigo_provincia"),
    "entidades_ubigeodistrito": ("ubigeo", "ubigeo"),
    "entidades_municipalidad": ("codigo", "codigo"),
    "liquidaciones_tipoliquidacion": ("codigo", "codigo"),
    "liquidaciones_liquidacioncodigo": ("tipo_liquidacion_codigo", "codigo_cta"),
    "liquidaciones_tarifaliquidacionbase": ("anio_tipo", "anio_tipo"),
    "liquidaciones_tarifaporcentajeobra": ("anio_tipo", "anio_tipo"),
    "liquidaciones_tarifaporcategoriavisitas": ("anio_tipo", "anio_tipo"),
    "liquidaciones_tarifapormetrocuadrado": ("anio_tipo", "anio_tipo"),
    "liquidaciones_derechopormetrocuadrado": ("anio_tipo", "anio_tipo"),
    "liquidaciones_derechoporcentajeobra": ("anio_tipo", "anio_tipo"),
}


def fetch_uuid_map(conn, table_name, fields):
    if len(fields) < 2:
        return None
    cur = conn.cursor()
    sql = f'SELECT id, {", ".join(fields[1:])} FROM {table_name}'
    cur.execute(sql)
    rows = cur.fetchall()
    result = {}
    for row in rows:
        new_uuid = str(row[0])
        natural = tuple(str(v) for v in row[1:])
        result[natural] = new_uuid
    return result


def natural_key_for_uuid(row, fields):
    return tuple(str(row.get(f, "")) for f in fields[1:])


def remap_uuid_field(rows, old_uuid, new_uuid):
    count = 0
    for row in rows:
        for k, v in list(row.items()):
            if isinstance(v, str) and v == old_uuid:
                row[k] = new_uuid
                count += 1
            elif isinstance(v, list):
                for i, item in enumerate(v):
                    if item == old_uuid:
                        v[i] = new_uuid
                        count += 1
    return count


def main():
    only = set(sys.argv[1:]) if len(sys.argv) > 1 else None

    conn = psycopg2.connect(
        host=DB_HOST, dbname=DB_NAME, user=DB_USER, password=DB_PASSWORD
    )
    print(f"Connected to {DB_HOST}/{DB_NAME}")

    catalog_maps = {}
    for cat_table, fields in CATALOG_UUIDS.items():
        if only and cat_table not in only:
            continue
        try:
            uuid_map = fetch_uuid_map(conn, cat_table, fields)
            if uuid_map:
                catalog_maps[cat_table] = (uuid_map, fields)
                print(f"  {cat_table}: {len(uuid_map)} records loaded")
        except Exception as e:
            print(f"  {cat_table}: ERROR {e}")

    conn.close()

    print(f"\nScanning JSON files in {SEEDS_DIR}")
    json_files = sorted(SEEDS_DIR.glob("*.json"))
    total_remapped = 0
    for json_path in json_files:
        with open(json_path, encoding="utf-8") as f:
            rows = json.load(f)
        if not isinstance(rows, list):
            continue
        remapped_count = 0
        for cat_table, (uuid_map, _) in catalog_maps.items():
            for old_uuid, new_uuid in uuid_map.items():
                remapped_count += remap_uuid_field(rows, old_uuid, new_uuid)
        if remapped_count > 0:
            with open(json_path, "w", encoding="utf-8") as f:
                json.dump(rows, f, ensure_ascii=False, indent=2, default=str)
            print(f"  {json_path.name}: {remapped_count} UUIDs remapped")
            total_remapped += remapped_count

    print(f"\nTotal UUIDs remapped: {total_remapped}")


if __name__ == "__main__":
    main()