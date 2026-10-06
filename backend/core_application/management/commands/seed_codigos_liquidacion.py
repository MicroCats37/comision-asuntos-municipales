"""
Comando para sembrar los códigos de cuenta (LiquidacionCodigo) por tipo de liquidación
desde catalogos/codigos_liquidacion.json.

Idempotente: update_or_create sobre (tipo_liquidacion).
Uso:
    python manage.py seed_codigos_liquidacion --settings=config.settings.development
    python manage.py seed_codigos_liquidacion --dry-run --settings=config.settings.development
"""
import json
from pathlib import Path

from django.core.management.base import BaseCommand

from modules.liquidaciones.domain.models.liquidacion.liquidacion_general.liquidacion import (
    LiquidacionCodigo,
)
from modules.liquidaciones.domain.models.tipo_liquidacion import TipoLiquidacion


class Command(BaseCommand):
    help = "Siembra los códigos de cuenta (LiquidacionCodigo) por tipo de liquidación desde JSON."

    SEEDS_DIR = Path(__file__).resolve().parent.parent.parent / "seeds" / "catalogos"

    def add_arguments(self, parser):
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Validar sin escribir en la base de datos.",
        )

    def handle(self, *args, **options):
        dry_run = options["dry_run"]

        seed_file = self.SEEDS_DIR / "codigos_liquidacion.json"
        if not seed_file.exists():
            self.stdout.write(self.style.ERROR(f"No se encontró {seed_file}"))
            return

        with open(seed_file, encoding="utf-8") as f:
            data = json.load(f)

        codigos = data.get("codigos", [])
        creados = 0
        actualizados = 0

        for item in codigos:
            tipo_liquidacion_codigo = item["tipo_liquidacion"]
            codigo_cta = item["codigo_cta"]

            tipo, _ = TipoLiquidacion.objects.get_or_create(
                codigo=tipo_liquidacion_codigo,
                defaults={"nombre": tipo_liquidacion_codigo.replace("_", " ").title()},
            )

            if dry_run:
                existing = LiquidacionCodigo.objects.filter(
                    tipo_liquidacion=tipo, codigo_cta=codigo_cta
                ).first()
                if existing:
                    self.stdout.write(
                        f"  [DRY-RUN] {tipo_liquidacion_codigo} -> ya existe ({codigo_cta})"
                    )
                else:
                    self.stdout.write(
                        f"  [DRY-RUN] {tipo_liquidacion_codigo} -> CREAR ({codigo_cta})"
                    )
                continue

            _, created = LiquidacionCodigo.objects.update_or_create(
                tipo_liquidacion=tipo,
                defaults={"codigo_cta": codigo_cta},
            )
            if created:
                creados += 1
            else:
                actualizados += 1

        if dry_run:
            self.stdout.write(
                self.style.WARNING("DRY-RUN: No se escribió en la base de datos.")
            )
            return

        self.stdout.write(
            self.style.SUCCESS(
                f"LiquidacionCodigo: {creados} creados, {actualizados} actualizados"
            )
        )
