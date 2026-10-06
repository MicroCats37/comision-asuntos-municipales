import json
import time
from pathlib import Path

from core_application.management.commands._seed_clean_base import (
    BaseCleanSeedCommand,
    SeedContext,
)
from modules.usuarios.domain.models.perfil_ingeniero import (
    Capitulo,
    EspecialidadIngeniero,
    EspecialidadRevision,
)


class Command(BaseCleanSeedCommand):
    help = "Phase 0 catalogos usuarios (capitulo, especialidadingeniero, especialidadrevision)"
    SEED_PHASE = "catalogos_usuarios"
    MODELS_TO_SEED = [Capitulo, EspecialidadIngeniero, EspecialidadRevision]
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
        self._seed_capitulo(ctx, dry_run, verbose)
        self._seed_especialidad_ingeniero(ctx, dry_run, verbose)
        self._seed_especialidad_revision(ctx, dry_run, verbose)

    def _seed_capitulo(self, ctx, dry_run, verbose):
        rows = self._load_json("usuarios_capitulo.json")
        if dry_run:
            self.print_summary(self.SEED_PHASE, "Capitulo", len(rows), 0, 0, 0, 0.0)
            return
        start = time.time()
        created = updated = errors = 0
        for row in rows:
            try:
                defaults = {
                    k: v for k, v in row.items() if k != "uuid" and not k.endswith("_uuid")
                }
                if "registro_uuid" in row:
                    defaults["registro_id"] = row["registro_uuid"]
                obj, was_created = Capitulo.objects.update_or_create(
                    id=row["uuid"], defaults=defaults
                )
                ctx.store(Capitulo, obj.id, obj)
                if was_created:
                    created += 1
                else:
                    updated += 1
                if verbose:
                    tag = "CREATE" if was_created else "UPDATE"
                    self.stdout.write(f"[{tag}] Capitulo {row['uuid']}")
            except Exception as e:
                errors += 1
                self.stdout.write(f"ERROR Capitulo {row['uuid']}: {e}")
        duration = time.time() - start
        self.print_summary(
            self.SEED_PHASE, "Capitulo", len(rows), created, updated, errors, duration
        )

    def _seed_especialidad_ingeniero(self, ctx, dry_run, verbose):
        rows = self._load_json("usuarios_especialidadingeniero.json")
        if dry_run:
            self.print_summary(
                self.SEED_PHASE, "EspecialidadIngeniero", len(rows), 0, 0, 0, 0.0
            )
            return
        start = time.time()
        created = updated = errors = 0
        for row in rows:
            try:
                defaults = {
                    k: v for k, v in row.items() if k != "uuid" and not k.endswith("_uuid")
                }
                if row.get("capitulo_uuid"):
                    defaults["capitulo"] = ctx.resolve_fk(Capitulo, row["capitulo_uuid"])
                obj, was_created = EspecialidadIngeniero.objects.update_or_create(
                    id=row["uuid"], defaults=defaults
                )
                ctx.store(EspecialidadIngeniero, obj.id, obj)
                if was_created:
                    created += 1
                else:
                    updated += 1
                if verbose:
                    tag = "CREATE" if was_created else "UPDATE"
                    self.stdout.write(f"[{tag}] EspecialidadIngeniero {row['uuid']}")
            except Exception as e:
                errors += 1
                self.stdout.write(f"ERROR EspecialidadIngeniero {row['uuid']}: {e}")
        duration = time.time() - start
        self.print_summary(
            self.SEED_PHASE,
            "EspecialidadIngeniero",
            len(rows),
            created,
            updated,
            errors,
            duration,
        )

    def _seed_especialidad_revision(self, ctx, dry_run, verbose):
        rows = self._load_json("usuarios_especialidadrevision.json")
        if dry_run:
            self.print_summary(
                self.SEED_PHASE, "EspecialidadRevision", len(rows), 0, 0, 0, 0.0
            )
            return
        start = time.time()
        created = updated = errors = 0
        for row in rows:
            try:
                defaults = {
                    k: v for k, v in row.items() if k != "uuid" and not k.endswith("_uuid")
                }
                obj, was_created = EspecialidadRevision.objects.update_or_create(
                    id=row["uuid"], defaults=defaults
                )
                ctx.store(EspecialidadRevision, obj.id, obj)
                if was_created:
                    created += 1
                else:
                    updated += 1
                if verbose:
                    tag = "CREATE" if was_created else "UPDATE"
                    self.stdout.write(f"[{tag}] EspecialidadRevision {row['uuid']}")
            except Exception as e:
                errors += 1
                self.stdout.write(f"ERROR EspecialidadRevision {row['uuid']}: {e}")
        duration = time.time() - start
        self.print_summary(
            self.SEED_PHASE,
            "EspecialidadRevision",
            len(rows),
            created,
            updated,
            errors,
            duration,
        )