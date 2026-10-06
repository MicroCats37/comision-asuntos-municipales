import json
import time
from pathlib import Path

from core_application.management.commands._seed_clean_base import (
    BaseCleanSeedCommand,
    SeedContext,
)
from modules.entidades.domain.models.entidad import Entidad
from modules.entidades.domain.models.ubigeo import UbigeoDistrito, UbigeoProvincia


class Command(BaseCleanSeedCommand):
    help = "Seed entidades from clean JSON"
    SEED_PHASE = "entidades"
    MODELS_TO_SEED = [Entidad]
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
        self._seed_entidad(ctx, dry_run, verbose)

    def _seed_entidad(self, ctx, dry_run, verbose):
        rows = self._load_json("entidades_entidad.json")
        if dry_run:
            self.print_summary(
                self.SEED_PHASE, "Entidad", len(rows), 0, 0, 0, 0.0
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
                if row.get("municipalidad_uuid"):
                    from modules.entidades.domain.models.municipalidad import (
                        Municipalidad,
                    )

                    defaults["municipalidad"] = ctx.resolve_fk(
                        Municipalidad, row["municipalidad_uuid"]
                    )
                if row.get("ubigeo_distrito_uuid"):
                    defaults["ubigeo_distrito"] = ctx.resolve_fk(
                        UbigeoDistrito, row["ubigeo_distrito_uuid"]
                    )
                if row.get("ubigeo_provincia_uuid"):
                    defaults["ubigeo_provincia"] = ctx.resolve_fk(
                        UbigeoProvincia, row["ubigeo_provincia_uuid"]
                    )

                obj, was_created = Entidad.objects.update_or_create(
                    id=row["uuid"], defaults=defaults
                )
                ctx.store(Entidad, obj.id, obj)
                if was_created:
                    created += 1
                else:
                    updated += 1
                if verbose:
                    tag = "CREATE" if was_created else "UPDATE"
                    self.stdout.write(f"[{tag}] Entidad {row['uuid']}")
            except Exception as e:
                errors += 1
                self.stdout.write(f"ERROR Entidad {row['uuid']}: {e}")

        duration = time.time() - start
        self.print_summary(
            self.SEED_PHASE, "Entidad", len(rows), created, updated, errors, duration
        )