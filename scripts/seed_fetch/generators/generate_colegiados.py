"""Genera colegiados_reales.json desde el endpoint CIP.

La especialidad se guarda con nombre = codigo (ej: "01"), porque el endpoint
NO devuelve el nombre de la especialidad. El usuario renombra después.
El capítulo SÍ trae nombre real del endpoint.
"""

import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO_ROOT / "scripts" / "seed_fetch"))

from generators.cip_client import CipClient  # noqa: E402

DEFAULT_ENDPOINT = "http://172.16.93.83:9001/api/v1/colegiado/{cip}"
DEFAULT_OUTPUT = REPO_ROOT / "backend" / "modules" / "liquidaciones" / "seeds" / "colegiados_reales.json"


def normalize(raw: dict) -> dict:
    """Transforma la respuesta cruda del endpoint al formato seed."""
    capitulo_raw = raw.get("capitulo") or {}
    return {
        "cip": raw.get("cip", ""),
        "dni": raw.get("dni", ""),
        "nombres": " ".join(filter(None, [raw.get("nombre1", ""), raw.get("nombre2", "")])).strip(),
        "apellido_paterno": raw.get("paterno", "") or raw.get("apellido_paterno", ""),
        "apellido_materno": raw.get("materno", "") or raw.get("apellido_materno", ""),
        "fecha_nacimiento": raw.get("fechaNacimiento", "") or raw.get("fecha_nacimiento", ""),
        "genero": raw.get("codGenero", "") or raw.get("genero", ""),
        "celular": raw.get("celular", ""),
        "correo_personal": raw.get("correoPers", "") or raw.get("correo_personal", ""),
        "correo_institucional": raw.get("correoInst", "") or raw.get("correo_institucional", ""),
        "direccion": raw.get("direccion", ""),
        "ubigeo": raw.get("distritoId", "") or raw.get("ubigeo", ""),
        # La especialidad SOLO tiene codigo. nombre = codigo por ahora.
        "codigo_especialidad": raw.get("codEspecialidad", "") or raw.get("codigo_especialidad", ""),
        # Datos de habilitación (llenan la tabla IngenieroHabilitacion)
        "habilitacion": {
            "condicion_cip": raw.get("condicion", ""),
            "ultimo_periodo_pagado_cip": raw.get("ultimoPeriodoPagado", ""),
        },
        "capitulo": {
            "registro_id": capitulo_raw.get("id", "") or capitulo_raw.get("registro_id", ""),
            "abreviacion": capitulo_raw.get("abreviatura", "") or capitulo_raw.get("abreviacion", ""),
            "nombre": capitulo_raw.get("descripcion", "") or capitulo_raw.get("nombre", ""),
            "grupo_envio_intitucional": capitulo_raw.get("grupoEnviosInst", ""),
        },
    }


def build(cips: list[str], endpoint_url: str = DEFAULT_ENDPOINT, skip_errors: bool = False) -> list[dict]:
    """Fetch cada CIP y normaliza a formato seed."""
    client = CipClient(endpoint_url)
    raw_data, errors = client.fetch_many(cips, skip_errors=skip_errors)
    return [normalize(r) for r in raw_data]


def write(colegiados: list[dict], output_path: Path = DEFAULT_OUTPUT) -> None:
    """Escribe el JSON final."""
    payload = {
        "version": "1.0",
        "source": "Endpoint CIP materializado desde scripts/seed_fetch",
        "count": len(colegiados),
        "colegiados": colegiados,
    }
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Wrote {len(colegiados)} colegiados to {output_path}")
