"""Export loaded PerfilIngeniero records referenced by delegados_reales seed.

Run from backend folder:
    uv run python ../scripts/export_colegiados_seed.py
"""

import json
import os
import sys
from pathlib import Path

import django


BACKEND_DIR = Path(__file__).resolve().parents[1] / "backend"
sys.path.insert(0, str(BACKEND_DIR))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.development")
django.setup()

from modules.usuarios.models import PerfilIngeniero  # noqa: E402


def main():
    seed_path = BACKEND_DIR / "modules" / "liquidaciones" / "seeds" / "delegados_reales.json"
    out_path = BACKEND_DIR / "modules" / "liquidaciones" / "seeds" / "colegiados_reales.json"

    seed = json.loads(seed_path.read_text(encoding="utf-8"))
    cips = sorted({item["cip"] for item in seed["delegados"]})

    data = []
    for perfil in PerfilIngeniero.objects.select_related("capitulo").filter(cip__in=cips).order_by("cip"):
        data.append(
            {
                "cip": perfil.cip,
                "dni": perfil.dni,
                "nombres": perfil.nombres,
                "apellido_paterno": perfil.apellido_paterno,
                "apellido_materno": perfil.apellido_materno,
                "fecha_nacimiento": perfil.fecha_nacimiento.isoformat() if perfil.fecha_nacimiento else None,
                "genero": perfil.genero,
                "correo_personal": perfil.correo_personal,
                "correo_institucional": perfil.correo_institucional,
                "direccion": perfil.direccion,
                "ubigeo": perfil.ubigeo,
                "codigo_especialidad": perfil.codigo_especialidad,
                "capitulo": {
                    "registro_id": perfil.capitulo.registro_id,
                    "abreviacion": perfil.capitulo.abreviacion,
                    "nombre": perfil.capitulo.nombre,
                    "grupo_envio_intitucional": perfil.capitulo.grupo_envio_intitucional,
                }
                if perfil.capitulo
                else None,
            }
        )

    out = {
        "version": "1.0",
        "source": "Endpoint CIP materializado desde load_delegados_reales",
        "count": len(data),
        "colegiados": data,
    }
    out_path.write_text(json.dumps(out, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"written {out_path} ({len(data)} colegiados)")


if __name__ == "__main__":
    main()
