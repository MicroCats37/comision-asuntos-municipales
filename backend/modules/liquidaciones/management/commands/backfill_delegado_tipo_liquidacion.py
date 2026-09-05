"""
Backfill tipo_liquidacion en DelegadoOperacion (DelegadoMunicipalidad) con NULL.

Las 574 operaciones seedeadas antes de la migración 0031 quedaron con
tipo_liquidacion=NULL. Este comando lee delegados_reales.json y, para cada
DelegadoOperacion con tipo_liquidacion NULL, le asigna el tipo de la asignación
correspondiente del JSON por (cip -> delegado, municipalidad_codigo).

Idempotente: solo actualiza filas con tipo_liquidacion NULL.
Uso:
    python manage.py backfill_delegado_tipo_liquidacion --settings=config.settings.development
    python manage.py backfill_delegado_tipo_liquidacion --dry-run --settings=config.settings.development
"""
import json
from pathlib import Path

from django.core.management.base import BaseCommand

from modules.liquidaciones.domain.models.delegado import DelegadoOperacion
from modules.liquidaciones.domain.models.tipo_liquidacion import TipoLiquidacion


class Command(BaseCommand):
    help = "Rellena tipo_liquidacion en DelegadoOperacion con NULL desde delegados_reales.json."

    SEEDS_DIR = Path(__file__).resolve().parent.parent.parent / "seeds"

    def add_arguments(self, parser):
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Validar sin escribir en la base de datos.",
        )
        parser.add_argument(
            "--seed-path",
            type=str,
            default=None,
            help="Ruta al archivo JSON de delegados.",
        )

    def handle(self, *args, **options):
        dry_run = options["dry_run"]
        seed_path = (
            Path(options["seed_path"])
            if options["seed_path"]
            else self.SEEDS_DIR / "delegados_reales.json"
        )

        if not seed_path.exists():
            self.stdout.write(self.style.ERROR(f"No se encontró {seed_path}"))
            return

        with open(seed_path, encoding="utf-8") as f:
            data = json.load(f)

        # Mapa de código de municipalidad -> nombre (para localizar por codigo).
        municipios_codigo = {}
        for m in data.get("municipalidades", []):
            if m.get("codigo"):
                municipios_codigo[m["codigo"]] = m.get("nombre")

        # Indexar asignaciones del JSON por (cip, municipalidad_codigo).
        asign_por_clave = {}
        for asign in data.get("asignaciones", []):
            cip = str(asign.get("cip", "")).strip()
            codigo_mun = str(asign.get("municipalidad_codigo", "")).strip()
            tipo_liq = str(asign.get("tipo_liquidacion", "") or "").strip()
            if cip and codigo_mun and tipo_liq:
                asign_por_clave[(cip, codigo_mun)] = tipo_liq

        # Tipos disponibles por codigo.
        tipos = {t.codigo: t for t in TipoLiquidacion.objects.all()}

        # Filas con NULL tipo, agrupadas por delegado (cip) y municipalidad (codigo).
        filas = DelegadoOperacion.objects.filter(
            tipo_liquidacion__isnull=True
        ).select_related("delegado__perfil_ingeniero", "municipalidad")

        actualizadas = 0
        sin_match = []

        for op in filas:
            cip = op.delegado.perfil_ingeniero.cip
            codigo_mun = op.municipalidad.codigo or ""
            tipo_codigo = asign_por_clave.get((cip, codigo_mun))

            if not tipo_codigo:
                sin_match.append(f"{cip} -> {codigo_mun or op.municipalidad.nombre}")
                continue

            tipo = tipos.get(tipo_codigo)
            if tipo is None:
                sin_match.append(f"{cip} -> {codigo_mun}: tipo '{tipo_codigo}' no en BD")
                continue

            if dry_run:
                self.stdout.write(f"  [DRY-RUN] {cip} -> {codigo_mun}: set {tipo_codigo}")
                continue

            op.tipo_liquidacion = tipo
            op.save(update_fields=["tipo_liquidacion"])
            actualizadas += 1

        if dry_run:
            self.stdout.write(self.style.WARNING("DRY-RUN: No se escribió en la base de datos."))
            return

        self.stdout.write(
            self.style.SUCCESS(
                f"DelegadoOperacion actualizadas: {actualizadas}"
            )
        )
        if sin_match:
            self.stdout.write(
                self.style.WARNING(
                    f"Sin match ({len(sin_match)}): {', '.join(sin_match[:10])}"
                )
            )
