import json
import time
from pathlib import Path

from core_application.management.commands._seed_clean_base import (
    BaseCleanSeedCommand,
    SeedContext,
)
from modules.finanzas.domain.models.descuento_inspector import (
    EscalaDescuentoInspector,
    RangoDescuentoInspector,
)
from modules.finanzas.domain.models.impuestos import IGV, UIT
from modules.finanzas.domain.models.tasa_delegado import TasaDelegado
from modules.liquidaciones.domain.models.tipo_liquidacion import TipoLiquidacion


class Command(BaseCleanSeedCommand):
    help = "Phase 0 catalogos finanzas (uit, igv, tasadelegado, rangodescuentoinspector, escaladescuentoinspector)"
    SEED_PHASE = "catalogos_finanzas"
    MODELS_TO_SEED = [
        UIT,
        IGV,
        TasaDelegado,
        RangoDescuentoInspector,
        EscalaDescuentoInspector,
    ]
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
        self._seed_uit(ctx, dry_run, verbose)
        self._seed_igv(ctx, dry_run, verbose)
        self._seed_tasa_delegado(ctx, dry_run, verbose)
        self._seed_escala_descuento(ctx, dry_run, verbose)
        self._seed_rango_descuento(ctx, dry_run, verbose)

    def _seed_uit(self, ctx, dry_run, verbose):
        rows = self._load_json("finanzas_uit.json")
        if dry_run:
            self.print_summary(self.SEED_PHASE, "UIT", len(rows), 0, 0, 0, 0.0)
            return
        start = time.time()
        created = updated = errors = 0
        for row in rows:
            try:
                defaults = {
                    k: v for k, v in row.items() if k != "uuid" and not k.endswith("_uuid")
                }
                obj, was_created = UIT.objects.update_or_create(
                    id=row["uuid"], defaults=defaults
                )
                ctx.store(UIT, obj.id, obj)
                if was_created:
                    created += 1
                else:
                    updated += 1
                if verbose:
                    tag = "CREATE" if was_created else "UPDATE"
                    self.stdout.write(f"[{tag}] UIT {row['uuid']}")
            except Exception as e:
                errors += 1
                self.stdout.write(f"ERROR UIT {row['uuid']}: {e}")
        duration = time.time() - start
        self.print_summary(
            self.SEED_PHASE, "UIT", len(rows), created, updated, errors, duration
        )

    def _seed_igv(self, ctx, dry_run, verbose):
        rows = self._load_json("finanzas_igv.json")
        if dry_run:
            self.print_summary(self.SEED_PHASE, "IGV", len(rows), 0, 0, 0, 0.0)
            return
        start = time.time()
        created = updated = errors = 0
        for row in rows:
            try:
                defaults = {
                    k: v for k, v in row.items() if k != "uuid" and not k.endswith("_uuid")
                }
                obj, was_created = IGV.objects.update_or_create(
                    id=row["uuid"], defaults=defaults
                )
                ctx.store(IGV, obj.id, obj)
                if was_created:
                    created += 1
                else:
                    updated += 1
                if verbose:
                    tag = "CREATE" if was_created else "UPDATE"
                    self.stdout.write(f"[{tag}] IGV {row['uuid']}")
            except Exception as e:
                errors += 1
                self.stdout.write(f"ERROR IGV {row['uuid']}: {e}")
        duration = time.time() - start
        self.print_summary(
            self.SEED_PHASE, "IGV", len(rows), created, updated, errors, duration
        )

    def _seed_tasa_delegado(self, ctx, dry_run, verbose):
        rows = self._load_json("finanzas_tasadelegado.json")
        if dry_run:
            self.print_summary(
                self.SEED_PHASE, "TasaDelegado", len(rows), 0, 0, 0, 0.0
            )
            return
        start = time.time()
        created = updated = errors = 0
        for row in rows:
            try:
                defaults = {
                    k: v for k, v in row.items() if k != "uuid" and not k.endswith("_uuid")
                }
                if row.get("tipo_liquidacion_uuid"):
                    defaults["tipo_liquidacion"] = ctx.resolve_fk(
                        TipoLiquidacion, row["tipo_liquidacion_uuid"]
                    )
                obj, was_created = TasaDelegado.objects.update_or_create(
                    id=row["uuid"], defaults=defaults
                )
                if was_created:
                    created += 1
                else:
                    updated += 1
                if verbose:
                    tag = "CREATE" if was_created else "UPDATE"
                    self.stdout.write(f"[{tag}] TasaDelegado {row['uuid']}")
            except Exception as e:
                errors += 1
                self.stdout.write(f"ERROR TasaDelegado {row['uuid']}: {e}")
        duration = time.time() - start
        self.print_summary(
            self.SEED_PHASE,
            "TasaDelegado",
            len(rows),
            created,
            updated,
            errors,
            duration,
        )

    def _seed_escala_descuento(self, ctx, dry_run, verbose):
        rows = self._load_json("finanzas_escaladescuentoinspector.json")
        if dry_run:
            self.print_summary(
                self.SEED_PHASE, "EscalaDescuentoInspector", len(rows), 0, 0, 0, 0.0
            )
            return
        start = time.time()
        created = updated = errors = 0
        for row in rows:
            try:
                defaults = {
                    k: v for k, v in row.items() if k != "uuid" and not k.endswith("_uuid")
                }
                obj, was_created = EscalaDescuentoInspector.objects.update_or_create(
                    id=row["uuid"], defaults=defaults
                )
                ctx.store(EscalaDescuentoInspector, obj.id, obj)
                if was_created:
                    created += 1
                else:
                    updated += 1
                if verbose:
                    tag = "CREATE" if was_created else "UPDATE"
                    self.stdout.write(f"[{tag}] EscalaDescuentoInspector {row['uuid']}")
            except Exception as e:
                errors += 1
                self.stdout.write(f"ERROR EscalaDescuentoInspector {row['uuid']}: {e}")
        duration = time.time() - start
        self.print_summary(
            self.SEED_PHASE,
            "EscalaDescuentoInspector",
            len(rows),
            created,
            updated,
            errors,
            duration,
        )

    def _seed_rango_descuento(self, ctx, dry_run, verbose):
        rows = self._load_json("finanzas_rangodescuentoinspector.json")
        if dry_run:
            self.print_summary(
                self.SEED_PHASE, "RangoDescuentoInspector", len(rows), 0, 0, 0, 0.0
            )
            return
        start = time.time()
        created = updated = errors = 0
        for row in rows:
            try:
                defaults = {
                    k: v for k, v in row.items() if k != "uuid" and not k.endswith("_uuid")
                }
                if row.get("escala_uuid"):
                    defaults["escala"] = ctx.resolve_fk(
                        EscalaDescuentoInspector, row["escala_uuid"]
                    )
                obj, was_created = RangoDescuentoInspector.objects.update_or_create(
                    id=row["uuid"], defaults=defaults
                )
                if was_created:
                    created += 1
                else:
                    updated += 1
                if verbose:
                    tag = "CREATE" if was_created else "UPDATE"
                    self.stdout.write(f"[{tag}] RangoDescuentoInspector {row['uuid']}")
            except Exception as e:
                errors += 1
                self.stdout.write(f"ERROR RangoDescuentoInspector {row['uuid']}: {e}")
        duration = time.time() - start
        self.print_summary(
            self.SEED_PHASE,
            "RangoDescuentoInspector",
            len(rows),
            created,
            updated,
            errors,
            duration,
        )