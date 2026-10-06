import json
import time
from pathlib import Path

from core_application.management.commands._seed_clean_base import (
    BaseCleanSeedCommand,
    SeedContext,
)
from modules.entidades.domain.models.entidad import Entidad
from modules.entidades.domain.models.ubigeo import UbigeoDistrito
from modules.liquidaciones.domain.models.proyecto import Proyecto


class Command(BaseCleanSeedCommand):
    help = "Seed proyectos from clean JSON"
    SEED_PHASE = "proyectos"
    MODELS_TO_SEED = [Proyecto]
    SEEDS_DIR = (
        Path(__file__).resolve().parent.parent.parent
        / "seeds"
        / "migrados"
    )

    def _load_json(self, filename):
        with open(self.SEEDS_DIR / filename, encoding="utf-8") as f:
            return json.load(f)

    def handle_phase(self, *args, **options):
        ctx = SeedContext()
        dry_run = options.get("dry_run", False)
        verbose = options.get("verbose", False)
        self._seed_proyecto(ctx, dry_run, verbose)

    def _seed_proyecto(self, ctx, dry_run, verbose):
        rows = self._load_json("liquidaciones_proyecto.json")
        if dry_run:
            self.print_summary(
                self.SEED_PHASE, "Proyecto", len(rows), 0, 0, 0, 0.0
            )
            return

        start = time.time()
        created = updated = errors = 0
        for row in rows:
            try:
                defaults = {
                    k: v
                    for k, v in row.items()
                    if k != "uuid" and not k.endswith("_uuid")
                }
                if row.get("entidad_uuid"):
                    defaults["entidad"] = ctx.resolve_fk(
                        Entidad, row["entidad_uuid"]
                    )
                if row.get("distrito_uuid"):
                    defaults["distrito"] = ctx.resolve_fk(
                        UbigeoDistrito, row["distrito_uuid"]
                    )

                obj, was_created = Proyecto.objects.update_or_create(
                    id=row["uuid"], defaults=defaults
                )
                ctx.store(Proyecto, obj.id, obj)
                if was_created:
                    created += 1
                else:
                    updated += 1
                if verbose:
                    tag = "CREATE" if was_created else "UPDATE"
                    self.stdout.write(f"[{tag}] Proyecto {row['uuid']}")
            except Exception as e:
                errors += 1
                self.stdout.write(f"ERROR Proyecto {row['uuid']}: {e}")

        duration = time.time() - start
        self.print_summary(
            self.SEED_PHASE,
            "Proyecto",
            len(rows),
            created,
            updated,
            errors,
            duration,
        )