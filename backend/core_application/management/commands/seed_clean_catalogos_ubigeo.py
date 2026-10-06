import json
import time
from pathlib import Path

from core_application.management.commands._seed_clean_base import (
    BaseCleanSeedCommand,
    SeedContext,
)
from modules.entidades.domain.models.ubigeo import (
    UbigeoDepartamento,
    UbigeoDistrito,
    UbigeoProvincia,
)


class Command(BaseCleanSeedCommand):
    help = "Phase 0 catalogos ubigeo (departamento, provincia, distrito)"
    SEED_PHASE = "catalogos_ubigeo"
    MODELS_TO_SEED = [UbigeoDepartamento, UbigeoProvincia, UbigeoDistrito]
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
        self._seed_departamento(ctx, dry_run, verbose)
        self._seed_provincia(ctx, dry_run, verbose)
        self._seed_distrito(ctx, dry_run, verbose)

    def _seed_departamento(self, ctx, dry_run, verbose):
        rows = self._load_json("entidades_ubigeodepartamento.json")
        if dry_run:
            self.print_summary(
                self.SEED_PHASE, "UbigeoDepartamento", len(rows), 0, 0, 0, 0.0
            )
            return
        start = time.time()
        created = updated = errors = 0
        for row in rows:
            try:
                defaults = {
                    k: v for k, v in row.items() if k != "uuid" and not k.endswith("_uuid")
                }
                obj, was_created = UbigeoDepartamento.objects.update_or_create(
                    id=row["uuid"], defaults=defaults
                )
                ctx.store(UbigeoDepartamento, obj.id, obj)
                if was_created:
                    created += 1
                else:
                    updated += 1
                if verbose:
                    tag = "CREATE" if was_created else "UPDATE"
                    self.stdout.write(f"[{tag}] UbigeoDepartamento {row['uuid']}")
            except Exception as e:
                errors += 1
                self.stdout.write(f"ERROR UbigeoDepartamento {row['uuid']}: {e}")
        duration = time.time() - start
        self.print_summary(
            self.SEED_PHASE,
            "UbigeoDepartamento",
            len(rows),
            created,
            updated,
            errors,
            duration,
        )

    def _seed_provincia(self, ctx, dry_run, verbose):
        rows = self._load_json("entidades_ubigeoprovincia.json")
        if dry_run:
            self.print_summary(
                self.SEED_PHASE, "UbigeoProvincia", len(rows), 0, 0, 0, 0.0
            )
            return
        start = time.time()
        created = updated = errors = 0
        for row in rows:
            try:
                defaults = {
                    k: v for k, v in row.items() if k != "uuid" and not k.endswith("_uuid")
                }
                if row.get("departamento_uuid"):
                    defaults["departamento"] = ctx.resolve_fk(
                        UbigeoDepartamento, row["departamento_uuid"]
                    )
                obj, was_created = UbigeoProvincia.objects.update_or_create(
                    id=row["uuid"], defaults=defaults
                )
                ctx.store(UbigeoProvincia, obj.id, obj)
                if was_created:
                    created += 1
                else:
                    updated += 1
                if verbose:
                    tag = "CREATE" if was_created else "UPDATE"
                    self.stdout.write(f"[{tag}] UbigeoProvincia {row['uuid']}")
            except Exception as e:
                errors += 1
                self.stdout.write(f"ERROR UbigeoProvincia {row['uuid']}: {e}")
        duration = time.time() - start
        self.print_summary(
            self.SEED_PHASE,
            "UbigeoProvincia",
            len(rows),
            created,
            updated,
            errors,
            duration,
        )

    def _seed_distrito(self, ctx, dry_run, verbose):
        rows = self._load_json("entidades_ubigeodistrito.json")
        if dry_run:
            self.print_summary(
                self.SEED_PHASE, "UbigeoDistrito", len(rows), 0, 0, 0, 0.0
            )
            return
        start = time.time()
        created = updated = errors = 0
        for row in rows:
            try:
                defaults = {
                    k: v for k, v in row.items() if k != "uuid" and not k.endswith("_uuid")
                }
                if row.get("provincia_uuid"):
                    defaults["provincia"] = ctx.resolve_fk(
                        UbigeoProvincia, row["provincia_uuid"]
                    )
                obj, was_created = UbigeoDistrito.objects.update_or_create(
                    id=row["uuid"], defaults=defaults
                )
                ctx.store(UbigeoDistrito, obj.id, obj)
                if was_created:
                    created += 1
                else:
                    updated += 1
                if verbose:
                    tag = "CREATE" if was_created else "UPDATE"
                    self.stdout.write(f"[{tag}] UbigeoDistrito {row['uuid']}")
            except Exception as e:
                errors += 1
                self.stdout.write(f"ERROR UbigeoDistrito {row['uuid']}: {e}")
        duration = time.time() - start
        self.print_summary(
            self.SEED_PHASE,
            "UbigeoDistrito",
            len(rows),
            created,
            updated,
            errors,
            duration,
        )