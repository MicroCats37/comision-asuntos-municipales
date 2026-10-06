import json
import time
from pathlib import Path

from core_application.management.commands._seed_clean_base import (
    BaseCleanSeedCommand,
    SeedContext,
)
from modules.liquidaciones.domain.models.liquidacion.liquidacion_general.liquidacion import (
    LiquidacionCodigo,
    LiquidacionEspecialidadDisponibles,
)
from modules.liquidaciones.domain.models.liquidacion.liquidacion_tipo.liquidacion_tipo import (
    LiquidacionPorCategoriaVisitas,
    LiquidacionPorMetroCuadrado,
)
from modules.liquidaciones.domain.models.liquidacion.liquidacion_tipo.tarifas_reglas import (
    DerechoPorcentajeObra,
    DerechoPorMetroCuadrado,
    TarifaLiquidacionBase,
    TarifaPorCategoriaVisitas,
    TarifaPorcentajeObra,
    TarifaPorMetroCuadrado,
)
from modules.liquidaciones.domain.models.tipo_liquidacion import TipoLiquidacion
from modules.usuarios.domain.models.perfil_ingeniero import EspecialidadRevision


class Command(BaseCleanSeedCommand):
    help = "Phase 0 catalogos liquidaciones (tipoliquidacion, codigo, tarifas, derechos, especialidades)"
    SEED_PHASE = "catalogos_liquidaciones"
    MODELS_TO_SEED = [
        TipoLiquidacion,
        LiquidacionCodigo,
        TarifaLiquidacionBase,
        TarifaPorcentajeObra,
        TarifaPorCategoriaVisitas,
        TarifaPorMetroCuadrado,
        DerechoPorMetroCuadrado,
        DerechoPorcentajeObra,
        LiquidacionEspecialidadDisponibles,
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
        self._seed_tipo_liquidacion(ctx, dry_run, verbose)
        self._seed_liquidacion_codigo(ctx, dry_run, verbose)
        self._seed_tarifa_liquidacion_base(ctx, dry_run, verbose)
        self._seed_tarifa_porcentaje_obra(ctx, dry_run, verbose)
        self._seed_tarifa_porcategoria_visitas(ctx, dry_run, verbose)
        self._seed_tarifa_pormetro_cuadrado(ctx, dry_run, verbose)
        self._seed_derecho_pormetro_cuadrado(ctx, dry_run, verbose)
        self._seed_derecho_porcentaje_obra(ctx, dry_run, verbose)
        self._seed_liquidacion_especialidad_disponibles(ctx, dry_run, verbose)

    def _seed_tipo_liquidacion(self, ctx, dry_run, verbose):
        rows = self._load_json("liquidaciones_tipoliquidacion.json")
        if dry_run:
            self.print_summary(
                self.SEED_PHASE, "TipoLiquidacion", len(rows), 0, 0, 0, 0.0
            )
            return
        start = time.time()
        created = updated = errors = 0
        for row in rows:
            try:
                defaults = {
                    k: v for k, v in row.items() if k != "uuid" and not k.endswith("_uuid")
                }
                obj, was_created = TipoLiquidacion.objects.update_or_create(
                    id=row["uuid"], defaults=defaults
                )
                ctx.store(TipoLiquidacion, obj.id, obj)
                if was_created:
                    created += 1
                else:
                    updated += 1
                if verbose:
                    tag = "CREATE" if was_created else "UPDATE"
                    self.stdout.write(f"[{tag}] TipoLiquidacion {row['uuid']}")
            except Exception as e:
                errors += 1
                self.stdout.write(f"ERROR TipoLiquidacion {row['uuid']}: {e}")
        duration = time.time() - start
        self.print_summary(
            self.SEED_PHASE,
            "TipoLiquidacion",
            len(rows),
            created,
            updated,
            errors,
            duration,
        )

    def _seed_liquidacion_codigo(self, ctx, dry_run, verbose):
        rows = self._load_json("liquidaciones_liquidacioncodigo.json")
        if dry_run:
            self.print_summary(
                self.SEED_PHASE, "LiquidacionCodigo", len(rows), 0, 0, 0, 0.0
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
                obj, was_created = LiquidacionCodigo.objects.update_or_create(
                    id=row["uuid"], defaults=defaults
                )
                if was_created:
                    created += 1
                else:
                    updated += 1
                if verbose:
                    tag = "CREATE" if was_created else "UPDATE"
                    self.stdout.write(f"[{tag}] LiquidacionCodigo {row['uuid']}")
            except Exception as e:
                errors += 1
                self.stdout.write(f"ERROR LiquidacionCodigo {row['uuid']}: {e}")
        duration = time.time() - start
        self.print_summary(
            self.SEED_PHASE,
            "LiquidacionCodigo",
            len(rows),
            created,
            updated,
            errors,
            duration,
        )

    def _seed_tarifa_liquidacion_base(self, ctx, dry_run, verbose):
        rows = self._load_json("liquidaciones_tarifaliquidacionbase.json")
        if dry_run:
            self.print_summary(
                self.SEED_PHASE, "TarifaLiquidacionBase", len(rows), 0, 0, 0, 0.0
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
                obj, was_created = TarifaLiquidacionBase.objects.update_or_create(
                    id=row["uuid"], defaults=defaults
                )
                ctx.store(TarifaLiquidacionBase, obj.id, obj)
                if was_created:
                    created += 1
                else:
                    updated += 1
                if verbose:
                    tag = "CREATE" if was_created else "UPDATE"
                    self.stdout.write(f"[{tag}] TarifaLiquidacionBase {row['uuid']}")
            except Exception as e:
                errors += 1
                self.stdout.write(f"ERROR TarifaLiquidacionBase {row['uuid']}: {e}")
        duration = time.time() - start
        self.print_summary(
            self.SEED_PHASE,
            "TarifaLiquidacionBase",
            len(rows),
            created,
            updated,
            errors,
            duration,
        )

    def _seed_tarifa_porcentaje_obra(self, ctx, dry_run, verbose):
        rows = self._load_json("liquidaciones_tarifaporcentajeobra.json")
        if dry_run:
            self.print_summary(
                self.SEED_PHASE, "TarifaPorcentajeObra", len(rows), 0, 0, 0, 0.0
            )
            return
        start = time.time()
        created = updated = errors = 0
        for row in rows:
            try:
                defaults = {
                    k: v for k, v in row.items() if k != "uuid" and not k.endswith("_uuid")
                }
                if row.get("tarifa_base_uuid"):
                    defaults["tarifa_base"] = ctx.resolve_fk(
                        TarifaLiquidacionBase, row["tarifa_base_uuid"]
                    )
                obj, was_created = TarifaPorcentajeObra.objects.update_or_create(
                    id=row["uuid"], defaults=defaults
                )
                if was_created:
                    created += 1
                else:
                    updated += 1
                if verbose:
                    tag = "CREATE" if was_created else "UPDATE"
                    self.stdout.write(f"[{tag}] TarifaPorcentajeObra {row['uuid']}")
            except Exception as e:
                errors += 1
                self.stdout.write(f"ERROR TarifaPorcentajeObra {row['uuid']}: {e}")
        duration = time.time() - start
        self.print_summary(
            self.SEED_PHASE,
            "TarifaPorcentajeObra",
            len(rows),
            created,
            updated,
            errors,
            duration,
        )

    def _seed_tarifa_porcategoria_visitas(self, ctx, dry_run, verbose):
        rows = self._load_json("liquidaciones_tarifaporcategoriavisitas.json")
        if dry_run:
            self.print_summary(
                self.SEED_PHASE, "TarifaPorCategoriaVisitas", len(rows), 0, 0, 0, 0.0
            )
            return
        start = time.time()
        created = updated = errors = 0
        for row in rows:
            try:
                defaults = {
                    k: v for k, v in row.items() if k != "uuid" and not k.endswith("_uuid")
                }
                if row.get("tarifa_base_uuid"):
                    defaults["tarifa_base"] = ctx.resolve_fk(
                        TarifaLiquidacionBase, row["tarifa_base_uuid"]
                    )
                obj, was_created = TarifaPorCategoriaVisitas.objects.update_or_create(
                    id=row["uuid"], defaults=defaults
                )
                if was_created:
                    created += 1
                else:
                    updated += 1
                if verbose:
                    tag = "CREATE" if was_created else "UPDATE"
                    self.stdout.write(f"[{tag}] TarifaPorCategoriaVisitas {row['uuid']}")
            except Exception as e:
                errors += 1
                self.stdout.write(f"ERROR TarifaPorCategoriaVisitas {row['uuid']}: {e}")
        duration = time.time() - start
        self.print_summary(
            self.SEED_PHASE,
            "TarifaPorCategoriaVisitas",
            len(rows),
            created,
            updated,
            errors,
            duration,
        )

    def _seed_tarifa_pormetro_cuadrado(self, ctx, dry_run, verbose):
        rows = self._load_json("liquidaciones_tarifapormetrocuadrado.json")
        if dry_run:
            self.print_summary(
                self.SEED_PHASE, "TarifaPorMetroCuadrado", len(rows), 0, 0, 0, 0.0
            )
            return
        start = time.time()
        created = updated = errors = 0
        for row in rows:
            try:
                defaults = {
                    k: v for k, v in row.items() if k != "uuid" and not k.endswith("_uuid")
                }
                if row.get("tarifa_base_uuid"):
                    defaults["tarifa_base"] = ctx.resolve_fk(
                        TarifaLiquidacionBase, row["tarifa_base_uuid"]
                    )
                obj, was_created = TarifaPorMetroCuadrado.objects.update_or_create(
                    id=row["uuid"], defaults=defaults
                )
                if was_created:
                    created += 1
                else:
                    updated += 1
                if verbose:
                    tag = "CREATE" if was_created else "UPDATE"
                    self.stdout.write(f"[{tag}] TarifaPorMetroCuadrado {row['uuid']}")
            except Exception as e:
                errors += 1
                self.stdout.write(f"ERROR TarifaPorMetroCuadrado {row['uuid']}: {e}")
        duration = time.time() - start
        self.print_summary(
            self.SEED_PHASE,
            "TarifaPorMetroCuadrado",
            len(rows),
            created,
            updated,
            errors,
            duration,
        )

    def _seed_derecho_pormetro_cuadrado(self, ctx, dry_run, verbose):
        rows = self._load_json("liquidaciones_derechopormetrocuadrado.json")
        if dry_run:
            self.print_summary(
                self.SEED_PHASE, "DerechoPorMetroCuadrado", len(rows), 0, 0, 0, 0.0
            )
            return
        start = time.time()
        created = updated = errors = 0
        for row in rows:
            try:
                defaults = {
                    k: v for k, v in row.items() if k != "uuid" and not k.endswith("_uuid")
                }
                obj, was_created = DerechoPorMetroCuadrado.objects.update_or_create(
                    id=row["uuid"], defaults=defaults
                )
                if was_created:
                    created += 1
                else:
                    updated += 1
                if verbose:
                    tag = "CREATE" if was_created else "UPDATE"
                    self.stdout.write(f"[{tag}] DerechoPorMetroCuadrado {row['uuid']}")
            except Exception as e:
                errors += 1
                self.stdout.write(f"ERROR DerechoPorMetroCuadrado {row['uuid']}: {e}")
        duration = time.time() - start
        self.print_summary(
            self.SEED_PHASE,
            "DerechoPorMetroCuadrado",
            len(rows),
            created,
            updated,
            errors,
            duration,
        )

    def _seed_derecho_porcentaje_obra(self, ctx, dry_run, verbose):
        rows = self._load_json("liquidaciones_derechoporcentajeobra.json")
        if dry_run:
            self.print_summary(
                self.SEED_PHASE, "DerechoPorcentajeObra", len(rows), 0, 0, 0, 0.0
            )
            return
        start = time.time()
        created = updated = errors = 0
        for row in rows:
            try:
                defaults = {
                    k: v for k, v in row.items() if k != "uuid" and not k.endswith("_uuid")
                }
                obj, was_created = DerechoPorcentajeObra.objects.update_or_create(
                    id=row["uuid"], defaults=defaults
                )
                if was_created:
                    created += 1
                else:
                    updated += 1
                if verbose:
                    tag = "CREATE" if was_created else "UPDATE"
                    self.stdout.write(f"[{tag}] DerechoPorcentajeObra {row['uuid']}")
            except Exception as e:
                errors += 1
                self.stdout.write(f"ERROR DerechoPorcentajeObra {row['uuid']}: {e}")
        duration = time.time() - start
        self.print_summary(
            self.SEED_PHASE,
            "DerechoPorcentajeObra",
            len(rows),
            created,
            updated,
            errors,
            duration,
        )

    def _seed_liquidacion_especialidad_disponibles(self, ctx, dry_run, verbose):
        rows = self._load_json("liquidaciones_liquidacionespecialidaddisponibles.json")
        if dry_run:
            self.print_summary(
                self.SEED_PHASE,
                "LiquidacionEspecialidadDisponibles",
                len(rows),
                0,
                0,
                0,
                0.0,
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
                if row.get("especialidad_uuid"):
                    defaults["especialidad"] = ctx.resolve_fk(
                        EspecialidadRevision, row["especialidad_uuid"]
                    )
                obj, was_created = LiquidacionEspecialidadDisponibles.objects.update_or_create(
                    id=row["uuid"], defaults=defaults
                )
                if was_created:
                    created += 1
                else:
                    updated += 1
                if verbose:
                    tag = "CREATE" if was_created else "UPDATE"
                    self.stdout.write(
                        f"[{tag}] LiquidacionEspecialidadDisponibles {row['uuid']}"
                    )
            except Exception as e:
                errors += 1
                self.stdout.write(
                    f"ERROR LiquidacionEspecialidadDisponibles {row['uuid']}: {e}"
                )
        duration = time.time() - start
        self.print_summary(
            self.SEED_PHASE,
            "LiquidacionEspecialidadDisponibles",
            len(rows),
            created,
            updated,
            errors,
            duration,
        )