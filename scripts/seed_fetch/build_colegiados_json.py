"""
Pipeline de fetch al endpoint CIP para generar seeds JSON.

Recolecta CIPs únicos (delegados + inspectores), consulta el endpoint
de colegiados y genera los JSON de seed con la estructura del modelo ACTUAL.

La especialidad se guarda con nombre = codigo (el endpoint no devuelve nombre).

Uso:
  python scripts/seed_fetch/build_colegiados_json.py --limit 5 --dry-run
  python scripts/seed_fetch/build_colegiados_json.py --endpoint-url http://host:port/api/v1/colegiado/{cip}
"""

import argparse
import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "scripts" / "seed_fetch"))

from generators import generate_colegiados  # noqa: E402

DEFAULT_ENDPOINT = "http://172.16.93.83:9001/api/v1/colegiado/{cip}"
DEFAULT_DELEGADOS_SEED = REPO_ROOT / "backend" / "modules" / "liquidaciones" / "seeds" / "delegados_reales.json"
DEFAULT_OUTPUT_DIR = REPO_ROOT / "backend" / "modules" / "liquidaciones" / "seeds"


def collect_cips(delegados_seed_path: Path, output_dir: Path) -> list[str]:
    """Extrae CIPs únicos de los seeds de delegados e inspectores."""
    cips: set[str] = set()
    if delegados_seed_path.exists():
        seed = json.loads(delegados_seed_path.read_text(encoding="utf-8"))
        for delegado in seed.get("delegados", []):
            cip = str(delegado.get("cip", "")).strip()
            if cip:
                cips.add(cip)

    inspectores_seed = output_dir / "inspectores_reales.json"
    if inspectores_seed.exists():
        seed = json.loads(inspectores_seed.read_text(encoding="utf-8"))
        if isinstance(seed, list):
            for inspector in seed:
                cip = str(inspector.get("cip", "")).strip()
                if cip:
                    cips.add(cip)
        elif isinstance(seed, dict):
            for inspector in seed.get("inspectores", []):
                cip = str(inspector.get("cip", "")).strip()
                if cip:
                    cips.add(cip)

    return sorted(cips)


def main():
    parser = argparse.ArgumentParser(description="Build seed JSON from CIP endpoint")
    parser.add_argument("--delegados-seed-path", type=Path, default=DEFAULT_DELEGADOS_SEED)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    parser.add_argument("--endpoint-url", type=str, default=DEFAULT_ENDPOINT)
    parser.add_argument("--limit", type=int, default=None, help="Limitar a N CIPs (debug)")
    parser.add_argument("--dry-run", action="store_true", help="No escribir archivos")
    parser.add_argument("--skip-errors", action="store_true", help="Continuar si un CIP falla")
    args = parser.parse_args()

    cips = collect_cips(args.delegados_seed_path, args.output_dir)
    if args.limit:
        cips = cips[: args.limit]

    print(f"Collected {len(cips)} unique CIPs")
    if args.dry_run:
        print("DRY RUN - no files will be written")
        for cip in cips[:5]:
            print(f"  Would fetch: {cip}")
        return

    colegiados = generate_colegiados.build(
        cips=cips,
        endpoint_url=args.endpoint_url,
        skip_errors=args.skip_errors,
    )
    generate_colegiados.write(colegiados, args.output_dir / "colegiados_reales.json")


if __name__ == "__main__":
    main()
