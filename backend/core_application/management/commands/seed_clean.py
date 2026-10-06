import time

from django.core.management import call_command
from django.core.management.base import BaseCommand


PHASE_0_COMMANDS = [
    "seed_clean_catalogos_usuarios",
    "seed_clean_catalogos_ubigeo",
    "seed_clean_catalogos_municipalidades",
    "seed_clean_catalogos_finanzas",
    "seed_clean_catalogos_liquidaciones",
]

PHASE_1_13_COMMANDS = [
    ("usuarios", "seed_clean_usuarios"),
    ("entidades", "seed_clean_entidades"),
    ("personas_operativas", "seed_clean_personas_operativas"),
    ("operaciones", "seed_clean_operaciones"),
    ("proyectos", "seed_clean_proyectos"),
    ("liquidacion_general", "seed_clean_liquidacion_general"),
    ("liquidacion_edil", "seed_clean_liquidacion_edil"),
    ("liquidacion_hu", "seed_clean_liquidacion_hu"),
    ("liquidacion_io", "seed_clean_liquidacion_io"),
    ("liquidacion_rh", "seed_clean_liquidacion_rh"),
    ("entidades_vacias", "seed_clean_entidades_vacias"),
    ("finanzas_vacias", "seed_clean_finanzas_vacias"),
    ("liquidaciones_vacias", "seed_clean_liquidaciones_vacias"),
]


class Command(BaseCommand):
    help = "Orquestador clean-seed: DB completa desde cero (Phase 0 + Phase 1-13)"

    def add_arguments(self, parser):
        parser.add_argument("--dry-run", action="store_true")
        parser.add_argument("--verbose", action="store_true")
        parser.add_argument(
            "--only",
            type=str,
            default="",
            help="Comma-separated list of phase names to run (e.g. liquidacion_rh,proyectos)",
        )
        parser.add_argument(
            "--skip-phase0",
            action="store_true",
            help="Skip Phase 0 catalogos (only run Phase 1-13)",
        )

    def handle(self, *args, **options):
        dry_run = options.get("dry_run", False)
        verbose = options.get("verbose", False)
        only = set(p.strip() for p in options.get("only", "").split(",") if p.strip())
        skip_phase0 = options.get("skip_phase0", False)

        grand_start = time.time()
        rows = []

        if not skip_phase0 and (not only or "phase0_catalogos" in only):
            self.stdout.write("\n=== Phase: phase0_catalogos (existing seeds) ===")
            phase0_start = time.time()
            phase0_failed = 0
            for cmd_name in PHASE_0_COMMANDS:
                try:
                    call_command(cmd_name)
                except Exception as e:
                    phase0_failed += 1
                    self.stdout.write(self.style.ERROR(f"  Phase0 {cmd_name} FAILED: {e}"))
            phase0_duration = time.time() - phase0_start
            rows.append(("phase0_catalogos", "OK" if phase0_failed == 0 else "FAIL", phase0_duration, phase0_failed))

        for phase_name, cmd_name in PHASE_1_13_COMMANDS:
            if only and phase_name not in only:
                continue
            start = time.time()
            self.stdout.write(f"\n=== Phase: {phase_name} ({cmd_name}) ===")
            try:
                kwargs = {}
                if dry_run:
                    kwargs["dry_run"] = True
                if verbose:
                    kwargs["verbose"] = True
                call_command(cmd_name, **kwargs)
                duration = time.time() - start
                rows.append((phase_name, "OK", duration, 0))
            except Exception as e:
                duration = time.time() - start
                rows.append((phase_name, "FAIL", duration, 1))
                self.stdout.write(self.style.ERROR(f"Phase {phase_name} FAILED: {e}"))

        total_duration = time.time() - grand_start

        self.stdout.write("\n" + "=" * 80)
        self.stdout.write("seed_clean SUMMARY")
        self.stdout.write("=" * 80)
        for phase, status, duration, err in rows:
            tag = "OK" if err == 0 else "FAIL"
            self.stdout.write(
                f"  [{tag}] {phase:30s} {duration:>8.2f}s"
            )
        self.stdout.write("-" * 80)
        self.stdout.write(f"  Total: {total_duration:.2f}s, errors: {sum(r[3] for r in rows)}")

        if any(r[3] > 0 for r in rows):
            self.stdout.write(self.style.ERROR("seed_clean FAILED"))
            exit(1)
        self.stdout.write(self.style.SUCCESS("seed_clean OK"))