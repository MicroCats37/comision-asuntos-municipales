"""
Genera seeds/delegados_reales.json desde el CSV consolidado de comisiones técnicas.

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
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CSV_PATH = ROOT / "data" / "comisiones_tecnicas_cam_sep2025_ago2026_consolidado.csv"
OUT_PATH = ROOT / "backend" / "modules" / "liquidaciones" / "seeds" / "delegados_reales.json"

PERIODO = "SEPTIEMBRE 2025 A AGOSTO 2026"

# Mapeo (tipo_comision, especialidad) -> especialidad del seed
ESPECIALIDAD_MAP = {
    ("EDIFICACION", "INGENIERIA SANITARIA"): "Ingeniería Sanitaria - Edificaciones",
    ("EDIFICACION", "INGENIERIA ELECTRICA Y MECANICA ELECTRICA"): "Ingeniería Eléctrica y Mecánica Eléctrica - Edificaciones",
    ("HABILITACION URBANA", "INGENIERIA CIVIL"): "Ingeniería Civil - Habilitaciones Urbanas",
}


def normalize_cip(cip: str) -> str:
    """Normaliza CIP a 6 dígitos con ceros iniciales."""
    digits = "".join(ch for ch in (cip or "").strip() if ch.isdigit())
    if not digits:
        return ""
    return digits.zfill(6)[:6]


def main() -> None:
    with open(CSV_PATH, encoding="utf-8-sig") as f:
        rows = list(csv.DictReader(f))

    # Municipalidades por orden de aparición (código MUN0001..)
    municipios = []
    codigo_by_nombre = {}
    for r in rows:
        nombre = (r.get("municipalidad") or "").strip()
        if not nombre or nombre in codigo_by_nombre:
            continue
        codigo = f"MUN{len(municipios) + 1:04d}"
        codigo_by_nombre[nombre] = codigo
        municipios.append({"nombre": nombre, "codigo": codigo, "provincia": None, "distrito": None})

    delegados_by_cip = {}  # cip -> delegado dict
    asignaciones = []

    for r in rows:
        tipo_comision = (r.get("tipo_comision") or "").strip().upper()
        especialidad_csv = (r.get("especialidad") or "").strip().upper()
        esp_seed = ESPECIALIDAD_MAP.get((tipo_comision, especialidad_csv))
        if not esp_seed:
            continue

        muni_nombre = (r.get("municipalidad") or "").strip()
        muni_codigo = codigo_by_nombre.get(muni_nombre)
        if not muni_codigo:
            continue

        # titular_1, titular_2 (opcional), alterno
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
    print(f"Escrito en: {OUT_PATH}")


if __name__ == "__main__":
    main()
