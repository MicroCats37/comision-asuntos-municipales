"""
Genera seeds/delegados_reales.json desde el CSV consolidado de comisiones técnicas,
usando los códigos L* reales de la BD local (no MUN0001).

Fuente: data/comisiones_tecnicas_cam_sep2025_ago2026_consolidado.csv

Regla de negocio por (municipalidad, especialidad):
- 1 titular (titular_1) + 1 alterno, obligatorios
- titular_2 OPCIONAL (solo en los casos especiales)
- NUNCA 2 alternos

Uso:
    python scripts/generate_delegados_from_csv.py
"""

import csv
import json
import sqlite3
import unicodedata
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CSV_PATH = ROOT / "data" / "comisiones_tecnicas_cam_sep2025_ago2026_consolidado.csv"
DB_PATH = ROOT / "backend" / "db.sqlite3"
OUT_PATH = ROOT / "backend" / "modules" / "liquidaciones" / "seeds" / "delegados_reales.json"

PERIODO = "SEPTIEMBRE 2025 A AGOSTO 2026"

ESPECIALIDAD_MAP = {
    ("EDIFICACION", "INGENIERIA SANITARIA"): "Ingeniería Sanitaria - Edificaciones",
    ("EDIFICACION", "INGENIERIA ELECTRICA Y MECANICA ELECTRICA"): "Ingeniería Eléctrica y Mecánica Eléctrica - Edificaciones",
    ("HABILITACION URBANA", "INGENIERIA CIVIL"): "Ingeniería Civil - Habilitaciones Urbanas",
}

# Sinónimos: nombre del CSV/seed -> nombre real en BD
SINONIMOS = {
    "CENTRO HISTORICO": "CENTRO HISTORICO DE LIMA",
    "COMISION AD HOC": "COMISION AD HOC SEGUNDA INSTANCIA ADMINISTRATIVA",
    "BARRANCA": "BARRANCA - NORTE",
    "PROVINCIAL DE HUAURA": "HUAURA",
    "PROVINCIA DE HUAROCHIRI": "HUAROCHIRI",
    "PROVINCIAL DE BARRANCA": "BARRANCA - NORTE",
    "STA MARIA": "SANTA MARIA",
    "SAN ANTONIO DE CAÑETE": "SAN ANTONIO - CAÑETE",
    "SAN LUIS DE CAÑETE": "SAN LUIS - CAÑETE",
    "SAN LUIS  DE CAÑETE": "SAN LUIS - CAÑETE",
    "ASIA": "SAN VICENTE DE CAÑETE/ASIA",
    "PROVINCIAL DE CAÑETE": "SAN VICENTE DE CAÑETE",
    "SUPE PUERTO": "SUPE - PUERTO",
}


def normalize_cip(cip: str) -> str:
    digits = "".join(ch for ch in (cip or "").strip() if ch.isdigit())
    if not digits:
        return ""
    return digits.zfill(6)[:6]


def norm_name(s: str) -> str:
    n = unicodedata.normalize("NFD", s.upper())
    return " ".join(
        "".join(c for c in n if unicodedata.category(c) != "Mn")
        .replace("-", " ")
        .replace("–", " ")
        .split()
    )


def load_bd_codigos() -> dict:
    """Devuelve {nombre_normalizado: (codigo_L, nombre_real)} desde la BD local."""
    con = sqlite3.connect(DB_PATH)
    try:
        rows = con.execute("SELECT codigo, nombre FROM entidades_municipalidad").fetchall()
    finally:
        con.close()
    return {norm_name(n): (c, n) for c, n in rows}


def resolve_codigo(nombre_csv: str, bd_codigos: dict) -> str | None:
    """Resuelve el código L de una municipalidad del CSV contra la BD local."""
    nn = norm_name(nombre_csv)
    if nn in bd_codigos:
        return bd_codigos[nn][0]
    sinonimo = SINONIMOS.get(nombre_csv.strip().upper())
    if sinonimo and norm_name(sinonimo) in bd_codigos:
        return bd_codigos[norm_name(sinonimo)][0]
    return None


# Códigos asignados a municipalidades que no existen en la BD (se crearán al seedear).
# El campo codigo de Municipalidad es max_length=10, así que usamos códigos cortos.
FALTANTE_COUNT = {"n": 0}


def resolve_codigo_o_faltante(nombre_csv: str, bd_codigos: dict) -> str:
    """Resuelve código L; si no existe en BD, asigna LFALTN (se creará al seedear)."""
    codigo = resolve_codigo(nombre_csv, bd_codigos)
    if codigo:
        return codigo
    FALTANTE_COUNT["n"] += 1
    return f"LFALTN{FALTANTE_COUNT['n']}"


def main() -> None:
    with open(CSV_PATH, encoding="utf-8-sig") as f:
        rows = list(csv.DictReader(f))

    bd_codigos = load_bd_codigos()
    print(f"BD local: {len(bd_codigos)} municipalidades con código L")

    # Municipalidades (nombre + codigo L) en orden de aparición
    municipios = []
    codigo_by_nombre = {}
    seen = set()
    for r in rows:
        nombre = (r.get("municipalidad") or "").strip()
        if not nombre or nombre in seen:
            continue
        codigo = resolve_codigo_o_faltante(nombre, bd_codigos)
        seen.add(nombre)
        codigo_by_nombre[nombre] = codigo
        municipios.append({"nombre": nombre, "codigo": codigo, "provincia": None, "distrito": None})

    delegados_by_cip = {}
    asignaciones = []

    for r in rows:
        tipo_comision = (r.get("tipo_comision") or "").strip().upper()
        especialidad_csv = (r.get("especialidad") or "").strip().upper()
        esp_seed = ESPECIALIDAD_MAP.get((tipo_comision, especialidad_csv))
        if not esp_seed:
            continue

        muni_nombre = (r.get("municipalidad") or "").strip()
        muni_codigo = codigo_by_nombre.get(muni_nombre)

        entries = [
            ("titular", r.get("titular_1_cip"), r.get("titular_1_nombre")),
            ("titular", r.get("titular_2_cip"), r.get("titular_2_nombre")),
            ("alterno", r.get("alterno_cip"), r.get("alterno_nombre")),
        ]

        for tipo, cip_raw, nombre_raw in entries:
            cip = normalize_cip(cip_raw)
            if not cip:
                continue
            nombre = (nombre_raw or "").strip()
            if cip not in delegados_by_cip:
                delegados_by_cip[cip] = {
                    "cip": cip,
                    "nombre_completo": nombre or cip,
                    "especialidad": esp_seed,
                }
            asignaciones.append(
                {
                    "cip": cip,
                    "municipalidad_codigo": muni_codigo,
                    "especialidad": esp_seed,
                    "tipo": tipo,
                }
            )

    payload = {
        "version": "1.0",
        "periodo": PERIODO,
        "fuente": str(CSV_PATH.relative_to(ROOT)),
        "municipalidades": municipios,
        "delegados": list(delegados_by_cip.values()),
        "asignaciones": asignaciones,
    }

    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(OUT_PATH, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)

    print(f"Municipalidades: {len(municipios)}")
    print(f"Delegados: {len(delegados_by_cip)}")
    print(f"Asignaciones: {len(asignaciones)}")
    print(f"Municipalidades FALTANTES (crear): {FALTANTE_COUNT['n']}")
    print(f"Escrito en: {OUT_PATH}")


if __name__ == "__main__":
    main()
