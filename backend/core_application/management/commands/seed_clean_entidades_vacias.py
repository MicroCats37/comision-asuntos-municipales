import json
import time
from pathlib import Path

from core_application.management.commands._seed_clean_base import BaseCleanSeedCommand


class Command(BaseCleanSeedCommand):
    help = "Phase 11 stub: entidades vacias (alcalde, banco, contacto, contactobanco, contactomunicipalidad, gerenteurbano)"
    SEED_PHASE = "entidades_vacias"

    SEEDS_DIR = (
        Path(__file__).resolve().parent.parent.parent
        / "seeds"
        / "migrados"
    )

    TABLES = [
        "entidades_alcalde",
        "entidades_banco",
        "entidades_contacto",
        "entidades_contactobanco",
        "entidades_contactomunicipalidad",
        "entidades_gerenteurbano",
    ]

    def add_arguments(self, parser):
        parser.add_argument("--dry-run", action="store_true")
        parser.add_argument("--verbose", action="store_true")

    def handle_phase(self, *args, **options):
        dry_run = options.get("dry_run", False)
        verbose = options.get("verbose", False)
        start = time.time()
        total = 0
        for table in self.TABLES:
            path = self.SEEDS_DIR / f"{table}.json"
            if not path.exists():
                self.stdout.write(f"[SKIP] {table}: JSON missing")
                continue
            with open(path, encoding="utf-8") as f:
                rows = json.load(f)
            count = len(rows)
            total += count
            if verbose or dry_run:
                msg = f"[{'DRY' if dry_run else 'INFO'}] {table}: {count} rows ({'empty stub' if count == 0 else 'HAS DATA — needs real handler'})"
                self.stdout.write(msg)
        duration = time.time() - start
        self.print_summary(
            self.SEED_PHASE,
            "stub (6 tables)",
            total,
            0,
            0,
            0,
            duration,
        )
        if total == 0:
            self.stdout.write("Phase 11 ready: 0 rows awaiting migration (15% remaining)")